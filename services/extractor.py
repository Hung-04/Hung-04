import fitz
from docx import Document
import re


def extract_text(file_path: str, file_type: str) -> str:
    if file_type == "pdf":
        return extract_from_pdf(file_path)
    elif file_type == "docx":
        return extract_from_docx(file_path)
    elif file_type == "txt":
        return extract_from_txt(file_path)
    else:
        raise ValueError(f"Định dạng không hỗ trợ: {file_type}")


def extract_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)
    doc.close()
    return clean_text("\n".join(pages))


def extract_from_docx(path: str) -> str:
    doc = Document(path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return clean_text("\n".join(paragraphs))


def extract_from_txt(path: str) -> str:
    encodings = ["utf-8", "utf-16", "cp1252", "latin-1"]
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                return clean_text(f.read())
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError("Không thể đọc file TXT — encoding không được hỗ trợ.")


def clean_text(text: str) -> str:
    # Xóa ký tự null và không in được
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # Chuẩn hóa khoảng trắng trên cùng 1 dòng
    text = re.sub(r'[ \t]+', ' ', text)
    # Giới hạn xuống dòng liên tiếp tối đa 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()