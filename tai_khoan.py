# tai_khoan.py — Tài khoản và tủ đồ, lưu ngay trên máy (bản demo, không dùng cho hệ thống thật)
import hashlib, hmac, io, json, os, re, uuid
from pathlib import Path
import numpy as np
from PIL import Image

GOC = Path(__file__).parent / "nguoi_dung"
F_TK = GOC / "tai_khoan.json"

def _doc(f, mac_dinh): return json.loads(f.read_text("utf-8")) if f.exists() else mac_dinh
def _bam(mk, muoi): return hashlib.pbkdf2_hmac("sha256", mk.encode(), muoi, 200_000).hex()

def dang_ky(ten, mk, mk2):
    ten = ten.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,20}", ten): return "Tên đăng nhập 3–20 ký tự: chữ thường không dấu, số, dấu gạch dưới."
    if len(mk) < 6: return "Mật khẩu tối thiểu 6 ký tự."
    if mk != mk2: return "Hai mật khẩu không khớp."
    ds = _doc(F_TK, {})
    if ten in ds: return "Tên đăng nhập đã có người dùng."
    muoi = os.urandom(16); ds[ten] = {"muoi": muoi.hex(), "bam": _bam(mk, muoi)}
    GOC.mkdir(exist_ok=True); F_TK.write_text(json.dumps(ds), "utf-8")
    return None

def dang_nhap(ten, mk):
    u = _doc(F_TK, {}).get(ten.strip().lower())
    return bool(u) and hmac.compare_digest(
        _bam(mk, bytes.fromhex(u["muoi"])),
        u["bam"]
    )


def tai_khoan_ton_tai(ten):
    return ten in _doc(F_TK, {})

def _tu(user):
    d = GOC / user / "tu_do"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _tu(user):
    d = GOC / user / "tu_do"; d.mkdir(parents=True, exist_ok=True); return d

def doc_tu_do(user):
    d = _tu(user)
    ds = _doc(d / "tu_do.json", [])
    for m in ds:
        if m.get("nhom") == "Áo khoác":
            m["nhom"] = "Áo"                       # gộp áo khoác cũ vào nhóm Áo
    return [dict(m, bytes=(d / f"{m['id']}.jpg").read_bytes(), v=np.load(d / f"{m['id']}.npy")) for m in ds]

def luu_mon(user, b, nhom, ten, v, kieu_dang=None):
    d = _tu(user)
    mid = uuid.uuid4().hex[:10]
    Image.open(io.BytesIO(b)).convert("RGB").save(d / f"{mid}.jpg", "JPEG", quality=90)
    np.save(d / f"{mid}.npy", v)
    ds = _doc(d / "tu_do.json", [])
    ds.append({"id": mid, "nhom": nhom, "ten": ten, "kieu_dang": kieu_dang})
    (d / "tu_do.json").write_text(json.dumps(ds, ensure_ascii=False), "utf-8")

def xoa_mon(user, mid):
    d = _tu(user); ds = [m for m in _doc(d / "tu_do.json", []) if m["id"] != mid]
    (d / "tu_do.json").write_text(json.dumps(ds, ensure_ascii=False), "utf-8")
    for duoi in (".jpg", ".npy"): (d / f"{mid}{duoi}").unlink(missing_ok=True)

# ================= BỘ ĐỒ ĐÃ LƯU (riêng từng người dùng)
import json as _json, uuid as _uuid, shutil as _shutil
from pathlib import Path as _Path
import numpy as _np


def _thu_muc_bo(user):
    d = _Path(__file__).parent / "nguoi_dung" / user / "bo_da_luu"
    d.mkdir(parents=True, exist_ok=True)
    return d


def luu_bo(user, mon):
    """Lưu một bộ đồ (danh sách món có bytes, v, nhom, ten, nguon)."""
    d = _thu_muc_bo(user)
    bid = _uuid.uuid4().hex[:10]
    (d / bid).mkdir()
    for k, m in enumerate(mon):
        (d / bid / f"{k}.bin").write_bytes(m["bytes"])
    _np.save(d / bid / "v.npy", _np.stack([m["v"] for m in mon]))
    f = d / "ds.json"
    ds = _json.loads(f.read_text("utf-8")) if f.exists() else []
    ds.append({"id": bid, "mon": [{"nhom": m["nhom"], "ten": m["ten"], "nguon": m.get("nguon", "tu")} for m in mon]})
    f.write_text(_json.dumps(ds, ensure_ascii=False), "utf-8")
    return bid


def doc_bo(user):
    """Các bộ đồ đã lưu: [{id, mon: [...], V: mảng vector}]."""
    d = _thu_muc_bo(user)
    f = d / "ds.json"
    if not f.exists():
        return []
    kq = []
    for b in _json.loads(f.read_text("utf-8")):
        thu = d / b["id"]
        if not thu.exists():
            continue
        V = _np.load(thu / "v.npy")
        mon = [dict(m, bytes=(thu / f"{k}.bin").read_bytes(), v=V[k]) for k, m in enumerate(b["mon"])]
        kq.append(dict(id=b["id"], mon=mon, V=V))
    return kq


def xoa_bo(user, bid):
    d = _thu_muc_bo(user)
    f = d / "ds.json"
    if f.exists():
        ds = [b for b in _json.loads(f.read_text("utf-8")) if b["id"] != bid]
        f.write_text(_json.dumps(ds, ensure_ascii=False), "utf-8")
    _shutil.rmtree(d / bid, ignore_errors=True)



def sua_mon(user, mid, **thay):
    """Sửa thông tin một món trong tủ đồ (ten, nhom, kieu_dang…)."""
    d = _tu(user)
    ds = _doc(d / "tu_do.json", [])
    for m in ds:
        if m["id"] == mid:
            m.update(thay)
    (d / "tu_do.json").write_text(json.dumps(ds, ensure_ascii=False), "utf-8")