import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
import uuid
import shutil
import unicodedata
from services.extractor import extract_text
from services.chunker import split_text
from services.embedder import index_chunks
from services.embedder import delete_chunks_by_doc


router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
os.makedirs(UPLOAD_DIR, exist_ok=True)


def decode_filename(filename):
    """
    Decode filename with proper Vietnamese encoding handling.
    Handles multiple encoding scenarios.
    """
    if not filename:
        return filename
    
    print(f"DEBUG DECODE: Input filename repr: {repr(filename)}")
    
    # If already has Vietnamese characters, return as-is
    vietnamese_pattern = re.compile(r'[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]')
    
    if vietnamese_pattern.search(filename):
        print(f"DEBUG DECODE: Already has Vietnamese chars, returning as-is")
        return filename
    
    # Try multiple encoding fixes
    encodings_to_try = ['latin-1', 'windows-1252', 'iso-8859-1', 'cp1252']
    
    for enc in encodings_to_try:
        try:
            # Encode to bytes using the encoding, then decode as UTF-8
            bytes_data = filename.encode(enc)
            decoded = bytes_data.decode('utf-8')
            
            if vietnamese_pattern.search(decoded):
                print(f"DEBUG DECODE: Fixed using {enc}->UTF-8: {decoded}")
                return decoded
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            print(f"DEBUG DECODE: {enc} failed: {e}")
            continue
    
    # Try NFC normalization (combining characters)
    try:
        normalized = unicodedata.normalize('NFC', filename)
        if vietnamese_pattern.search(normalized):
            print(f"DEBUG DECODE: Fixed using NFC normalization: {normalized}")
            return normalized
    except Exception as e:
        print(f"DEBUG DECODE: NFC normalization failed: {e}")
    
    print(f"DEBUG DECODE: No fix applied, returning original: {filename}")
    return filename


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Decode filename with proper encoding
    original_filename = file.filename
    fixed_filename = decode_filename(original_filename)
    
    print(f"DEBUG UPLOAD: Original: {repr(original_filename)}")
    print(f"DEBUG UPLOAD: Fixed: {repr(fixed_filename)}")
    
    ext = fixed_filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng không hỗ trợ. Chỉ chấp nhận: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    doc_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{doc_id}.{ext}")
    
    # Save file with proper encoding in name
    try:
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        print(f"DEBUG UPLOAD: Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi lưu file: {str(e)}")

    try:
        text = extract_text(save_path, ext)
    except Exception as e:
        os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Lỗi trích xuất văn bản: {str(e)}")

    if not text.strip():
        os.remove(save_path)
        raise HTTPException(status_code=400, detail="Tài liệu không có nội dung văn bản.")

    chunks = split_text(text)
    if not chunks:
        os.remove(save_path)
        raise HTTPException(status_code=400, detail="Không thể chia đoạn tài liệu.")

    try:
        index_chunks(doc_id, chunks)
    except Exception as e:
        os.remove(save_path)
        raise HTTPException(status_code=500, detail=f"Lỗi lưu vector DB: {str(e)}")

    # Save to database
    try:
        document = models.Document(
            id=doc_id,
            filename=fixed_filename,
            file_type=ext,
            num_chunks=len(chunks)
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        print(f"DEBUG UPLOAD: Saved to DB with filename: {repr(document.filename)}")
    except Exception as e:
        print(f"DEBUG UPLOAD: Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi lưu database: {str(e)}")

    return {
        "message": "Tải lên thành công",
        "doc_id": doc_id,
        "filename": fixed_filename,
        "num_chunks": len(chunks)
    }


@router.get("/documents")
def get_documents(db: Session = Depends(get_db)):
    docs = db.query(models.Document).order_by(models.Document.created_at.desc()).all()
    
    result = []
    for d in docs:
        # Re-decode filename when returning (in case DB stored it wrong)
        filename = decode_filename(d.filename) if d.filename else ""
        
        result.append({
            "doc_id": str(d.id),
            "filename": filename,
            "file_type": d.file_type,
            "num_chunks": d.num_chunks,
            "created_at": d.created_at.isoformat() if d.created_at else None
        })
    
    print(f"DEBUG API: Returning {len(result)} documents")
    for r in result:
        print(f"DEBUG API: {r['doc_id']} - {repr(r['filename'])}")
    
    return result


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(models.Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

    db.delete(doc)
    db.commit()

    for ext in ALLOWED_EXTENSIONS:
        path = os.path.join(UPLOAD_DIR, f"{doc_id}.{ext}")
        if os.path.exists(path):
            os.remove(path)

    delete_chunks_by_doc(doc_id)
    return {"message": "Đã xóa tài liệu thành công."}
