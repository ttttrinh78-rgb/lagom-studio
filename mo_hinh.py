# mo_hinh.py — Mô hình chấm điểm 2 món đồ hợp nhau đến đâu (dùng chung cho huấn luyện và app)
import torch, torch.nn as nn

class PairScorer(nn.Module):
    def __init__(self, d, h=512):
        super().__init__()
        self.f = nn.Sequential(nn.Linear(3 * d, h), nn.ReLU(), nn.Dropout(0.2), nn.Linear(h, 1))
    def forward(self, a, b):
        return self.f(torch.cat([a + b, a * b, (a - b).abs()], -1)).squeeze(-1)

def tai_mo_hinh(path):
    ck = torch.load(path, map_location="cpu")
    m = PairScorer(ck["d"], ck["h"]); m.load_state_dict(ck["state"]); m.eval()
    return m

@torch.no_grad()
def diem(m, a, B):
    """a: vector 1 món (d,), B: nhiều món (n, d) → điểm hợp nhau 0–1 của a với từng món trong B."""
    return torch.sigmoid(m(a.expand_as(B), B)).numpy()