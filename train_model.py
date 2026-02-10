import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import transforms
from torchvision.datasets import ImageFolder
from torchvision.models import resnet18
from tqdm import tqdm
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")


def main():
    # =========================
    # 1. CẤU HÌNH
    # =========================
    DATA_DIR = r"E:/Workspace/ThucTap/train/casia-webface"
    BATCH_SIZE = 32
    EPOCHS = 20                 # bạn có thể đổi thành 15 hoặc 20
    LR = 3e-4                  # LR ban đầu phù hợp với Cosine
    IMG_SIZE = 112
    EMBEDDING_SIZE = 512
    NUM_WORKERS = 2

    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Using device:", DEVICE)

    # =========================
    # 2. TIỀN XỬ LÝ DỮ LIỆU
    # =========================
    train_transform = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5, 0.5, 0.5],
                             std=[0.5, 0.5, 0.5])
    ])

    train_dataset = ImageFolder(root=DATA_DIR, transform=train_transform)

    # =========================
    # 3. SỐ LỚP
    # =========================
    num_classes = len(train_dataset.classes)
    print("Số lớp (số người):", num_classes)
    print("Số ảnh train:", len(train_dataset))

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=NUM_WORKERS,
        drop_last=True,
        pin_memory=True if DEVICE.type == "cuda" else False
    )

    # =========================
    # 4. BACKBONE: RESNET18
    # =========================
    class FaceBackbone(nn.Module):
        def __init__(self, embedding_size=512):
            super(FaceBackbone, self).__init__()
            self.model = resnet18(pretrained=True)
            self.model.fc = nn.Linear(self.model.fc.in_features, embedding_size)

        def forward(self, x):
            x = self.model(x)
            x = nn.functional.normalize(x)
            return x

    # =========================
    # 5. ARCFACE LOSS (MARGIN TỐI ƯU)
    # =========================
    class ArcFaceLoss(nn.Module):
        def __init__(self, in_features, out_features, s=64.0, m=0.50):
            super(ArcFaceLoss, self).__init__()
            self.s = s
            self.m = m
            self.weight = nn.Parameter(torch.FloatTensor(out_features, in_features))
            nn.init.xavier_uniform_(self.weight)

        def forward(self, embeddings, labels):
            cosine = nn.functional.linear(
                nn.functional.normalize(embeddings),
                nn.functional.normalize(self.weight)
            )

            theta = torch.acos(torch.clamp(cosine, -1.0 + 1e-7, 1.0 - 1e-7))
            target_logits = torch.cos(theta + self.m)

            one_hot = torch.zeros_like(cosine)
            one_hot.scatter_(1, labels.view(-1, 1), 1)

            output = one_hot * target_logits + (1.0 - one_hot) * cosine
            output *= self.s

            loss = nn.CrossEntropyLoss()(output, labels)
            return loss

    # =========================
    # 6. KHỞI TẠO MODEL
    # =========================
    model = FaceBackbone(embedding_size=EMBEDDING_SIZE).to(DEVICE)
    criterion = ArcFaceLoss(EMBEDDING_SIZE, num_classes).to(DEVICE)

    optimizer = optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)

    # =========================
    # 7. COSINE LEARNING RATE
    # =========================
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=EPOCHS,       # số epoch cho 1 chu kỳ cosine
        eta_min=1e-5        # LR nhỏ nhất
    )

    # =========================
    # 8. TRAIN LOOP
    # =========================
    train_losses = []
    train_accuracies = []

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        pbar = tqdm(train_loader, desc=f"Epoch [{epoch+1}/{EPOCHS}]", ncols=100)

        for imgs, labels in pbar:
            imgs = imgs.to(DEVICE)
            labels = labels.to(DEVICE)

            optimizer.zero_grad()
            embeddings = model(imgs)
            loss = criterion(embeddings, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()

            with torch.no_grad():
                logits = torch.matmul(
                    nn.functional.normalize(embeddings),
                    nn.functional.normalize(criterion.weight).t()
                )
                preds = torch.argmax(logits, dim=1)
                correct += (preds == labels).sum().item()
                total += labels.size(0)

            avg_loss = running_loss / (total / BATCH_SIZE)
            acc = correct / total

            pbar.set_postfix({
                "loss": f"{avg_loss:.4f}",
                "acc": f"{acc:.4f}",
                "lr": f"{optimizer.param_groups[0]['lr']:.6f}"
            })

        scheduler.step()

        epoch_loss = running_loss / len(train_loader)
        epoch_acc = correct / total

        train_losses.append(epoch_loss)
        train_accuracies.append(epoch_acc)

        pbar.set_description(f"Epoch {epoch+1}/{EPOCHS} | Loss: {epoch_loss:.4f} | Acc: {epoch_acc:.4f}")
        pbar.close()

    # =========================
    # 9. LƯU MODEL
    # =========================
    torch.save(model.state_dict(), "arcface_resnet18.pth")
    print("Đã lưu model: arcface_resnet18.pth")

    # =========================
    # 10. VẼ ĐỒ THỊ
    # =========================
    plt.figure()
    plt.plot(range(1, EPOCHS + 1), train_losses, marker='o')
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training Loss")
    plt.grid(True)
    plt.show()

    plt.figure()
    plt.plot(range(1, EPOCHS + 1), train_accuracies, marker='o')
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.title("Training Accuracy")
    plt.grid(True)
    plt.show()


# =========================
# WINDOWS MULTIPROCESS FIX
# =========================
if __name__ == "__main__":
    main()
