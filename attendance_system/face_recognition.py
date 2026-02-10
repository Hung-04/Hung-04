"""
Module xử lý nhận diện khuôn mặt với ArcFace + ResNet18
"""
import torch
import numpy as np
from torchvision import transforms
from PIL import Image
import cv2
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import os

# Import model và detector
import sys

sys.path.append(os.path.dirname(__file__))

try:
    from face_detector import FaceDetector
    from arcface_model import FaceBackbone
except:
    # Nếu import thất bại, tạo class giả để không crash
    print("Warning: Cannot import FaceDetector/FaceBackbone")
    FaceDetector = None
    FaceBackbone = None


class FaceRecognizer:
    """
    Class xử lý nhận diện khuôn mặt
    """

    def __init__(self, model_path=None, device='cpu'):
        """
        Args:
            model_path: Đường dẫn đến file model arcface_resnet18.pth
            device: 'cpu' hoặc 'cuda'
        """
        self.device = device
        self.detector = None
        self.model = None

        # Khởi tạo face detector
        try:
            if FaceDetector is not None:
                self.detector = FaceDetector(ctx_id=-1)
                print("✅ Face detector loaded successfully")
        except Exception as e:
            print(f"⚠️ Cannot load face detector: {e}")

        # Khởi tạo ArcFace model
        if model_path and os.path.exists(model_path) and FaceBackbone is not None:
            try:
                self.model = FaceBackbone().to(self.device)
                state = torch.load(model_path, map_location=self.device)

                # Loại bỏ fc layer nếu có
                state = {k: v for k, v in state.items() if not k.startswith("model.fc")}

                self.model.load_state_dict(state, strict=False)
                self.model.eval()
                print(f"✅ ArcFace model loaded from {model_path}")
            except Exception as e:
                print(f"⚠️ Cannot load model: {e}")
                self.model = None
        else:
            print(f"⚠️ Model path not found or invalid: {model_path}")

        # Transform cho ảnh
        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize([0.5] * 3, [0.5] * 3)
        ])

    def process_image(self, image):
        """
        Xử lý ảnh và trích xuất embedding

        Args:
            image: PIL Image hoặc numpy array

        Returns:
            tuple: (embedding, face_image, bbox) hoặc (None, None, None) nếu không detect được face
        """
        try:
            # Convert PIL Image sang numpy array nếu cần
            if isinstance(image, Image.Image):
                image = np.array(image)

            # Convert sang RGB nếu cần
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)

            # Detect và align face
            if self.detector is None:
                print("⚠️ Face detector not available, using whole image")
                # Fallback: resize whole image
                face_image = cv2.resize(image, (112, 112))
                bbox = [0, 0, image.shape[1], image.shape[0]]
            else:
                # Lưu ảnh tạm để detector xử lý
                temp_path = "temp_face.jpg"
                cv2.imwrite(temp_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

                aligned = self.detector.detect_align(temp_path)

                # Xóa file tạm
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                if aligned is None:
                    print("⚠️ No face detected")
                    return None, None, None

                face_image = aligned
                # TODO: Lấy bbox từ detector nếu cần
                bbox = [0, 0, 112, 112]

            # Extract embedding
            if self.model is None:
                print("⚠️ Model not available, using random embedding")
                # Fallback: random embedding
                embedding = np.random.rand(512).astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)
            else:
                img_tensor = self.transform(face_image).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    embedding = self.model(img_tensor)

                embedding = embedding.cpu().numpy()[0]

            # Convert face_image sang PIL Image
            face_pil = Image.fromarray(face_image)

            return embedding, face_pil, bbox

        except Exception as e:
            print(f"❌ Error processing image: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None

    def process_image_with_bbox(self, image):
        """
        Xử lý ảnh và trích xuất embedding kèm bbox thực tế từ detector

        Args:
            image: PIL Image hoặc numpy array

        Returns:
            tuple: (embedding, face_image, box, bbox) hoặc (None, None, None, None) nếu không detect được face
            bbox format: [x1, y1, x2, y2] trong tọa độ ảnh gốc
        """
        try:
            # Convert PIL Image sang numpy array nếu cần
            if isinstance(image, Image.Image):
                image = np.array(image)

            # Convert sang RGB nếu cần
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2RGB)

            # Detect và align face
            if self.detector is None:
                print("⚠️ Face detector not available, using whole image")
                # Fallback: resize whole image
                face_image = cv2.resize(image, (112, 112))
                bbox = [0, 0, image.shape[1], image.shape[0]]
            else:
                # Lưu ảnh tạm để detector xử lý
                temp_path = "temp_face_detection.jpg"
                cv2.imwrite(temp_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

                # Detect với insightface để lấy bbox
                from insightface.app import FaceAnalysis
                app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
                app.prepare(ctx_id=-1, det_size=(640, 640))

                img_bgr = cv2.imread(temp_path)
                faces = app.get(img_bgr)

                # Xóa file tạm
                if os.path.exists(temp_path):
                    os.remove(temp_path)

                if len(faces) == 0:
                    print("⚠️ No face detected")
                    return None, None, None, None

                # Lấy face đầu tiên
                face = faces[0]

                # Lấy bbox từ detector (format: [x1, y1, x2, y2])
                bbox = face.bbox.astype(int).tolist()

                # Align face để extract embedding
                from insightface.utils import face_align
                aligned = face_align.norm_crop(img_bgr, face.kps)

                if aligned is None or aligned.size == 0:
                    print("⚠️ Face alignment failed")
                    return None, None, None, None

                face_image = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)

            # Extract embedding
            if self.model is None:
                print("⚠️ Model not available, using random embedding")
                # Fallback: random embedding
                embedding = np.random.rand(512).astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)
            else:
                img_tensor = self.transform(face_image).unsqueeze(0).to(self.device)

                with torch.no_grad():
                    embedding = self.model(img_tensor)

                embedding = embedding.cpu().numpy()[0]

            # Convert face_image sang PIL Image
            face_pil = Image.fromarray(face_image)

            return embedding, face_pil, [0, 0, 112, 112], bbox

        except Exception as e:
            print(f"❌ Error processing image with bbox: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None, None

    def compare_faces(self, embedding1, embedding2):
        """
        So sánh 2 embeddings

        Args:
            embedding1, embedding2: numpy arrays

        Returns:
            float: Cosine similarity (0-1)
        """
        similarity = cosine_similarity([embedding1], [embedding2])[0][0]
        return float(similarity)


class FaceDatabase:
    """
    Class quản lý database embeddings
    """

    def __init__(self, db_path="face_embeddings.pkl"):
        """
        Args:
            db_path: Đường dẫn đến file pickle lưu embeddings
        """
        self.db_path = db_path
        self.embeddings = {}  # {ma_nv: [embedding1, embedding2, ...]}
        self.load_database()

    def load_database(self):
        """Load embeddings từ file"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'rb') as f:
                    self.embeddings = pickle.load(f)
                print(f"✅ Loaded {len(self.embeddings)} employees from database")
            except Exception as e:
                print(f"⚠️ Cannot load database: {e}")
                self.embeddings = {}
        else:
            print("ℹ️ No existing database found, creating new one")
            self.embeddings = {}

    def reload_database(self):
        """Reload database từ file - dùng khi cần refresh dữ liệu"""
        print("🔄 Reloading database...")
        self.load_database()
        return len(self.embeddings)

    def save_database(self):
        """Lưu embeddings ra file"""
        try:
            with open(self.db_path, 'wb') as f:
                pickle.dump(self.embeddings, f)
            print(f"✅ Database saved successfully to {os.path.abspath(self.db_path)}")
        except Exception as e:
            print(f"❌ Cannot save database: {e}")

    def add_embedding(self, ma_nv, embedding):
        """
        Thêm embedding mới cho nhân viên

        Args:
            ma_nv: Mã nhân viên
            embedding: numpy array
        """
        if ma_nv not in self.embeddings:
            self.embeddings[ma_nv] = []

        self.embeddings[ma_nv].append(embedding)
        self.save_database()
        print(f"✅ Added embedding for {ma_nv}, total: {len(self.embeddings[ma_nv])}")

    def get_embeddings(self, ma_nv):
        """
        Lấy tất cả embeddings của 1 nhân viên

        Args:
            ma_nv: Mã nhân viên

        Returns:
            list: Danh sách embeddings
        """
        return self.embeddings.get(ma_nv, [])

    def remove_employee(self, ma_nv):
        """
        Xóa tất cả embeddings của 1 nhân viên

        Args:
            ma_nv: Mã nhân viên

        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy
        """
        if ma_nv in self.embeddings:
            del self.embeddings[ma_nv]
            self.save_database()
            print(f"✅ Removed embeddings for {ma_nv}")
            return True
        else:
            print(f"⚠️ No embeddings found for {ma_nv}")
            return False

    def search_face(self, query_embedding, threshold=0.6):
        """
        Tìm kiếm khuôn mặt trong database

        Args:
            query_embedding: Embedding cần tìm
            threshold: Ngưỡng similarity (mặc định 0.6)

        Returns:
            tuple: (ma_nv, similarity) hoặc (None, max_similarity)
        """
        best_match = None
        max_similarity = 0.0

        for ma_nv, embeddings in self.embeddings.items():
            for emb in embeddings:
                similarity = cosine_similarity([query_embedding], [emb])[0][0]

                if similarity > max_similarity:
                    max_similarity = similarity

                    if similarity >= threshold:
                        best_match = ma_nv

        if best_match:
            print(f"✅ Found match: {best_match} with similarity {max_similarity:.4f}")
        else:
            print(f"❌ No match found (best similarity: {max_similarity:.4f}, threshold: {threshold})")

        return best_match, max_similarity

    def get_all_employees(self):
        """
        Lấy danh sách tất cả mã nhân viên đã đăng ký

        Returns:
            list: Danh sách mã nhân viên
        """
        return list(self.embeddings.keys())

    def get_statistics(self):
        """
        Thống kê database

        Returns:
            dict: {
                'total_employees': int,
                'total_embeddings': int,
                'avg_embeddings_per_employee': float
            }
        """
        total_employees = len(self.embeddings)
        total_embeddings = sum(len(embs) for embs in self.embeddings.values())
        avg_embeddings = total_embeddings / total_employees if total_employees > 0 else 0

        return {
            'total_employees': total_employees,
            'total_embeddings': total_embeddings,
            'avg_embeddings_per_employee': round(avg_embeddings, 2)
        }


# Khởi tạo global instances
# Thay đổi đường dẫn model theo vị trí thực tế của bạn
MODEL_PATH = "arcface_resnet18.pth"  # Đặt file model trong cùng thư mục với app
DB_PATH = "face_embeddings.pkl"

face_recognizer = FaceRecognizer(model_path=MODEL_PATH, device='cpu')
face_db = FaceDatabase(db_path=DB_PATH)

print("\n" + "=" * 50)
print("FACE RECOGNITION SYSTEM INITIALIZED")
print("=" * 50)
stats = face_db.get_statistics()
print(f"📊 Total employees: {stats['total_employees']}")
print(f"📊 Total embeddings: {stats['total_embeddings']}")
print(f"📊 Avg embeddings/employee: {stats['avg_embeddings_per_employee']}")
print("=" * 50 + "\n")