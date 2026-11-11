# buoc2_clip.py — Biến ảnh và mô tả mỗi sản phẩm thành vector bằng CLIP
from pathlib import Path
import numpy as np, pandas as pd, torch, open_clip
from PIL import Image

BASE = Path(__file__).parent
D, KQ = BASE, BASE / "ket_qua"
sp = pd.read_csv(KQ / "san_pham.csv", dtype={"article_id": str})
van_ban = (sp["prod_name"] + ", " + sp["product_type_name"] + ", " + sp["colour_group_name"] + ", "
           + sp["graphical_appearance_name"] + ". " + sp["detail_desc"].str[:250]).tolist()

model, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
tok = open_clip.get_tokenizer("ViT-B-32"); model.eval()
anh_v, chu_v = [], []
for i in range(0, len(sp), 64):
    ims = torch.stack([pre(Image.open(D / p).convert("RGB")) for p in sp["duong_dan_anh"][i:i + 64]])
    with torch.no_grad():
        vi = model.encode_image(ims); vt = model.encode_text(tok(van_ban[i:i + 64]))
    anh_v.append(torch.nn.functional.normalize(vi, dim=-1).numpy())
    chu_v.append(torch.nn.functional.normalize(vt, dim=-1).numpy())
    print(f"{min(i + 64, len(sp))}/{len(sp)} sản phẩm", end="\r")
np.save(KQ / "img.npy", np.concatenate(anh_v)); np.save(KQ / "txt.npy", np.concatenate(chu_v))
print("\nXong:", len(sp), "sản phẩm")