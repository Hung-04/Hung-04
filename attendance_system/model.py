from app import db
from datetime import datetime
import pytz


# Múi giờ Việt Nam
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')


def get_vietnam_time():
    """Lấy thời gian hiện tại theo múi giờ Việt Nam"""
    return datetime.now(vietnam_tz)


class NhanVien(db.Model):
    __tablename__ = "NhanVien"
    __table_args__ = {'extend_existing': True}  # ✅ Cho phép redefine table

    id = db.Column(db.Integer, primary_key=True)
    ma_nv = db.Column(db.String(20), unique=True, nullable=False)
    ho_ten = db.Column(db.Unicode(100), nullable=False)  # ✅ FIX: Unicode thay vì String
    phong_ban = db.Column(db.Unicode(100))  # ✅ FIX: Unicode
    chuc_vu = db.Column(db.Unicode(100))  # ✅ FIX: Unicode
    trang_thai = db.Column(db.Boolean, default=True)

    # Relationship với cascade delete
    cham_cong = db.relationship('ChamCong', backref='nhanvien', lazy=True, cascade='all, delete-orphan')
    khuon_mat = db.relationship('KhuonMat', backref='nhanvien', lazy=True, cascade='all, delete-orphan')


class KhuonMat(db.Model):
    __tablename__ = "KhuonMat"

    id = db.Column(db.Integer, primary_key=True)
    nhanvien_id = db.Column(db.Integer, db.ForeignKey("NhanVien.id", ondelete='CASCADE'))
    embedding = db.Column(db.LargeBinary, nullable=False)
    ngay_tao = db.Column(db.DateTime, default=get_vietnam_time)


class ChamCong(db.Model):
    __tablename__ = "ChamCong"
    __table_args__ = {'extend_existing': True}  # ✅ Cho phép redefine table

    id = db.Column(db.Integer, primary_key=True)
    nhanvien_id = db.Column(db.Integer, db.ForeignKey("NhanVien.id", ondelete='CASCADE'))
    thoi_gian = db.Column(db.DateTime, default=get_vietnam_time)
    trang_thai = db.Column(db.Unicode(50))  # ✅ FIX: Unicode thay vì String