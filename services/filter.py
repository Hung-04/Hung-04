from sentence_transformers import SentenceTransformer, util
import torch
from services.embedder import get_model

SIMILARITY_THRESHOLD = 0.85  # ngưỡng coi là trùng lặp


def filter_duplicate_questions(questions: list[dict]) -> list[dict]:
    if len(questions) <= 1:
        return questions

    model = get_model()
    texts = [q["question"] for q in questions]
    embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=False)

    kept = []
    kept_embeddings = []

    for i, (question, embedding) in enumerate(zip(questions, embeddings)):
        if not kept_embeddings:
            kept.append(question)
            kept_embeddings.append(embedding)
            continue

        # So sánh với tất cả câu đã giữ lại
        kept_tensor = torch.stack(kept_embeddings)
        similarities = util.cos_sim(embedding.unsqueeze(0), kept_tensor)[0]
        max_similarity = similarities.max().item()

        if max_similarity < SIMILARITY_THRESHOLD:
            kept.append(question)
            kept_embeddings.append(embedding)

    return kept


def filter_against_existing(
    new_questions: list[dict],
    existing_questions: list[dict]
) -> list[dict]:
    """Lọc câu hỏi mới trùng với câu hỏi đã có trong ngân hàng."""
    if not existing_questions:
        return new_questions

    model = get_model()

    existing_texts = [q["question"] for q in existing_questions]
    new_texts = [q["question"] for q in new_questions]

    existing_embeddings = model.encode(existing_texts, convert_to_tensor=True, show_progress_bar=False)
    new_embeddings = model.encode(new_texts, convert_to_tensor=True, show_progress_bar=False)

    kept = []
    for question, embedding in zip(new_questions, new_embeddings):
        similarities = util.cos_sim(embedding.unsqueeze(0), existing_embeddings)[0]
        max_similarity = similarities.max().item()

        if max_similarity < SIMILARITY_THRESHOLD:
            kept.append(question)

    return kept