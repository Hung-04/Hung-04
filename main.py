import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from database import engine, Base
import models

from api.upload import router as upload_router
from api.generate import router as generate_router
from api.questions import router as questions_router

# Đường dẫn tuyệt đối đến thư mục app/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print("✅ Kết nối SQL Server thành công — bảng đã sẵn sàng.")
    yield
    print("🔴 Ứng dụng đã dừng.")


app = FastAPI(
    title="Question Bank API",
    description="Hệ thống sinh câu hỏi trắc nghiệm và tự luận từ tài liệu sử dụng RAG + LLM",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(upload_router,    prefix="/api", tags=["Upload"])
app.include_router(generate_router,  prefix="/api", tags=["Generate"])
app.include_router(questions_router, prefix="/api", tags=["Questions"])

# Tạo thư mục static nếu chưa có và mount
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return {"error": f"Không tìm thấy file tại: {index_path}"}
    return FileResponse(index_path)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)