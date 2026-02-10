import numpy as np
from numpy.linalg import norm

def get_embedding(face_img):
    # TODO: thay bằng ArcFace thật
    return np.random.rand(512).astype(np.float32)

def cosine_similarity(a, b):
    return np.dot(a, b) / (norm(a) * norm(b))