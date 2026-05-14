import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from database import get_db
import models
import json

router = APIRouter()


def serialize_question(q: models.Question) -> dict:
    return {
        "id": str(q.id),
        "doc_id": str(q.doc_id),
        "type": q.type,
        "question": q.question,
        "options": json.loads(q.options) if q.options else None,
        "answer": q.answer,
        "explanation": q.explanation,
        "key_points": json.loads(q.key_points) if q.key_points else None,
        "created_at": q.created_at,
    }


@router.get("/questions")
def get_questions(
    doc_id: str = Query(None),
    question_type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Question)
    if doc_id:
        query = query.filter(models.Question.doc_id == doc_id)
    if question_type:
        query = query.filter(models.Question.type == question_type)

    total = query.count()
    questions = (
        query
        .order_by(models.Question.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "questions": [serialize_question(q) for q in questions]
    }


@router.get("/questions/{question_id}")
def get_question(question_id: str, db: Session = Depends(get_db)):
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")
    return serialize_question(q)


class UpdateQuestionRequest(BaseModel):
    question: str = None
    options: dict = None
    answer: str = None
    explanation: str = None
    key_points: list = None


@router.put("/questions/{question_id}")
def update_question(
    question_id: str,
    body: UpdateQuestionRequest,
    db: Session = Depends(get_db)
):
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")

    if body.question is not None:
        q.question = body.question
    if body.options is not None:
        q.options = json.dumps(body.options, ensure_ascii=False)
    if body.answer is not None:
        q.answer = body.answer
    if body.explanation is not None:
        q.explanation = body.explanation
    if body.key_points is not None:
        q.key_points = json.dumps(body.key_points, ensure_ascii=False)

    db.commit()
    db.refresh(q)
    return {"message": "Cập nhật thành công", "question": serialize_question(q)}


@router.delete("/questions/{question_id}")
def delete_question(question_id: str, db: Session = Depends(get_db)):
    q = db.query(models.Question).filter(models.Question.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Không tìm thấy câu hỏi.")
    db.delete(q)
    db.commit()
    return {"message": "Đã xóa câu hỏi thành công."}


class DeleteManyRequest(BaseModel):
    ids: list[str]


@router.delete("/questions")
def delete_many_questions(body: DeleteManyRequest, db: Session = Depends(get_db)):
    if not body.ids:
        raise HTTPException(status_code=400, detail="Danh sách id trống.")
    deleted = (
        db.query(models.Question)
        .filter(models.Question.id.in_(body.ids))
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"message": f"Đã xóa {deleted} câu hỏi."}