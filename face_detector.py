import cv2
from insightface.app import FaceAnalysis
from insightface.utils import face_align

class FaceDetector:
    def __init__(self, ctx_id=-1):
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CPUExecutionProvider"]
        )
        self.app.prepare(ctx_id=ctx_id, det_size=(640, 640))

    def detect_align(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return None

        faces = self.app.get(img)
        if len(faces) == 0:
            return None

        face = faces[0]

        aligned = face_align.norm_crop(img, face.kps)

        if aligned is None or aligned.size == 0:
            return None

        aligned = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB)
        return aligned
