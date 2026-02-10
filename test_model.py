import os
import csv
import torch
import numpy as np
from torchvision import transforms
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
from tqdm import tqdm

from face_detector import FaceDetector
from arcface_model import FaceBackbone
import warnings
warnings.filterwarnings("ignore")


# =========================
# CONFIG
# =========================
LFW_ROOT = r"E:/Workspace/ThucTap/test/lfw-deepfunneled/lfw-deepfunneled"
MATCH_CSV = r"E:/Workspace/ThucTap/test/matchpairsDevTest.csv"
MISMATCH_CSV = r"E:/Workspace/ThucTap/test/mismatchpairsDevTest.csv"
MODEL_PATH = r"E:/Workspace/ThucTap/arcface_resnet18.pth"
DEVICE = "cpu"

# =========================
# INIT
# =========================
detector = FaceDetector(ctx_id=-1)

model = FaceBackbone().to(DEVICE)
state = torch.load(MODEL_PATH, map_location=DEVICE)
state = {k: v for k, v in state.items() if not k.startswith("model.fc")}
model.load_state_dict(state, strict=False)
model.eval()

transform = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])

# =========================
def get_lfw_image(root, name, idx):
    return os.path.join(root, name, f"{name}_{idx:04d}.jpg")

def extract_embedding(path):
    aligned = detector.detect_align(path)
    if aligned is None:
        return None

    img = transform(aligned).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        emb = model(img)

    return emb.cpu().numpy()[0]

# =========================
def load_pairs():
    pairs = []

    with open(MATCH_CSV, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            pairs.append((r["name"], int(r["imagenum1"]),
                          r["name"], int(r["imagenum2"]), 1))

    with open(MISMATCH_CSV, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            pairs.append((r[0], int(r[1]), r[2], int(r[3]), 0))

    return pairs

# =========================
def evaluate():
    pairs = load_pairs()
    sims, labels = [], []
    skip = 0

    for n1,i1,n2,i2,l in tqdm(pairs):
        e1 = extract_embedding(get_lfw_image(LFW_ROOT,n1,i1))
        e2 = extract_embedding(get_lfw_image(LFW_ROOT,n2,i2))

        if e1 is None or e2 is None:
            skip += 1
            continue

        sims.append(cosine_similarity([e1],[e2])[0][0])
        labels.append(l)

    ths = np.arange(0.2,0.8,0.01)
    accs = []

    for th in ths:
        acc = np.mean([(s>=th)==l for s,l in zip(sims,labels)])
        accs.append(acc)

    best = np.argmax(accs)

    print(f"\nBEST ACC = {accs[best]:.4f} @ TH = {ths[best]:.2f}")
    print(f"SKIPPED PAIRS: {skip}")

    plt.plot(ths, accs)
    plt.axvline(ths[best],color='r',ls='--')
    plt.grid()
    plt.show()

if __name__ == "__main__":
    evaluate()
