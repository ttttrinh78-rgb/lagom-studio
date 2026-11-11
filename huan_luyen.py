# buoc4_huan_luyen.py — Huấn luyện mô hình, so với 2 baseline, lưu mô hình cho app
from pathlib import Path
import numpy as np, pandas as pd, torch
from sklearn.metrics import roc_auc_score
from mo_hinh import PairScorer, diem

BASE = Path(__file__).parent; KQ, MD = BASE / "ket_qua", BASE / "models"; MD.mkdir(exist_ok=True)
sp = pd.read_csv(KQ / "san_pham.csv", dtype={"article_id": str})
img, txt = np.load(KQ / "img.npy"), np.load(KQ / "txt.npy")
idx = {a: i for i, a in enumerate(sp["article_id"])}
nhom_arr = sp["nhom_phoi"].values

def doc(tap):
    c = pd.read_csv(KQ / f"cap_{tap}.csv", dtype={"mon_a": str, "mon_b": str})
    return (torch.as_tensor([idx[x] for x in c["mon_a"]]), torch.as_tensor([idx[x] for x in c["mon_b"]]),
            torch.as_tensor(c["nhan"].values, dtype=torch.float32))
TR, VA, TE = doc("train"), doc("valid"), doc("test")

@torch.no_grad()
def cham_auc(m, X, cap):
    m.eval(); a, b, y = cap
    s = np.concatenate([torch.sigmoid(m(X[a[i:i+8192]], X[b[i:i+8192]])).numpy() for i in range(0, len(y), 8192)])
    return roc_auc_score(y.numpy(), s)

def huan_luyen(X, ten, h=512, epochs=6):
    X = torch.as_tensor(X); m = PairScorer(X.shape[1], h)
    opt, lossf = torch.optim.Adam(m.parameters(), 1e-3), torch.nn.BCEWithLogitsLoss()
    a, b, y = TR; best, state = 0, None
    for ep in range(epochs):
        m.train(); perm = torch.randperm(len(y))
        for i in range(0, len(y), 1024):
            j = perm[i:i + 1024]
            loss = lossf(m(X[a[j]], X[b[j]]), y[j]); opt.zero_grad(); loss.backward(); opt.step()
        auc = cham_auc(m, X, VA); print(f"{ten} – epoch {ep + 1}: AUC valid = {auc:.4f}")
        if auc > best: best, state = auc, {k: v.clone() for k, v in m.state_dict().items()}
    m.load_state_dict(state); m.eval()
    torch.save({"state": state, "d": X.shape[1], "h": h}, MD / f"{ten}.pt")
    return m, X

def recall10(score_fn, n=500):
    a, b, y = TE; pos = np.where(y.numpy() == 1)[0]
    pos = np.random.default_rng(0).choice(pos, min(n, len(pos)), replace=False); trung = 0
    for k in pos:
        ai, bi = int(a[k]), int(b[k]); cand = np.where(nhom_arr == nhom_arr[bi])[0]
        s = score_fn(ai, cand); trung += bi in cand[np.argsort(-s)[:10]]
    return trung / len(pos)

# Baseline 1: món bán chạy nhất
df = pd.read_csv(KQ / "du_lieu_sach.csv", dtype={"article_id": str}, usecols=["t_dat", "article_id"])
pop = np.zeros(len(sp)); vc = df[df["t_dat"] < "2020-09-08"]["article_id"].value_counts()
for k, v in vc.items(): pop[idx[k]] = v
a, b, y = TE
kq = [("Ngẫu nhiên", 0.5, recall10(lambda ai, c: np.random.rand(len(c))))]
kq.append(("Bán chạy nhất", roc_auc_score(y, pop[a] + pop[b]), recall10(lambda ai, c: pop[c])))
# Baseline 2: CLIP nguyên bản
cos = lambda ai, c: (img[c] @ img[ai] + txt[c] @ txt[ai]) / 2
kq.append(("CLIP nguyên bản", roc_auc_score(y, ((img[a] * img[b]).sum(1) + (txt[a] * txt[b]).sum(1)) / 2), recall10(cos)))
# Mô hình của nhóm + mô hình chỉ ảnh (cho tab tải ảnh)
m, X = huan_luyen(np.concatenate([img, txt], 1), "final")
kq.append(("Mô hình nhóm (ảnh + chữ)", cham_auc(m, X, TE), recall10(lambda ai, c: diem(m, X[ai], X[c]))))
mi, Xi = huan_luyen(img, "model_chi_anh")
kq.append(("Mô hình nhóm (chỉ ảnh)", cham_auc(mi, Xi, TE), recall10(lambda ai, c: diem(mi, Xi[ai], Xi[c]))))

bang = pd.DataFrame(kq, columns=["Phương pháp", "AUC (test)", "Recall@10 (test)"])
bang.to_csv(KQ / "bang_ket_qua.csv", index=False, encoding="utf-8-sig"); print(bang.round(4).to_string(index=False))