import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
import models
from services.embedder import get_chunks_by_doc
from services.generator import generate_mcq, generate_essay
from services.filter import filter_duplicate_questions, filter_against_existing
from services.chunker import split_text
from services.embedder import get_model
from sentence_transformers import util
import math
import random
import uuid
import json


router = APIRouter()

BATCH_SIZE = 15


class GenerateRequest(BaseModel):
    doc_id: str
    question_type: str
    difficulty: str = "medium"
    num: int = 5
    batch_size: int = 15


class GenerateFromTextRequest(BaseModel):
    text: str
    question_type: str
    difficulty: str = "medium"
    num: int = 5
    batch_size: int = 15


class SaveRequest(BaseModel):
    doc_id: str
    question_type: str
    questions: list[dict]


class SaveFromTextRequest(BaseModel):
    question_type: str
    questions: list[dict]


def _generate_batch(question_type: str, context: str, num: int, difficulty: str = "medium", existing_questions: list = None, batch_size: int = 15) -> list[dict]:
    print(f"DEBUG _generate_batch: type={question_type}, num={num}, difficulty={difficulty}, batch_size={batch_size}")
    print(f"DEBUG _generate_batch: context_length={len(context)}")
    
    model = get_model()
    THRESHOLD = 0.85

    all_questions = []
    all_embeddings = []
    # Tối ưu: giảm max_attempts để tránh vòng lặp quá dài
    max_attempts = num + 3
    attempt = 0

    # Tối ưu: Cache embedding của ngân hàng câu hỏi đã có, chỉ encode 1 lần
    existing_embeddings = None
    if existing_questions:
        existing_texts = [eq.get("question", "") for eq in existing_questions]
        if existing_texts:
            existing_embeddings = model.encode(existing_texts, convert_to_tensor=True, show_progress_bar=False)
            print(f"DEBUG: Cached {len(existing_texts)} existing question embeddings")

    while len(all_questions) < num and attempt < max_attempts:
        attempt += 1
        remaining = num - len(all_questions)
        batch_num = min(batch_size, remaining)

        print(f"DEBUG: Attempt {attempt}, generating {batch_num} questions")

        try:
            if question_type == "mcq":
                batch = generate_mcq(context, batch_num, difficulty)
            else:
                batch = generate_essay(context, batch_num, difficulty)
        except Exception as e:
            print(f"DEBUG: Generation failed: {str(e)}")
            raise Exception(f"Lỗi sinh câu hỏi: {str(e)}")

        print(f"DEBUG: Generated {len(batch)} questions in batch")

        # Embed toàn bộ batch mới 1 lần
        new_texts = [q.get("question", "") for q in batch]
        new_embeddings = model.encode(new_texts, convert_to_tensor=True, show_progress_bar=False)

        for q, emb in zip(batch, new_embeddings):
            is_dup = False

            # Kiểm tra trùng với câu hỏi đã sinh trong batch này
            if all_embeddings:
                import torch
                existing_tensor = torch.stack(all_embeddings)
                sims = util.cos_sim(emb.unsqueeze(0), existing_tensor)[0]
                if sims.max().item() >= THRESHOLD:
                    is_dup = True

            # Tối ưu: Kiểm tra trùng với ngân hàng câu hỏi đã có (dùng cached embeddings)
            if not is_dup and existing_embeddings is not None:
                sims = util.cos_sim(emb.unsqueeze(0), existing_embeddings)[0]
                if sims.max().item() >= THRESHOLD:
                    is_dup = True

            if not is_dup:
                all_questions.append(q)
                all_embeddings.append(emb)

        print(f"DEBUG: Total questions so far: {len(all_questions)}")

    print(f"DEBUG: Completed with {len(all_questions)} questions")
    return all_questions


@router.post("/generate")
async def generate(body: GenerateRequest, db: Session = Depends(get_db)):
    print(f"DEBUG /generate: doc_id={body.doc_id}, type={body.question_type}, num={body.num}")
    
    if body.difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=400, detail="difficulty phải là 'easy', 'medium' hoặc 'hard'.")

    if body.question_type not in ("mcq", "essay"):
        raise HTTPException(status_code=400, detail="question_type phải là 'mcq' hoặc 'essay'.")

    if body.num < 1 or body.num > 50:
        raise HTTPException(status_code=400, detail="Số câu hỏi phải từ 1 đến 50.")

    # Lấy chunks theo doc_id
    try:
        chunks = get_chunks_by_doc(body.doc_id)
    except Exception as e:
        print(f"DEBUG: Error getting chunks: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu: {str(e)}")

    if not chunks:
        raise HTTPException(status_code=400, detail="Tài liệu không có nội dung.")

    # Sample ngẫu nhiên tối đa 15 chunks làm context, giới hạn 4000 ký tự
    sample = random.sample(chunks, min(15, len(chunks)))
    context = "\n\n".join(sample)
    if len(context) > 4000:
        context = context[:4000] + "..."

    # Lấy câu hỏi đã có trong ngân hàng để kiểm tra trùng lặp
    existing_questions = db.query(models.Question).filter(
        models.Question.doc_id == body.doc_id,
        models.Question.type == body.question_type
    ).all()
    
    existing_questions_data = []
    for q in existing_questions:
        q_dict = {
            "question": q.question,
            "type": q.type
        }
        existing_questions_data.append(q_dict)

    try:
        questions = _generate_batch(body.question_type, context, body.num, body.difficulty, existing_questions_data, body.batch_size)
    except Exception as e:
        print(f"DEBUG: Generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "doc_id": body.doc_id,
        "question_type": body.question_type,
        "difficulty": body.difficulty,
        "total": len(questions),
        "questions": questions
    }


@router.post("/generate-from-text")
async def generate_from_text(body: GenerateFromTextRequest, db: Session = Depends(get_db)):
    print(f"DEBUG /generate-from-text: type={body.question_type}, num={body.num}, text_length={len(body.text)}")
    
    if len(body.text.strip()) < 100:
        raise HTTPException(status_code=400, detail="Văn bản quá ngắn, cần ít nhất 100 ký tự.")

    if body.difficulty not in ("easy", "medium", "hard"):
        raise HTTPException(status_code=400, detail="difficulty phải là 'easy', 'medium' hoặc 'hard'.")

    if body.question_type not in ("mcq", "essay"):
        raise HTTPException(status_code=400, detail="question_type phải là 'mcq' hoặc 'essay'.")

    if body.num < 1 or body.num > 50:
        raise HTTPException(status_code=400, detail="Số câu hỏi phải từ 1 đến 50.")

    # Chia chunks từ văn bản dán trực tiếp
    try:
        chunks = split_text(body.text)
        print(f"DEBUG: Split text into {len(chunks)} chunks")
    except Exception as e:
        print(f"DEBUG: Error splitting text: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Không thể xử lý văn bản: {str(e)}")

    if not chunks:
        raise HTTPException(status_code=400, detail="Không thể xử lý văn bản.")

    # Sample ngẫu nhiên tối đa 15 chunks làm context, giới hạn 4000 ký tự
    sample = random.sample(chunks, min(15, len(chunks)))
    context = "\n\n".join(sample)
    if len(context) > 4000:
        context = context[:4000] + "..."
    print(f"DEBUG: Context length: {len(context)}")

    # Lấy câu hỏi đã có trong ngân hàng để kiểm tra trùng lặp
    existing_questions = db.query(models.Question).filter(
        models.Question.type == body.question_type
    ).all()
    
    existing_questions_data = []
    for q in existing_questions:
        q_dict = {
            "question": q.question,
            "type": q.type
        }
        existing_questions_data.append(q_dict)

    try:
        questions = _generate_batch(body.question_type, context, body.num, body.difficulty, existing_questions_data, body.batch_size)
    except Exception as e:
        print(f"DEBUG: Generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "question_type": body.question_type,
        "difficulty": body.difficulty,
        "total": len(questions),
        "questions": questions
    }


@router.post("/save")
def save_questions(
    body: SaveRequest,
    db: Session = Depends(get_db)
):
    doc = db.query(models.Document).filter(
        models.Document.id == body.doc_id
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    added = 0
    for q in body.questions:
        question = models.Question(
            id=str(uuid.uuid4()),
            doc_id=body.doc_id,
            question=q.get("question", ""),
            type=body.question_type,
            options=json.dumps(q.get("options", {})) if q.get("options") else None,
            answer=q.get("answer", ""),
            explanation=q.get("explanation", ""),
            key_points=json.dumps(q.get("key_points", [])) if q.get("key_points") else None
        )
        db.add(question)
        added += 1

    db.commit()
    return {"added": added}


@router.post("/save-from-text")
def save_from_text(
    body: SaveFromTextRequest,
    db: Session = Depends(get_db)
):
    added = 0
    for q in body.questions:
        question = models.Question(
            id=str(uuid.uuid4()),
            doc_id=None,
            question=q.get("question", ""),
            type=body.question_type,
            options=json.dumps(q.get("options", {})) if q.get("options") else None,
            answer=q.get("answer", ""),
            explanation=q.get("explanation", ""),
            key_points=json.dumps(q.get("key_points", [])) if q.get("key_points") else None
        )
        db.add(question)
        added += 1

    db.commit()
    return {"added": added}
