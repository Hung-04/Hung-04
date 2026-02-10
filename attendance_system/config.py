import urllib

# ============================================
# DATABASE CONFIGURATION
# ============================================
SERVER = "HUM\\SQLEXPRESS"
DATABASE = "ChamCongKhuonMat"
USERNAME = "sa"
PASSWORD = "123456"  # Thay đổi mật khẩu của bạn
DRIVER = "ODBC Driver 17 for SQL Server"

# Connection string với UTF-8 support
params = urllib.parse.quote_plus(
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={SERVER};"
    f"DATABASE={DATABASE};"
    f"UID={USERNAME};"
    f"PWD={PASSWORD};"
    f"TrustServerCertificate=yes;"
    f"CHARSET=UTF8;"  # ← FIX LỖI TIẾNG VIỆT
)

SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc:///?odbc_connect={params}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Engine options để đảm bảo UTF-8
SQLALCHEMY_ENGINE_OPTIONS = {
    'connect_args': {
        'charset': 'utf8'
    },
    'pool_pre_ping': True,  # Kiểm tra connection trước khi dùng
    'pool_recycle': 3600,   # Recycle connection mỗi giờ
}

# ============================================
# CAMERA CONFIGURATION
# ============================================
CAMERA_INDEX = 0

# ============================================
# PERFORMANCE SETTINGS - TỐI ƯU CHO i5-1135G7
# ============================================

# Frame processing (Tối ưu để giảm lag - giảm xuống 2 frames)
FRAME_SKIP = 2  # Nhận diện mỗi 2 frames (mượt hơn)
RECOGNITION_CACHE_TTL = 15  # Cache 15 frames (smooth hơn)

# Detection settings (Tối ưu cho CPU Intel Gen 11)
DETECTION_RESIZE_WIDTH = 480  # Resize về 480px (cân bằng tốc độ/chính xác)
DETECTION_SIZE = (320, 320)   # Detection model size

# Camera settings
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CAMERA_BUFFER_SIZE = 1  # Giảm lag

# JPEG encoding quality (90% = chất lượng cao hơn)
JPEG_QUALITY = 90

# ============================================
# FACE RECOGNITION SETTINGS
# ============================================
FACES_DIR = "face_data"  # Thư mục lưu ảnh khuôn mặt
SIMILARITY_THRESHOLD = 0.55  # Ngưỡng nhận diện
MAX_FACES_PER_EMPLOYEE = 10  # Số ảnh tối đa mỗi nhân viên

# ============================================
# THREADING SETTINGS
# ============================================
USE_THREADING = True  # Sử dụng threading để tăng performance
MAX_WORKERS = 2  # Số threads xử lý song song

# ============================================
# DEBUG SETTINGS
# ============================================
DEBUG = False  # Set True để xem thông tin debug
SHOW_FPS = True  # Hiển thị FPS trên video
SHOW_PERFORMANCE_STATS = False  # Hiển thị CPU/RAM stats