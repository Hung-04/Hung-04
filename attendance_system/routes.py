from flask import render_template, request, jsonify, Response
from app import app, db
from model import NhanVien, ChamCong, KhuonMat, get_vietnam_time
from camera import gen_frames, gen_frames_with_recognition
from datetime import datetime, date
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
from PIL import Image
import base64
from io import BytesIO
import pytz
import shutil
import json  # ✅ Thêm import json để xử lý encoding UTF-8

# Import face recognition
from face_recognition import face_recognizer, face_db

# Cấu hình upload
UPLOAD_FOLDER = 'face_data'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Timezone Việt Nam
vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def json_response(data, status=200):
    """
    Helper function để trả về JSON response với encoding UTF-8 đúng

    Args:
        data: Dictionary data để trả về
        status: HTTP status code

    Returns:
        Flask Response object với UTF-8 encoding
    """
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        mimetype='application/json; charset=utf-8',
        status=status
    )


@app.route("/")
def home():
    return render_template("home.html")


# ========= CAMERA =========
@app.route("/video_feed")
def video_feed():
    """Video feed thông thường không có nhận diện"""
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route("/video_feed_recognition")
def video_feed_recognition():
    """Video feed với nhận diện khuôn mặt realtime"""
    return Response(gen_frames_with_recognition(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ========= ATTENDANCE =========
@app.route("/attendance")
def attendance():
    return render_template("attendance.html")


@app.route("/api/attendance", methods=["POST"])
def api_attendance():
    """API endpoint cho check-in/check-out với nhận diện khuôn mặt"""
    try:
        data = request.json
        attendance_type = data.get("type")
        image_data = data.get("image")  # Base64 encoded image

        if not image_data:
            return jsonify({
                "success": False,
                "message": "Không có ảnh để nhận diện!"
            })

        # Debug: Reload database để đảm bảo có data mới nhất
        face_db.reload_database()

        # Debug: In thông tin database
        stats = face_db.get_statistics()
        print(f"🔍 Database stats: {stats['total_employees']} employees, {stats['total_embeddings']} embeddings")

        # Decode base64 image
        image_bytes = base64.b64decode(image_data.split(',')[1])
        image = Image.open(BytesIO(image_bytes))

        # Nhận diện khuôn mặt
        embedding, face_img, box = face_recognizer.process_image(image)

        if embedding is None:
            return jsonify({
                "success": False,
                "message": "Không phát hiện khuôn mặt trong ảnh!"
            })

        # Tìm kiếm trong database
        ma_nv, similarity = face_db.search_face(embedding, threshold=0.6)

        if ma_nv is None:
            return jsonify({
                "success": False,
                "message": f"Không nhận diện được khuôn mặt! (Độ tương đồng cao nhất: {similarity:.2%})"
            })

        # Tìm nhân viên
        nv = NhanVien.query.filter_by(ma_nv=ma_nv).first()
        if not nv:
            return jsonify({
                "success": False,
                "message": "Không tìm thấy thông tin nhân viên!"
            })

        # Tạo bản ghi chấm công với thời gian Việt Nam
        trang_thai = "Check-in" if attendance_type == "checkin" else "Check-out"
        vietnam_time = get_vietnam_time()

        # Chuyển về naive datetime để lưu vào SQL Server
        vietnam_time_naive = vietnam_time.replace(tzinfo=None)

        cc = ChamCong(
            nhanvien_id=nv.id,
            trang_thai=trang_thai,
            thoi_gian=vietnam_time_naive
        )
        db.session.add(cc)
        db.session.commit()

        print(f"✅ Attendance recorded: {nv.ho_ten} - {trang_thai} at {vietnam_time_naive}")

        return jsonify({
            "success": True,
            "message": f"{trang_thai} thành công!",
            "employee": nv.ho_ten,
            "ma_nv": nv.ma_nv,
            "time": vietnam_time_naive.strftime("%H:%M:%S"),
            "date": vietnam_time_naive.strftime("%Y-%m-%d"),
            "similarity": f"{similarity:.2%}"
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": f"Lỗi: {str(e)}"
        })


# ========= EMPLOYEES =========
@app.route("/employees")
def employees():
    return render_template("employees.html")


@app.route("/api/employees", methods=["GET", "POST"])
def api_employees():
    if request.method == "GET":
        # Lấy danh sách nhân viên (có thể tìm kiếm)
        keyword = request.args.get("key", "")

        if keyword:
            data = NhanVien.query.filter(
                (NhanVien.ma_nv.contains(keyword)) |
                (NhanVien.ho_ten.contains(keyword))
            ).all()
        else:
            data = NhanVien.query.all()

        # Đếm số ảnh đã đăng ký cho mỗi nhân viên
        result = []
        for n in data:
            face_count = len(face_db.get_embeddings(n.ma_nv))
            result.append({
                "id": n.id,
                "ma_nv": n.ma_nv,
                "ho_ten": n.ho_ten,
                "phong_ban": n.phong_ban,
                "chuc_vu": n.chuc_vu,
                "face_count": face_count
            })

        # ✅ FIX: ensure_ascii=False để hiển thị tiếng Việt đúng
        from flask import Response
        import json
        return Response(json.dumps(result, ensure_ascii=False), mimetype='application/json; charset=utf-8')

    elif request.method == "POST":
        # Thêm nhân viên mới
        try:
            data = request.json
            nv = NhanVien(
                ma_nv=data["ma_nv"],
                ho_ten=data["ho_ten"],
                phong_ban=data.get("phong_ban", ""),
                chuc_vu=data.get("chuc_vu", "")
            )
            db.session.add(nv)
            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Thêm nhân viên thành công!",
                "employee": {
                    "id": nv.id,
                    "ma_nv": nv.ma_nv,
                    "ho_ten": nv.ho_ten
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "success": False,
                "message": f"Lỗi: {str(e)}"
            })


@app.route("/api/employees/<int:id>", methods=["GET", "PUT", "DELETE"])
def manage_employee(id):
    """Quản lý nhân viên: Lấy thông tin, cập nhật, hoặc xóa"""

    if request.method == "GET":
        # Lấy thông tin chi tiết 1 nhân viên
        nv = NhanVien.query.get(id)
        if nv:
            return jsonify({
                "success": True,
                "employee": {
                    "id": nv.id,
                    "ma_nv": nv.ma_nv,
                    "ho_ten": nv.ho_ten,
                    "phong_ban": nv.phong_ban or "",
                    "chuc_vu": nv.chuc_vu or ""
                }
            })
        return jsonify({
            "success": False,
            "message": "Không tìm thấy nhân viên!"
        }), 404

    elif request.method == "PUT":
        # Cập nhật thông tin nhân viên
        try:
            nv = NhanVien.query.get(id)
            if not nv:
                return jsonify({
                    "success": False,
                    "message": "Không tìm thấy nhân viên!"
                }), 404

            data = request.get_json(force=True)  # force=True để đảm bảo parse UTF-8 đúng

            # Cập nhật các trường (không cho đổi mã NV)
            if "ho_ten" in data:
                nv.ho_ten = str(data["ho_ten"]).strip()
            if "phong_ban" in data:
                nv.phong_ban = str(data.get("phong_ban", "")).strip()
            if "chuc_vu" in data:
                nv.chuc_vu = str(data.get("chuc_vu", "")).strip()

            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Cập nhật thông tin nhân viên thành công!",
                "employee": {
                    "id": nv.id,
                    "ma_nv": nv.ma_nv,
                    "ho_ten": nv.ho_ten,
                    "phong_ban": nv.phong_ban,
                    "chuc_vu": nv.chuc_vu
                }
            })
        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "message": f"Lỗi: {str(e)}"
            }), 500

    elif request.method == "DELETE":
        # Xóa nhân viên
        try:
            nv = NhanVien.query.get(id)
            if not nv:
                return jsonify({
                    "success": False,
                    "message": "Không tìm thấy nhân viên!"
                }), 404

            ma_nv = nv.ma_nv
            ho_ten = nv.ho_ten

            print(f"🗑️ Deleting employee: {ma_nv} - {ho_ten}")

            # Bước 1: Xóa embeddings trong face_db (pickle file)
            try:
                face_db.remove_employee(ma_nv)
                print(f"✅ Removed embeddings for {ma_nv}")
            except Exception as e:
                print(f"⚠️ Warning: Could not remove embeddings: {e}")

            # Bước 2: Xóa folder ảnh
            employee_folder = os.path.join(UPLOAD_FOLDER, ma_nv)
            if os.path.exists(employee_folder):
                try:
                    import shutil
                    shutil.rmtree(employee_folder)
                    print(f"✅ Removed folder: {employee_folder}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not remove folder: {e}")

            # Bước 3: Xóa bản ghi KhuonMat trong SQL (nếu cascade không hoạt động)
            try:
                KhuonMat.query.filter_by(nhanvien_id=nv.id).delete()
                print(f"✅ Removed face records for employee {nv.id}")
            except Exception as e:
                print(f"⚠️ Warning: Could not remove face records: {e}")

            # Bước 4: Xóa bản ghi ChamCong trong SQL (nếu cascade không hoạt động)
            try:
                ChamCong.query.filter_by(nhanvien_id=nv.id).delete()
                print(f"✅ Removed attendance records for employee {nv.id}")
            except Exception as e:
                print(f"⚠️ Warning: Could not remove attendance records: {e}")

            # Bước 5: Xóa bản ghi NhanVien
            db.session.delete(nv)
            db.session.commit()

            print(f"✅ Successfully deleted employee: {ho_ten}")

            return jsonify({
                "success": True,
                "message": f"Đã xóa nhân viên {ho_ten}!"
            })

        except Exception as e:
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return jsonify({
                "success": False,
                "message": f"Lỗi khi xóa nhân viên: {str(e)}"
            }), 500


# ========= FACE REGISTRATION =========
@app.route("/register_face/<ma_nv>")
def register_face(ma_nv):
    """Trang đăng ký khuôn mặt cho nhân viên"""
    nv = NhanVien.query.filter_by(ma_nv=ma_nv).first()
    if not nv:
        return "Không tìm thấy nhân viên!", 404

    # Đếm số ảnh đã đăng ký
    face_count = len(face_db.get_embeddings(ma_nv))

    from config import MAX_FACES_PER_EMPLOYEE

    return render_template("register_face.html",
                           employee=nv,
                           face_count=face_count,
                           max_faces=MAX_FACES_PER_EMPLOYEE)


@app.route("/api/register_face", methods=["POST"])
def api_register_face():
    """API đăng ký khuôn mặt - upload ảnh hoặc chụp từ webcam"""
    try:
        # Lấy mã nhân viên từ form hoặc JSON
        ma_nv = request.form.get("ma_nv")
        if not ma_nv:
            # Thử lấy từ JSON nếu không có trong form
            data = request.get_json() or {}
            employee_id = data.get("employee_id")
            if employee_id:
                # Tìm nhân viên theo ID
                nv = NhanVien.query.get(employee_id)
                if nv:
                    ma_nv = nv.ma_nv

        if not ma_nv:
            return jsonify({
                "success": False,
                "message": "Vui lòng cung cấp mã nhân viên!"
            })

        # Kiểm tra nhân viên có tồn tại không
        nv = NhanVien.query.filter_by(ma_nv=ma_nv).first()
        if not nv:
            return jsonify({
                "success": False,
                "message": "Không tìm thấy nhân viên với mã này!"
            })

        # Tạo folder cho nhân viên
        employee_folder = os.path.join(UPLOAD_FOLDER, ma_nv)
        os.makedirs(employee_folder, exist_ok=True)

        # Xử lý ảnh từ webcam (base64) hoặc upload file
        image = None
        filename = None

        # Kiểm tra có file upload không
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Tạo tên file unique
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{timestamp}_{filename}"
                filepath = os.path.join(employee_folder, filename)
                file.save(filepath)
                image = Image.open(filepath)

        # Kiểm tra có ảnh từ webcam không (từ JSON)
        elif request.is_json:
            data = request.get_json()
            image_data = data.get('image')
            if image_data:
                image_bytes = base64.b64decode(image_data.split(',')[1])
                image = Image.open(BytesIO(image_bytes))

                # Lưu ảnh
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"webcam_{timestamp}.jpg"
                filepath = os.path.join(employee_folder, filename)
                image.save(filepath)

        if image is None:
            return jsonify({
                "success": False,
                "message": "Không có ảnh để xử lý!"
            })

        # Xử lý ảnh và tạo embedding
        embedding, face_img, box = face_recognizer.process_image(image)

        if embedding is None:
            # Xóa file ảnh nếu không detect được face
            if filename and 'filepath' in locals():
                if os.path.exists(filepath):
                    os.remove(filepath)
            return jsonify({
                "success": False,
                "message": "Không phát hiện khuôn mặt trong ảnh! Vui lòng chụp lại."
            })

        # Lưu ảnh face đã crop
        face_filename = f"face_{filename}"
        face_filepath = os.path.join(employee_folder, face_filename)
        face_img.save(face_filepath)

        # Lưu embedding vào database
        face_db.add_embedding(ma_nv, embedding)

        # Lưu vào SQL database với thời gian Việt Nam
        vietnam_time = get_vietnam_time()
        vietnam_time_naive = vietnam_time.replace(tzinfo=None)

        khuon_mat = KhuonMat(
            nhanvien_id=nv.id,
            embedding=embedding.tobytes(),
            ngay_tao=vietnam_time_naive
        )
        db.session.add(khuon_mat)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Đăng ký khuôn mặt thành công cho {nv.ho_ten}!",
            "image_path": face_filepath,
            "face_count": len(face_db.get_embeddings(ma_nv))
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Lỗi: {str(e)}"
        })


@app.route("/api/get_employee_faces/<ma_nv>")
def get_employee_faces(ma_nv):
    """Lấy danh sách ảnh đã đăng ký của nhân viên"""
    try:
        employee_folder = os.path.join(UPLOAD_FOLDER, ma_nv)
        if not os.path.exists(employee_folder):
            return jsonify([])

        faces = []
        for filename in os.listdir(employee_folder):
            if filename.startswith('face_'):
                faces.append({
                    "filename": filename,
                    "path": os.path.join(employee_folder, filename)
                })

        return jsonify(faces)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========= HISTORY =========
@app.route("/history")
def history():
    return render_template("history.html")


@app.route("/api/history")
def history_data():
    """Lấy lịch sử chấm công"""
    try:
        date_str = request.args.get("date")
        ma_nv = request.args.get("ma_nv")

        print(f"🔍 API /api/history called with date={date_str}, ma_nv={ma_nv}")

        query = ChamCong.query.join(NhanVien)

        # Filter theo date nếu có
        if date_str:
            try:
                # Parse date string
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                print(f"📅 Filtering by date: {date_obj}")

                # Filter by date (comparing only date part, ignoring time)
                query = query.filter(db.func.cast(ChamCong.thoi_gian, db.Date) == date_obj)
            except ValueError as e:
                print(f"❌ Invalid date format: {e}")
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Filter theo mã nhân viên nếu có
        if ma_nv:
            query = query.filter(NhanVien.ma_nv == ma_nv)

        # Sắp xếp theo thời gian mới nhất
        rows = query.order_by(ChamCong.thoi_gian.desc()).all()

        print(f"📊 Found {len(rows)} attendance records")

        result = []
        for r in rows:
            record = {
                "id": r.id,
                "ma_nv": r.nhanvien.ma_nv,
                "ho_ten": r.nhanvien.ho_ten,
                "time": r.thoi_gian.strftime("%Y-%m-%d %H:%M:%S"),
                "date": r.thoi_gian.strftime("%Y-%m-%d"),
                "status": r.trang_thai
            }
            result.append(record)
            print(f"  - {record['ma_nv']}: {record['time']} - {record['status']}")

        # ✅ Sử dụng json_response để đảm bảo UTF-8
        return json_response(result)

    except Exception as e:
        import traceback
        print(f"❌ Error in /api/history:")
        traceback.print_exc()
        return json_response({"error": str(e)}, status=500)


@app.route("/api/history/summary")
def history_summary():
    """Tổng hợp lịch sử chấm công theo ngày"""
    try:
        date_str = request.args.get("date")

        if not date_str:
            return jsonify({"error": "Missing date parameter"}), 400

        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Lấy tất cả bản ghi trong ngày
        records = ChamCong.query.join(NhanVien).filter(
            db.func.cast(ChamCong.thoi_gian, db.Date) == date_obj
        ).order_by(NhanVien.ma_nv, ChamCong.thoi_gian).all()

        # Group theo nhân viên
        summary = {}
        for r in records:
            if r.nhanvien.ma_nv not in summary:
                summary[r.nhanvien.ma_nv] = {
                    "ma_nv": r.nhanvien.ma_nv,
                    "ho_ten": r.nhanvien.ho_ten,
                    "checkin": None,
                    "checkout": None,
                    "work_hours": 0
                }

            if r.trang_thai == "Check-in":
                if summary[r.nhanvien.ma_nv]["checkin"] is None:
                    summary[r.nhanvien.ma_nv]["checkin"] = r.thoi_gian.strftime("%H:%M:%S")
            elif r.trang_thai == "Check-out":
                summary[r.nhanvien.ma_nv]["checkout"] = r.thoi_gian.strftime("%H:%M:%S")

        # Tính giờ làm việc
        for data in summary.values():
            if data["checkin"] and data["checkout"]:
                checkin_time = datetime.strptime(data["checkin"], "%H:%M:%S")
                checkout_time = datetime.strptime(data["checkout"], "%H:%M:%S")
                diff = checkout_time - checkin_time
                data["work_hours"] = round(diff.total_seconds() / 3600, 2)

        return jsonify(list(summary.values()))

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ========= API MỚI: XÓA ĐĂNG KÝ KHUÔN MẶT =========
@app.route("/api/delete_face/<int:employee_id>", methods=["DELETE"])
def delete_face_registration(employee_id):
    """
    Xóa toàn bộ đăng ký khuôn mặt của nhân viên
    """
    try:
        # Tìm nhân viên
        nv = NhanVien.query.get(employee_id)
        if not nv:
            return jsonify({
                "success": False,
                "message": "Không tìm thấy nhân viên!"
            }), 404

        ma_nv = nv.ma_nv

        # 1. Xóa embeddings từ face_db (file pickle)
        removed_from_db = face_db.remove_employee(ma_nv)

        # 2. Xóa bản ghi KhuonMat trong SQL database
        deleted_count = KhuonMat.query.filter_by(nhanvien_id=employee_id).delete()
        db.session.commit()

        # 3. Xóa thư mục chứa ảnh
        face_folder = os.path.join(UPLOAD_FOLDER, ma_nv)
        folder_deleted = False
        if os.path.exists(face_folder):
            shutil.rmtree(face_folder)
            folder_deleted = True
            print(f"✅ Deleted folder: {face_folder}")

        return jsonify({
            "success": True,
            "message": f"Đã xóa đăng ký khuôn mặt của {nv.ho_ten}!",
            "details": {
                "removed_from_pickle": removed_from_db,
                "deleted_sql_records": deleted_count,
                "deleted_folder": folder_deleted
            }
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Lỗi khi xóa đăng ký khuôn mặt: {str(e)}"
        }), 500


# ========= API MỚI: LỊCH SỬ VỚI TỔNG THỜI GIAN =========
@app.route("/api/history/with_duration")
def history_with_duration():
    """
    Lấy lịch sử chấm công kèm tính tổng thời gian làm việc
    Tính từ check-in gần nhất đến check-out
    """
    try:
        date_str = request.args.get("date")
        ma_nv = request.args.get("ma_nv")

        query = ChamCong.query.join(NhanVien)

        # Filter theo date nếu có
        if date_str:
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                query = query.filter(db.func.cast(ChamCong.thoi_gian, db.Date) == date_obj)
            except ValueError:
                return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

        # Filter theo mã nhân viên nếu có
        if ma_nv:
            query = query.filter(NhanVien.ma_nv == ma_nv)

        # Sắp xếp theo nhân viên và thời gian
        rows = query.order_by(NhanVien.ma_nv, ChamCong.thoi_gian).all()

        # Group theo nhân viên để tính duration
        employee_records = {}
        for r in rows:
            if r.nhanvien.ma_nv not in employee_records:
                employee_records[r.nhanvien.ma_nv] = {
                    'info': r.nhanvien,
                    'checkins': [],
                    'checkouts': []
                }

            if r.trang_thai == "Check-in":
                employee_records[r.nhanvien.ma_nv]['checkins'].append(r)
            else:
                employee_records[r.nhanvien.ma_nv]['checkouts'].append(r)

        # Tạo result với duration
        result = []
        for ma_nv, data in employee_records.items():
            # Lấy check-in gần nhất và check-out gần nhất
            checkins = sorted(data['checkins'], key=lambda x: x.thoi_gian, reverse=True)
            checkouts = sorted(data['checkouts'], key=lambda x: x.thoi_gian, reverse=True)

            last_checkin = checkins[0] if checkins else None
            last_checkout = checkouts[0] if checkouts else None

            # Tính duration
            duration_seconds = 0
            duration_str = ""

            if last_checkin and last_checkout:
                # Chỉ tính nếu check-out sau check-in
                if last_checkout.thoi_gian > last_checkin.thoi_gian:
                    time_diff = last_checkout.thoi_gian - last_checkin.thoi_gian
                    duration_seconds = int(time_diff.total_seconds())

                    # Format duration thành giờ và phút
                    hours = duration_seconds // 3600
                    minutes = (duration_seconds % 3600) // 60
                    duration_str = f"{hours}h {minutes}m"

            # Thêm tất cả bản ghi vào result
            for r in checkins + checkouts:
                result.append({
                    "id": r.id,
                    "ma_nv": r.nhanvien.ma_nv,
                    "ho_ten": r.nhanvien.ho_ten,
                    "time": r.thoi_gian.strftime("%Y-%m-%d %H:%M:%S"),
                    "date": r.thoi_gian.strftime("%Y-%m-%d"),
                    "status": r.trang_thai,
                    # Chỉ hiển thị duration ở dòng check-out cuối cùng
                    "duration": duration_str if (r == last_checkout and duration_str) else "",
                    "duration_seconds": duration_seconds if (r == last_checkout) else 0
                })

        # Sort theo thời gian mới nhất
        result.sort(key=lambda x: x['time'], reverse=True)

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500