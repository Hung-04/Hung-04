"""
Flask Application - Hệ thống chấm công nhận diện khuôn mặt
Đã tối ưu hóa với UTF-8 support
VERSION: FIXED - Set app context cho camera module
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_ENGINE_OPTIONS

# Khởi tạo Flask app
app = Flask(__name__)

# ✅ FIX LỖI TIẾNG VIỆT: Cấu hình JSON encoding
app.config['JSON_AS_ASCII'] = False  # Cho phép hiển thị ký tự Unicode
app.config['JSON_SORT_KEYS'] = False

# Cấu hình database với UTF-8 support
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ QUAN TRỌNG: Engine options để hỗ trợ tiếng Việt
try:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS
    print("✅ Database engine configured with UTF-8 support")
except Exception as e:
    print(f"⚠️ Warning: Cannot set engine options: {e}")

# Khởi tạo SQLAlchemy
db = SQLAlchemy(app)

# Import models (sau khi db đã được khởi tạo)
from model import NhanVien, ChamCong, KhuonMat

# ✅ SỬA LỖI: Set Flask app instance cho camera module
# Phải làm điều này TRƯỚC khi import routes (vì routes sử dụng camera)
try:
    import camera
    camera.set_app(app)
    print("✅ Camera module configured with Flask app context")
except Exception as e:
    print(f"⚠️ Warning: Cannot set camera app context: {e}")

# Import routes (sau cùng)
import routes

# Print thông tin khi khởi động
print("\n" + "="*60)
print("🚀 HỆ THỐNG CHẤM CÔNG NHẬN DIỆN KHUÔN MẶT")
print("="*60)
print("✅ Flask app initialized")
print("✅ Database connected with UTF-8 encoding")
print("✅ JSON encoding: UTF-8 (ensure_ascii=False)")
print("✅ Camera module linked with app context")
print("✅ Routes registered")
print("="*60 + "\n")