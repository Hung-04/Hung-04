"""
Camera module với tối ưu hóa cho Intel i5-1135G7
VERSION: FIXED - Sửa lỗi Flask application context
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time
import os

from config import (
    CAMERA_INDEX, FRAME_SKIP, RECOGNITION_CACHE_TTL,
    DETECTION_RESIZE_WIDTH, CAMERA_WIDTH, CAMERA_HEIGHT,
    CAMERA_FPS, CAMERA_BUFFER_SIZE, JPEG_QUALITY,
    SHOW_FPS, DEBUG
)

# Lazy import để tránh load nặng khi không cần
_face_recognizer = None
_face_db = None
_detector = None
_app = None  # ← THÊM: Flask app instance


def get_face_recognizer():
    """Lazy load face recognizer"""
    global _face_recognizer
    if _face_recognizer is None:
        from face_recognition import face_recognizer
        _face_recognizer = face_recognizer
        print("✅ Face recognizer loaded")
    return _face_recognizer


def get_face_db():
    """Lazy load face database"""
    global _face_db
    if _face_db is None:
        from face_recognition import face_db
        _face_db = face_db
        stats = _face_db.get_statistics()
        print(f"✅ Face DB loaded: {stats['total_employees']} employees, {stats['total_embeddings']} embeddings")
    return _face_db


def get_detector():
    """Lazy load InsightFace detector"""
    global _detector
    if _detector is None:
        try:
            from insightface.app import FaceAnalysis
            print("🔄 Initializing InsightFace detector...")
            _detector = FaceAnalysis(
                name="buffalo_l",
                providers=["CPUExecutionProvider"]
            )
            _detector.prepare(ctx_id=-1, det_size=(256, 256))
            print("✅ Face detector initialized successfully!")
        except Exception as e:
            print(f"❌ Cannot initialize detector: {e}")
            import traceback
            traceback.print_exc()
            _detector = None
    return _detector


def set_app(app):
    """Set Flask app instance để sử dụng app context"""
    global _app
    _app = app
    print("✅ Flask app instance set for camera module")


def get_camera():
    """Khởi tạo camera"""
    camera = cv2.VideoCapture(CAMERA_INDEX)

    if not camera.isOpened():
        camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

    if camera.isOpened():
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_BUFFER_SIZE)
        camera.set(cv2.CAP_PROP_AUTOFOCUS, 0)
        print(f"📹 Camera initialized: {CAMERA_WIDTH}x{CAMERA_HEIGHT} @ {CAMERA_FPS}fps")
    else:
        print("❌ Cannot open camera!")

    return camera


def gen_frames():
    """Generator stream video frames KHÔNG có nhận diện"""
    camera = get_camera()

    try:
        while True:
            success, frame = camera.read()
            if not success:
                break

            ret, buffer = cv2.imencode('.jpg', frame,
                                       [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    finally:
        camera.release()
        print("📹 Camera released (gen_frames)")


def get_employee_info(ma_nv):
    """
    Lấy thông tin nhân viên từ database với Flask app context

    Args:
        ma_nv: Mã nhân viên

    Returns:
        dict: {'ma_nv': str, 'ho_ten': str} hoặc None
    """
    global _app

    if _app is None:
        print("⚠️ [DEBUG] Flask app not set, cannot query database")
        return None

    try:
        # Sử dụng app context để truy cập database
        with _app.app_context():
            from model import NhanVien
            nv = NhanVien.query.filter_by(ma_nv=ma_nv).first()

            if nv:
                return {
                    'ma_nv': nv.ma_nv,
                    'ho_ten': nv.ho_ten
                }
            else:
                print(f"⚠️ [DEBUG] Employee {ma_nv} not found in database")
                return None

    except Exception as e:
        print(f"❌ [DEBUG] Error querying employee info: {e}")
        import traceback
        traceback.print_exc()
        return None


def detect_and_recognize_simple(frame, detector, face_recognizer, face_db):
    """
    Version đơn giản hóa với debug logging
    ✅ SỬA LỖI: Sử dụng app context để truy cập database
    ✅ CHỈ TRẢ VỀ KẾT QUẢ KHI NHẬN DIỆN ĐƯỢC NHÂN VIÊN
    """
    try:
        print("🔍 [DEBUG] Starting face detection...")

        # Resize frame
        height, width = frame.shape[:2]
        scale = DETECTION_RESIZE_WIDTH / width
        small_frame = cv2.resize(frame, None, fx=scale, fy=scale,
                                 interpolation=cv2.INTER_LINEAR)

        print(f"🔍 [DEBUG] Frame resized: {frame.shape} -> {small_frame.shape}")

        # Detect faces
        faces = detector.get(small_frame)
        print(f"🔍 [DEBUG] Detected {len(faces)} faces")

        if len(faces) == 0:
            return None

        # Lấy face lớn nhất
        face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))

        # Scale bbox về kích thước gốc
        bbox = (face.bbox / scale).astype(int).tolist()
        x1, y1, x2, y2 = bbox

        # Clamp bbox
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)

        print(f"🔍 [DEBUG] Bbox: [{x1}, {y1}, {x2}, {y2}]")

        # Align face
        from insightface.utils import face_align
        kps_scaled = face.kps / scale
        aligned = face_align.norm_crop(frame, kps_scaled)

        if aligned is None or aligned.size == 0:
            print("⚠️ [DEBUG] Face alignment failed - NOT showing bbox")
            return None

        # Extract embedding
        rgb_aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_aligned)

        import torch
        img_tensor = face_recognizer.transform(pil_image).unsqueeze(0).to(face_recognizer.device)

        with torch.no_grad():
            embedding = face_recognizer.model(img_tensor)
            embedding = embedding.cpu().numpy()[0]

        print("🔍 [DEBUG] Embedding extracted")

        # Search in database
        ma_nv, similarity = face_db.search_face(embedding, threshold=0.55)

        print(f"🔍 [DEBUG] Search result: ma_nv={ma_nv}, similarity={similarity:.2%}")

        if ma_nv is not None:
            # ✅ SỬA LỖI: Sử dụng hàm get_employee_info với app context
            employee_info = get_employee_info(ma_nv)

            if employee_info:
                print(f"✅ [DEBUG] Recognized: {employee_info['ho_ten']} ({employee_info['ma_nv']}) - SHOWING bbox")
                return {
                    'bbox': [x1, y1, x2, y2],
                    'ma_nv': employee_info['ma_nv'],
                    'ho_ten': employee_info['ho_ten'],
                    'similarity': similarity
                }
            else:
                # Nếu không query được từ DB, vẫn trả về với ma_nv
                print(f"⚠️ [DEBUG] Cannot get employee info from DB, using ma_nv only")
                return {
                    'bbox': [x1, y1, x2, y2],
                    'ma_nv': ma_nv,
                    'ho_ten': ma_nv,  # Dùng ma_nv làm fallback
                    'similarity': similarity
                }

        # Không nhận diện được - KHÔNG TRẢ VỀ KẾT QUẢ
        print(f"⚠️ [DEBUG] Face not recognized (similarity: {similarity:.2%}) - NOT showing bbox")
        return None

    except Exception as e:
        print(f"❌ [DEBUG] Error in detect_and_recognize: {e}")
        import traceback
        traceback.print_exc()
        return None


def draw_bbox_simple(frame, result):
    """
    Version đơn giản - vẽ bounding box và thông tin nhân viên
    ✅ Chỉ được gọi khi result != None (tức đã nhận diện được)
    """
    if result is None:
        return frame

    print(f"🎨 [DEBUG] Drawing bbox for: {result['ma_nv']}")

    x1, y1, x2, y2 = result['bbox']

    # Màu box xanh (đã nhận diện được)
    color = (0, 255, 0)

    # Vẽ bounding box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

    # Font cho text
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Text phía trên: Mã NV và độ tương đồng
    top_text = f"{result['ma_nv']} ({result['similarity']:.0%})"
    cv2.putText(frame, top_text, (x1, y1 - 10),
                font, 0.7, color, 2, cv2.LINE_AA)

    # Text phía dưới: Tên nhân viên (nếu có)
    if 'ho_ten' in result and result['ho_ten'] and result['ho_ten'] != result['ma_nv']:
        # Để hiển thị tiếng Việt đúng, cần dùng PIL
        # Tạm thời hiển thị mã NV
        name_text = result['ma_nv']
        cv2.putText(frame, name_text, (x1, y2 + 25),
                    font, 0.7, color, 2, cv2.LINE_AA)

    print(f"✅ [DEBUG] Bbox drawn successfully")
    return frame


def gen_frames_with_recognition():
    """
    Generator với recognition - VERSION FIXED với Flask app context
    ✅ Chỉ hiện bounding box khi nhận diện được nhân viên
    """
    print("\n" + "="*60)
    print("🎬 STARTING VIDEO FEED WITH RECOGNITION (FIXED MODE)")
    print("✅ Bounding box CHỈ hiện khi nhận diện được nhân viên")
    print("="*60)

    camera = get_camera()

    # Khởi tạo components
    print("🔧 Initializing components...")
    detector = get_detector()
    face_recognizer = get_face_recognizer()
    face_db = get_face_db()

    if detector is None:
        print("❌ Detector not available, falling back to simple streaming")
        for frame_data in gen_frames():
            yield frame_data
        return

    if face_recognizer is None:
        print("❌ Face recognizer not available")
        for frame_data in gen_frames():
            yield frame_data
        return

    print("✅ All components initialized successfully")
    print(f"📊 Face DB: {len(face_db.get_all_employees())} employees registered")
    print("="*60 + "\n")

    # Variables
    frame_count = 0
    last_result = None
    result_ttl = 0
    last_detection_time = time.time()

    # FPS tracking
    fps_start_time = time.time()
    fps_frame_count = 0
    current_fps = 0

    try:
        while True:
            success, frame = camera.read()
            if not success:
                break

            frame_count += 1
            fps_frame_count += 1

            # Tính FPS
            if time.time() - fps_start_time >= 1.0:
                current_fps = fps_frame_count
                fps_frame_count = 0
                fps_start_time = time.time()

            # Nhận diện sau mỗi FRAME_SKIP frames
            should_detect = (frame_count % FRAME_SKIP == 0)

            if should_detect:
                detection_start = time.time()
                result = detect_and_recognize_simple(frame, detector, face_recognizer, face_db)
                detection_time = (time.time() - detection_start) * 1000

                print(f"⏱️ [DEBUG] Detection took {detection_time:.0f}ms")

                if result is not None:
                    # ✅ Có kết quả nhận diện thành công
                    last_result = result
                    result_ttl = RECOGNITION_CACHE_TTL
                    print(f"✅ [DEBUG] Result cached for {result_ttl} frames")
                else:
                    # ❌ Không nhận diện được hoặc không có face
                    result_ttl = max(0, result_ttl - 1)
                    if result_ttl == 0:
                        last_result = None
            else:
                result_ttl = max(0, result_ttl - 1)
                if result_ttl == 0:
                    last_result = None

            # Vẽ bounding box - CHỈ KHI CÓ KẾT QUẢ (last_result != None)
            if last_result is not None:
                frame = draw_bbox_simple(frame, last_result)

            # Hiển thị FPS
            if SHOW_FPS and current_fps > 0:
                fps_text = f"FPS: {current_fps}"
                cv2.putText(frame, fps_text, (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame,
                                       [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            if not ret:
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    except Exception as e:
        print(f"❌ Error in gen_frames_with_recognition: {e}")
        import traceback
        traceback.print_exc()

    finally:
        camera.release()
        print("📹 Camera released (gen_frames_with_recognition)")


# Export
__all__ = ['gen_frames', 'gen_frames_with_recognition', 'get_camera', 'set_app']