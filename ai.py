# ai.py — Phần AI của MixMe: CLIP, nhận diện, chấm điểm, phối đồ theo quy tắc stylist, ghép ảnh, thử đồ
import io, itertools, colorsys, json, hashlib
from pathlib import Path
import numpy as np, pandas as pd, torch, streamlit as st
from PIL import Image
from mo_hinh import tai_mo_hinh, diem
import cai_dat as C

BASE = Path(__file__).parent
KQ, MD = BASE / "ket_qua", BASE / "models"
F = torch.nn.functional
KHONG_TINH_GIOI_HAN = ("Túi xách", "Phụ kiện")
PHU_KIEN_NHOM = ("Giày", "Túi xách", "Phụ kiện")
QUAN_AO = ("Áo", "Quần/Chân váy", "Đồ liền thân")
KHO_CHUNG = BASE / "kho_chung"
TRUNG_TINH = {"den", "trang", "xam", "be_nau"}


# ================= KHO CHUNG (món người dùng chia sẻ)
def _doc_kho_chung():
    f = KHO_CHUNG / "ds.json"
    if not f.exists():
        return []
    kq = []
    for d in json.loads(f.read_text("utf-8")):
        if (KHO_CHUNG / f"{d['id']}.npy").exists() and (KHO_CHUNG / f"{d['id']}.jpg").exists():
            kq.append(dict(d, v=np.load(KHO_CHUNG / f"{d['id']}.npy")))
    return kq


def chia_se_mon(b, v, nhom, ten, kieu_dang=None):
    """Đưa một món của người dùng lên cửa hàng chung (không lưu tên tài khoản). Ảnh trùng chỉ lưu một lần."""
    KHO_CHUNG.mkdir(exist_ok=True)
    mid = hashlib.md5(b).hexdigest()[:12]
    f = KHO_CHUNG / "ds.json"
    ds = json.loads(f.read_text("utf-8")) if f.exists() else []
    if any(d["id"] == mid for d in ds):
        return
    Image.open(io.BytesIO(b)).convert("RGB").save(KHO_CHUNG / f"{mid}.jpg", "JPEG", quality=90)
    np.save(KHO_CHUNG / f"{mid}.npy", np.asarray(v, dtype=np.float32))
    ds.append({"id": mid, "nhom": nhom, "ten": ten, "kieu_dang": kieu_dang})
    f.write_text(json.dumps(ds, ensure_ascii=False), "utf-8")


def _vector_thu_muc(thu_muc, clip, pre):
    """Ảnh và vector CLIP của mọi ảnh trong thư mục (kể cả thư mục con)."""
    ds = [p for p in sorted(Path(thu_muc).rglob("*")) if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    if not ds:
        return [], None
    with torch.no_grad():
        anh = torch.stack([pre(Image.open(p).convert("RGB")) for p in ds])
        return ds, F.normalize(clip.encode_image(anh), dim=-1)


# ================= NẠP MÔ HÌNH VÀ KHO CỬA HÀNG
@st.cache_resource(show_spinner="Đang nạp mô hình AI…")
def _tai():
    import open_clip
    clip, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
    tok = open_clip.get_tokenizer("ViT-B-32")
    clip.eval()

    def chu(cau):
        with torch.no_grad():
            return F.normalize(clip.encode_text(tok(cau)), dim=-1)

    vd = chu(list(C.DIP.values()))
    vp = chu(list(getattr(C, "PHONG_CACH", {"-": "an outfit"}).values()))
    vn = chu([C.NHOM[n]["mo_ta"] for n in C.NHOM])
    vk = chu(["a photo of a jacket, coat, blazer or cardigan"])[0]
    vt = chu(["a photo of a t-shirt, blouse, shirt or tank top"])[0]
    vs = chu(["a photo of a skirt", "a photo of trousers, jeans or shorts"])
    vb = chu(["a photo of a handbag, purse, clutch or shoulder bag",
              "a photo of jewelry, a belt, a hat, a scarf, hair accessories or sunglasses"])
    vde = chu(["a photo of platform shoes with thick chunky soles or wedge heels",
               "a photo of shoes with thin flat soles or slim heels"])
    vr = chu(["a photo of a plain solid-color item with no pattern",
              "a photo of an item with a busy print, pattern, graphics or many details"])
    vo = chu(["a photo of a tight fitted bodycon skirt, dress or shorts",
              "a photo of a loose flowy wide skirt, dress or shorts"])
    vf = chu(["a photo of an oversized loose fitting top", "a photo of a slim fitted top"])
    vtx = chu([f"a photo of a clothing item made of {p}"
               for p in getattr(C, "CHAT_LIEU_HOA_TIET", {"tron": "plain fabric"}).values()])
    vkd = {nh: (list(ds), chu([f"a photo of {p}" for _, p in ds.values()]))
           for nh, ds in getattr(C, "KIEU_DANG", {}).items()}

    img = torch.as_tensor(np.load(KQ / "img.npy"))
    sp = pd.read_csv(KQ / "san_pham.csv", dtype={"article_id": str})

    # Sản phẩm xu hướng (thư mục xu_huong\, thư mục con đặt tên theo loại)
    ds_xh, vx = _vector_thu_muc(BASE / "xu_huong", clip, pre)
    _, vl = _vector_thu_muc(BASE / "loi_thoi", clip, pre)
    so_goc = len(sp)
    if vx is not None and getattr(C, "THEM_XU_HUONG_VAO_KHO", True):
        tm = getattr(C, "THU_MUC_NHOM", {})
        nhom_xh = [tm.get(p.parent.name, list(C.NHOM)[int((vn @ v).argmax())]) for p, v in zip(ds_xh, vx)]
        viet_tat = {"Áo": "AO", "Quần/Chân váy": "QV", "Đồ liền thân": "VL",
                    "Giày": "GI", "Túi xách": "TX", "Phụ kiện": "PK"}
        # Mã dựa trên đường dẫn tương đối của ảnh: thêm/xóa ảnh khác không làm đổi mã cũ.
        ma_xh = []
        for p, nhom in zip(ds_xh, nhom_xh):
            duong_dan = p.relative_to(BASE).as_posix().lower()
            ma_hash = hashlib.sha256(duong_dan.encode("utf-8")).hexdigest()[:8].upper()
            ma_xh.append(f"XH-{viet_tat.get(nhom, 'PK')}-{ma_hash}")
        them = pd.DataFrame({"article_id": ma_xh,
                             "prod_name": [p.stem.replace("_", " ") for p in ds_xh],
                             "product_type_name": "", "nhom_phoi": nhom_xh, "colour_group_name": "Xu hướng",
                             "graphical_appearance_name": "", "detail_desc": "",
                             "duong_dan_anh": [p.relative_to(BASE).as_posix() for p in ds_xh]})
        sp = pd.concat([sp, them], ignore_index=True)
        img = torch.cat([img, vx])
    # Món người dùng chia sẻ
    so_truoc_nd = len(sp)
    ds_nd = _doc_kho_chung()
    if ds_nd:
        them_nd = pd.DataFrame({"article_id": [f"nd_{d['id']}" for d in ds_nd],
                                "prod_name": [d["ten"] for d in ds_nd],
                                "product_type_name": "", "nhom_phoi": [d["nhom"] for d in ds_nd],
                                "colour_group_name": "Người dùng chia sẻ",
                                "graphical_appearance_name": "", "detail_desc": "",
                                "duong_dan_anh": [f"kho_chung/{d['id']}.jpg" for d in ds_nd]})
        sp = pd.concat([sp, them_nd], ignore_index=True)
        img = torch.cat([img, torch.as_tensor(np.stack([d["v"] for d in ds_nd])).float()])
    vi_tri = np.arange(len(sp))
    la_xh = (vi_tri >= so_goc) & (vi_tri < so_truoc_nd)
    la_nd = vi_tri >= so_truoc_nd

    s = (img @ vd.T).numpy()
    s2 = (img @ vp.T).numpy()

    # Tách túi xách khỏi phụ kiện
    ten_loai_sp = sp["product_type_name"].fillna("")
    la_tui = (sp["nhom_phoi"] == "Phụ kiện") & ten_loai_sp.str.contains("bag|backpack", case=False)
    sp.loc[la_tui, "nhom_phoi"] = "Túi xách"
    giong_tui = ((img @ vb[0]) > (img @ vb[1])).numpy()
    trang_suc = ten_loai_sp.str.contains(
        "necklace|earring|bracelet|ring|hair|sunglasses|hat|cap|belt|scarf|watch|jewel", case=False).values
    sp.loc[(sp["nhom_phoi"] == "Phụ kiện").values & giong_tui & ~trang_suc & ~la_xh & ~la_nd, "nhom_phoi"] = "Túi xách"

    # AI tự sửa áo / quần-chân váy / váy liền bị xếp sai loại (chỉ sản phẩm H&M)
    if getattr(C, "TU_SUA_PHAN_LOAI", True):
        nhom_ds = list(C.NHOM)
        dn = (img @ vn.T).numpy()
        hien = np.array([nhom_ds.index(x) if x in nhom_ds else 0 for x in sp["nhom_phoi"]])
        top = dn.argmax(1)
        chenh = dn[vi_tri, top] - dn[vi_tri, hien]
        la_qa = sp["nhom_phoi"].isin(QUAN_AO).values & np.array([nhom_ds[t] in QUAN_AO for t in top])
        sua = la_qa & (chenh > getattr(C, "NGUONG_SUA_LOAI", 0.03)) & ~la_xh & ~la_nd
        sp.loc[sua, "nhom_phoi"] = [nhom_ds[t] for t in top[sua]]

    # Chỉnh tay trên web (ket_qua\\sua_kho.csv)
    kd_sua = {}
    f_sua = KQ / "sua_kho.csv"
    if f_sua.exists():
        for _, r in pd.read_csv(f_sua, dtype=str).fillna("").iterrows():
            sp.loc[sp["article_id"] == r["article_id"], "nhom_phoi"] = r["nhom"]
            if r["kieu_dang"]:
                kd_sua[r["article_id"]] = r["kieu_dang"]

    # Bộ lọc kho
    ban = pd.read_csv(KQ / "du_lieu_sach.csv", dtype={"article_id": str}, usecols=["t_dat", "article_id", "section_name"])
    ban_gan = sp["article_id"].map(ban[ban["t_dat"] >= "2020-09-01"]["article_id"].value_counts()).fillna(0).values
    bst = sp["article_id"].map(ban.drop_duplicates("article_id").set_index("article_id")["section_name"]).fillna("")
    hop_thoi = (ban_gan >= C.BAN_TOI_THIEU) & ~bst.str.contains("|".join(C.LOAI_BO_BST), case=False).values
    ten_day_du = (" " + sp["prod_name"].fillna("") + " " + ten_loai_sp).str.lower()
    tu_khoa_bo = getattr(C, "LOAI_BO_TU_KHOA", [])
    if tu_khoa_bo:
        hop_thoi &= ~ten_day_du.str.contains("|".join(tu_khoa_bo), na=False).values
    if getattr(C, "LOAI_GIAY_DE_DAY", True):
        la_giay = (sp["nhom_phoi"] == "Giày").values
        la_bot_kho = ten_day_du.str.contains("boot", na=False).values
        de_day = ((img @ vde[0]) > (img @ vde[1])).numpy()
        hop_thoi &= ~(la_giay & de_day & ~la_bot_kho)
    hop_thoi |= la_xh | la_nd
    hop_thoi &= np.array([(BASE / str(p)).exists() for p in sp["duong_dan_anh"]])
    if vl is not None:
        gan_lt = (img @ vl.T).numpy().max(1)
        hop_thoi &= (gan_lt <= getattr(C, "NGUONG_LOI_THOI", 0.82)) | la_xh

    dieu_chinh = np.zeros(len(sp))
    for tu, w in getattr(C, "DIEU_CHINH_LOAI", {}).items():
        dieu_chinh += w * ten_day_du.str.contains(tu, regex=False, na=False).values

    def gan_nhat(T):
        if T is None:
            return np.zeros(len(img))
        s_ = (img @ T.T).numpy()
        return np.sort(s_, axis=1)[:, -min(5, s_.shape[1]):].mean(1)

    tho = gan_nhat(vx) - gan_nhat(vl)
    xu_huong = (tho - tho.mean()) / (tho.std() + 1e-8)
    xu_huong[la_xh] = xu_huong.max() + 0.5
    ty_le_bo = getattr(C, "LOAI_BO_LOI_THOI", 0.3)
    if (vx is not None or vl is not None) and ty_le_bo > 0 and (~la_xh).any():
        hop_thoi &= (xu_huong > np.quantile(xu_huong[~la_xh], ty_le_bo)) | la_xh | la_nd

    mo = tai_mo_hinh(MD / "model_chi_anh.pt")
    rng = np.random.default_rng(0)
    mau_nn = img[torch.as_tensor(rng.choice(len(img), size=min(300, len(img)), replace=False))]
    de_hop = np.stack([diem(mo, v, img) for v in mau_nn]).mean(0)

    return dict(clip=clip, pre=pre, vd=vd, vn=vn, vk=vk, vs=vs, vt=vt, vb=vb, vr=vr, vo=vo, vf=vf, vtx=vtx, vkd=vkd,
                tb=s.mean(0), dl=s.std(0), zk=(s - s.mean(0)) / s.std(0),
                vp=vp, tb2=s2.mean(0), dl2=s2.std(0), zk2=(s2 - s2.mean(0)) / s2.std(0),
                dieu_chinh=dieu_chinh, xu_huong=xu_huong, de_hop=de_hop, la_xh=la_xh, kd_sua=kd_sua,
                m=mo, sp=sp, img=img, hop_thoi=hop_thoi)


# ================= KHO CỬA HÀNG
def _kho_hop_le():
    A = _tai()
    f = KQ / "an_san_pham.csv"
    da_an = set(pd.read_csv(f, dtype=str)["article_id"]) if f.exists() else set()
    return A["hop_thoi"] & ~A["sp"]["article_id"].isin(da_an).values


def _anh_trong():
    """Ảnh xám nhạt thay cho ảnh sản phẩm đã bị xóa khỏi máy."""
    out = io.BytesIO()
    Image.new("RGB", (240, 300), (240, 236, 236)).save(out, "JPEG", quality=80)
    return out.getvalue()


def _doc_anh_sp(k):
    """Đọc ảnh sản phẩm thứ k; ảnh đã bị xóa thì trả ảnh trống thay vì báo lỗi."""
    f = BASE / str(_tai()["sp"]["duong_dan_anh"][k])
    try:
        return f.read_bytes()
    except OSError:
        return _anh_trong()


def _mon_kho(k):
    A = _tai()
    sp = A["sp"]
    ma = sp["article_id"][k]
    return dict(v=A["img"][k].numpy(), nhom=sp["nhom_phoi"][k], nguon="kho", id=ma, k=int(k),
                kieu_dang=A["kd_sua"].get(ma), ten=f'{sp["prod_name"][k]} – {sp["colour_group_name"][k]}',
                bytes=_doc_anh_sp(k))



def kho_cua_hang():
    """Lấy sản phẩm hợp lệ và tự động loại bỏ sản phẩm trùng lặp."""
    A = _tai()
    mask = _kho_hop_le()

    # Sắp xếp trước để ưu tiên giữ sản phẩm có điểm xu hướng cao.
    ds = (
        A["sp"][mask]
        .assign(_xh=A["xu_huong"][mask])
        .sort_values("_xh", ascending=False)
        .copy()
    )

    # Loại các dòng có cùng mã sản phẩm.
    ds = ds.drop_duplicates(subset=["article_id"], keep="first")

    # Loại ảnh trùng nhau, kể cả khi mã sản phẩm khác nhau.
    da_gap = set()
    giu_lai = []

    for _, row in ds.iterrows():
        duong_dan = BASE / str(row["duong_dan_anh"])

        if not duong_dan.exists():
            continue

        try:
            ma_anh = hashlib.sha256(duong_dan.read_bytes()).hexdigest()
        except OSError:
            continue

        if ma_anh in da_gap:
            continue

        da_gap.add(ma_anh)
        giu_lai.append(row.name)

    return ds.loc[giu_lai].copy()



def mon_kho(k):
    return _mon_kho(int(k))


def an_mon_kho(ma_sp):
    f = KQ / "an_san_pham.csv"
    pd.DataFrame({"article_id": [ma_sp]}).to_csv(f, mode="a", header=not f.exists(), index=False)


def bo_an_mon_kho(ma_sp):
    """Bỏ trạng thái ẩn của sản phẩm (dùng khi người dùng quay lại món trước)."""
    f = KQ / "an_san_pham.csv"
    if not f.exists():
        return
    ds = pd.read_csv(f, dtype=str)
    if "article_id" not in ds.columns:
        return
    ds = ds[ds["article_id"] != str(ma_sp)]
    if ds.empty:
        f.unlink()
    else:
        ds.to_csv(f, index=False)


def sua_kho(ma_sp, nhom, kieu_dang=None):
    """Sửa tay loại món / kiểu dáng của một sản phẩm cửa hàng (lưu lại, có hiệu lực ngay)."""
    A = _tai()
    f = KQ / "sua_kho.csv"
    pd.DataFrame({"article_id": [ma_sp], "nhom": [nhom], "kieu_dang": [kieu_dang or ""]}) \
        .to_csv(f, mode="a", header=not f.exists(), index=False)
    A["sp"].loc[A["sp"]["article_id"] == ma_sp, "nhom_phoi"] = nhom
    if kieu_dang:
        A["kd_sua"][ma_sp] = kieu_dang
    else:
        A["kd_sua"].pop(ma_sp, None)


# ================= NHẬN DIỆN TỪ ẢNH
@st.cache_data(show_spinner=False)
def vector(b: bytes):
    A = _tai()
    im = Image.open(io.BytesIO(b)).convert("RGB")
    with torch.no_grad():
        return F.normalize(A["clip"].encode_image(A["pre"](im).unsqueeze(0)), dim=-1)[0].numpy()


def doan_nhom(v):
    return list(C.NHOM)[int((_tai()["vn"] @ torch.as_tensor(v)).argmax())]


def kieu_dang(m):
    if m.get("kieu_dang"):
        return m["kieu_dang"]
    ds = _tai()["vkd"].get(m["nhom"])
    if not ds:
        return None
    ma, e = ds
    return ma[int((e @ torch.as_tensor(m["v"])).argmax())]


def ten_kieu_dang(ma, nhom):
    return getattr(C, "KIEU_DANG", {}).get(nhom, {}).get(ma, ("", ""))[0]


def giong_tui_xach(v):
    s = _tai()["vb"] @ torch.as_tensor(v)
    return bool(s[0] > s[1])


def la_ao_khoac(v):
    A = _tai()
    t = torch.as_tensor(v)
    return bool(A["vk"] @ t > A["vt"] @ t)


def diem_ao_khoac(v):
    return float(_tai()["vk"] @ torch.as_tensor(v))


def la_chan_vay(v):
    s = _tai()["vs"] @ torch.as_tensor(v)
    return bool(s[0] > s[1])


def la_om(v):
    s = _tai()["vo"] @ torch.as_tensor(v)
    return bool(s[0] > s[1])


def do_rong(m):
    A = _tai()
    t = torch.as_tensor(m["v"])
    if m["nhom"] == "Áo":
        return torch.softmax(100 * (A["vf"] @ t), 0)[0].item()
    if m["nhom"] in ("Quần/Chân váy", "Đồ liền thân"):
        return torch.softmax(100 * (A["vo"] @ t), 0)[1].item()
    return 0.5


@st.cache_data(show_spinner=False)
def mau_chu_dao(b: bytes):
    """Màu chính: (sắc độ 0–360, bão hòa 0–1, sáng 0–1), bỏ nền trắng/xám nhạt."""
    im = Image.open(io.BytesIO(b)).convert("RGB").resize((64, 64))
    hsv = np.asarray(im.convert("HSV"), dtype=float) / 255.0
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    nen = (s < 0.12) & (v > 0.82)
    if (~nen).sum() < 50:
        nen = np.zeros_like(nen, dtype=bool)
    h, s, v = h[~nen], s[~nen], v[~nen]
    goc = np.radians(h)
    hh = (np.degrees(np.arctan2((np.sin(goc) * s).mean(), (np.cos(goc) * s).mean())) + 360) % 360
    return float(hh), float(np.median(s)), float(np.median(v))


@st.cache_data(show_spinner=False)
def so_mau_noi(b: bytes):
    im = Image.open(io.BytesIO(b)).convert("RGB").resize((64, 64))
    hsv = np.asarray(im.convert("HSV"), dtype=float) / 255.0
    h, s, v = hsv[..., 0] * 360, hsv[..., 1], hsv[..., 2]
    noi = (s > 0.35) & (v > 0.25)
    if noi.sum() < 40:
        return 0
    hist, _ = np.histogram(h[noi], bins=12, range=(0, 360))
    return int((hist > 0.08 * noi.sum()).sum())


@st.cache_data(show_spinner=False)
def bang_mau(b: bytes, so_mau: int = 4):
    """Bảng màu: [(sắc độ, bão hòa, sáng, tỷ lệ diện tích)], bỏ nền, bỏ màu dưới 5%."""
    im = Image.open(io.BytesIO(b)).convert("RGB").resize((80, 80))
    a = np.asarray(im).reshape(-1, 3)
    hsv = np.asarray(im.convert("HSV"), dtype=float).reshape(-1, 3) / 255.0
    nen = (hsv[:, 1] < 0.12) & (hsv[:, 2] > 0.82)
    if (~nen).sum() >= 60:
        a = a[~nen]
    q = Image.fromarray(a.reshape(1, -1, 3).astype(np.uint8)).quantize(colors=so_mau, method=0)
    pal = np.array(q.getpalette()[:so_mau * 3]).reshape(-1, 3)
    dem = np.bincount(np.asarray(q).ravel(), minlength=so_mau)[:so_mau]
    ket = []
    for rgb, c in zip(pal, dem):
        if c / dem.sum() < 0.05:
            continue
        h, s, v = colorsys.rgb_to_hsv(*(rgb / 255.0))
        ket.append((h * 360, s, v, c / dem.sum()))
    return ket


def ho_mau(h, s, v):
    """Họ màu: den, trang, xam, be_nau (trung tính) hoặc sac_0…sac_11 (màu có sắc, mỗi họ 30°)."""
    if v < 0.22:
        return "den"
    if s < 0.15:
        return "trang" if v > 0.82 else "xam"
    if 15 <= h <= 50 and (s < 0.55 or v < 0.55):
        return "be_nau"
    return f"sac_{int(h // 30) % 12}"


def cung_tong(m1, m2):
    """Hai màu cùng tông: cùng trung tính, hoặc sắc độ gần nhau."""
    h1, h2 = ho_mau(*m1), ho_mau(*m2)
    if h1 in TRUNG_TINH and h2 in TRUNG_TINH:
        return True
    if h1 in TRUNG_TINH or h2 in TRUNG_TINH:
        return False
    return min(abs(m1[0] - m2[0]), 360 - abs(m1[0] - m2[0])) < 35


def khop_mau(mau_mon, bang_neo):
    h, s, v = mau_mon
    trung_tinh = lambda s_, v_: s_ < 0.2 or v_ < 0.2
    if trung_tinh(s, v):
        return 1.0 if any(trung_tinh(s2, v2) and abs(v - v2) < 0.25 for _, s2, v2, _ in bang_neo) else 0.6
    tot = 0.0
    for h2, s2, v2, _ in bang_neo:
        if trung_tinh(s2, v2):
            continue
        dh = min(abs(h - h2), 360 - abs(h - h2))
        tot = max(tot, float(np.exp(-dh / 25) * np.exp(-abs(s - s2) / 0.5)))
    return tot


def dong_nhat_mau(ds):
    noi = [(h, s) for h, s, v in ds if s >= 0.2 and v >= 0.2]
    if not noi:
        return 0.8
    if len(noi) == 1:
        return 0.6
    gan = [float(np.exp(-min(abs(h1 - h2), 360 - abs(h1 - h2)) / 25) * np.exp(-abs(s1 - s2) / 0.5))
           for (h1, s1), (h2, s2) in itertools.combinations(noi, 2)]
    return float(np.mean(gan))


def ho_chat_lieu(v):
    p = torch.softmax(100 * (_tai()["vtx"] @ torch.as_tensor(v)), 0).numpy()
    return p / (np.linalg.norm(p) + 1e-8)


def do_ruom(m):
    p = torch.softmax(100 * (_tai()["vr"] @ torch.as_tensor(m["v"])), 0)[1].item()
    return 0.6 * p + 0.4 * min(1.0, max(0, so_mau_noi(m["bytes"]) - 1) / 3)


def la_mau_choi(b):
    dai = getattr(C, "MAU_KHONG_UA", [])
    if not dai:
        return False
    h, s, v = mau_chu_dao(b)
    nguong = getattr(C, "DO_RUC_TOI_THIEU", 0.55)
    return s > nguong and v > nguong and any(a <= h <= z for a, z in dai)


# ================= CHẤM ĐIỂM
def ma_tran_diem(V):
    m = _tai()["m"]
    V = torch.as_tensor(np.stack(V))
    return np.stack([diem(m, V[i], V) for i in range(len(V))])
def diem_bo(P, idx):
    """Tính điểm tổng hợp cho một outfit.

    Kết hợp điểm hợp trung bình giữa các cặp món
    và điểm của cặp món kém hợp nhất.
    """
    cap = [
        float(P[a, b])
        for a, b in itertools.combinations(idx, 2)
    ]

    if not cap:
        return 0.0

    trung_binh = float(np.mean(cap))

    # Outfit chỉ có 2 món: giữ nguyên điểm của cặp duy nhất.
    if len(cap) == 1:
        return trung_binh

    # Trọng số dành cho cặp món kém hợp nhất.
    w_yeu = float(
        np.clip(
            getattr(C, "TRONG_SO_CAP_YEU", 0.20),
            0.0,
            0.5
        )
    )

    diem_thap_nhat = float(np.min(cap))

    return (
        (1.0 - w_yeu) * trung_binh
        + w_yeu * diem_thap_nhat
    )


def diem_bo_mon(mon):
    if len(mon) < 2:
        return 0.0
    return diem_bo(ma_tran_diem([m["v"] for m in mon]), list(range(len(mon))))


def _diem_dip(V, j):
    if j is None:
        return np.zeros(len(V))
    A = _tai()
    return (np.stack(V) @ A["vd"][j].numpy() - A["tb"][j]) / A["dl"][j]


def _diem_pc(V, j):
    if j is None:
        return np.zeros(len(V))
    A = _tai()
    return (np.stack(V) @ A["vp"][j].numpy() - A["tb2"][j]) / A["dl2"][j]


def doan_phong_cach(V):
    if not V or not getattr(C, "PHONG_CACH", None):
        return None
    A = _tai()
    z = (np.stack(V) @ A["vp"].numpy().T - A["tb2"]) / A["dl2"]
    return int(z.mean(0).argmax())


def phu_hop_dip(V):
    A = _tai()
    s = np.stack(V) @ A["vd"].numpy().T
    return ((s - A["tb"]) / A["dl"]).mean(0)


# ================= GỢI Ý TỪ KHO
def _top_kho_theo_nhom(mon, nh, j_dip, k, j_pc=None):
    A = _tai()
    sp, IMG = A["sp"], A["img"]
    cand = np.where((sp["nhom_phoi"].values == nh) & _kho_hop_le())[0]
    if len(cand) == 0:
        return []
    s = np.mean([diem(A["m"], torch.as_tensor(u["v"]), IMG[cand]) for u in mon], axis=0) if mon else np.zeros(len(cand))
    if j_dip is not None:
        s = s + C.TRONG_SO_DIP * A["zk"][cand, j_dip]
    if j_pc is not None:
        s = s + getattr(C, "TRONG_SO_PHONG_CACH", 0.2) * A["zk2"][cand, j_pc]
    s = s - getattr(C, "PHAT_DE_TINH", 0.3) * A["de_hop"][cand]
    s = s + A["dieu_chinh"][cand] + getattr(C, "TRONG_SO_XU_HUONG", 0.3) * A["xu_huong"][cand]
    thu_tu = np.argsort(-s)
    if k <= 200 and getattr(C, "MAU_KHONG_UA", None):
        ket = []
        for o in thu_tu:
            kk = int(cand[o])
            f_anh = BASE / str(sp["duong_dan_anh"][kk])
            if not f_anh.exists():          # ảnh đã bị xóa khỏi máy: bỏ qua món này
                continue
            if la_mau_choi(f_anh.read_bytes()):
                continue
            ket.append((kk, float(s[o])))
            if len(ket) == k:
                break
        return ket
    return [(int(cand[o]), float(s[o])) for o in thu_tu[:k]]


def top_kho(mon, nh, j_dip, k):
    return [(_mon_kho(kk), s) for kk, s in _top_kho_theo_nhom(mon, nh, j_dip, k)]


def xep_hang_kho(mon, nh, j_dip):
    return _top_kho_theo_nhom(mon, nh, j_dip, 10 ** 6)


def goi_y_thay(mon, i, k):
    khac = [m for j, m in enumerate(mon) if j != i]
    return [dict(_mon_kho(kk), diem=s) for kk, s in _top_kho_theo_nhom(khac, mon[i]["nhom"], None, k)]


def thay_mon(pool, idx, i, j_dip=None, j_pc=None, loai_tru=()):
    khac = [pool[x] for x in idx if x != i]
    nh = pool[i]["nhom"]
    for kk, _ in _top_kho_theo_nhom(khac, nh, j_dip, 40, j_pc):
        mk = _mon_kho(kk)
        if mk["id"] in loai_tru:
            continue
        if nh == "Phụ kiện" and giong_tui_xach(mk["v"]):
            continue
        return mk
    return None


# ================= PHỐI ĐỒ
def _boc_tham(ung, so_lay, rng, nhiet):
    """Bốc so_lay món từ danh sách (món, điểm) đã xếp hạng.

    Món điểm cao vẫn dễ được chọn hơn (xác suất theo softmax(điểm / nhiệt)),
    nhưng mỗi lần phối sẽ ra một nhóm món hơi khác nhau thay vì luôn đúng top đầu.
    nhiet <= 0: lấy đúng top so_lay như cũ.
    """
    if len(ung) <= so_lay or nhiet <= 0:
        return ung[:so_lay]
    diem_ = np.array([s for _, s in ung], dtype=float)
    p = np.exp((diem_ - diem_.max()) / nhiet)
    p /= p.sum()
    chon_ = rng.choice(len(ung), size=so_lay, replace=False, p=p)
    return [ung[i] for i in sorted(chon_)]


def phoi(mon, j_dip, so_bo, ket_hop, bat_buoc=(), toi_da=None, j_pc=None, tranh_ids=(), thanh_phan=None,
         bo_thich=None, hat=None):
    """Ghép outfit theo mô hình + quy tắc stylist.

    hat: hạt ngẫu nhiên. Để None thì mỗi lần gọi một hạt mới, nên bấm phối lại
    sẽ ra bộ khác; truyền cùng một số thì kết quả lặp lại được (để kiểm tra).
    """
    rng = np.random.default_rng(hat)
    gioi_han = C.SO_MON_KHO_TOI_DA if toi_da is None else toi_da
    tp = set(thanh_phan) if thanh_phan else set(getattr(C, "MAC_DINH_THANH_PHAN",
                                                        ["ao_khoac", "giay", "tui", "phu_kien"]))
    bb = set(bat_buoc)
    if j_pc is None and bb and getattr(C, "TU_DOAN_PHONG_CACH", True):
        j_pc = doan_phong_cach([mon[i]["v"] for i in bb])
    pool = [dict(m, nguon=m.get("nguon", "tu")) for m in mon]
    if ket_hop:
        goc = [mon[i] for i in bb] or mon
        da_co = {m.get("id") for m in pool}
        so_lay = C.SO_MON_KHO_MOI_NHOM
        mo_rong = max(1.0, float(getattr(C, "HE_SO_UNG_VIEN_KHO", 3)))
        nhiet = float(getattr(C, "NHIET_DO_BOC_KHO", 0.08))
        for nh in C.NHOM:
            ung = _top_kho_theo_nhom(goc, nh, j_dip, int(so_lay * mo_rong), j_pc)
            for k, _ in _boc_tham(ung, so_lay, rng, nhiet):
                mk = _mon_kho(k)
                if mk["id"] not in da_co:
                    pool.append(mk)
    if len(pool) < 2:
        return [], pool

    A = _tai()
    n = len(pool)
    V = [m["v"] for m in pool]
    Vm = np.stack(V)
    P = ma_tran_diem(V)
    tb = (P.sum(1) - np.diag(P)) / max(n - 1, 1)
    Pc = P - getattr(C, "PHAT_DE_TINH", 0.3) * (tb[:, None] + tb[None, :]) / 2

    # Học từ bộ đồ đã lưu
    so_thich = np.zeros((n, n))
    for Vb in (bo_thich or []):
        S_ = Vm @ np.asarray(Vb).T
        for p_, q_ in itertools.combinations(range(S_.shape[1]), 2):
            M_ = np.minimum(S_[:, p_][:, None], S_[:, q_][None, :])
            so_thich = np.maximum(so_thich, np.maximum(M_, M_.T))
    ng_st = getattr(C, "NGUONG_SO_THICH", 0.8)
    so_thich = np.clip((so_thich - ng_st) / (1 - ng_st), 0, 1)
    w_st = getattr(C, "TRONG_SO_SO_THICH", 0.3)

    # Món trông giống nhau
    tuong_dong = Vm @ Vm.T
    nhom_arr = np.array([m["nhom"] for m in pool])
    la_pk = np.isin(nhom_arr, PHU_KIEN_NHOM)
    giong = (tuong_dong > getattr(C, "NGUONG_GIONG", 0.9)) | \
        ((tuong_dong > getattr(C, "NGUONG_GIONG_PHU_KIEN", 0.82)) & la_pk[:, None] & (nhom_arr[:, None] == nhom_arr[None, :]))

    # Điểm riêng từng món
    la_kho = np.array([m["nguon"] == "kho" for m in pool])
    tinh_gioi_han = la_kho & ~np.isin(nhom_arr, KHONG_TINH_GIOI_HAN)
    tinh_gioi_han[list(bb)] = False
    thuong = C.TRONG_SO_DIP * _diem_dip(V, j_dip) - C.PHAT_MON_KHO * la_kho \
        + getattr(C, "TRONG_SO_PHONG_CACH", 0.2) * _diem_pc(V, j_pc)
    w_xh = getattr(C, "TRONG_SO_XU_HUONG", 0.3)
    for i, m in enumerate(pool):
        if m.get("nguon") == "kho" and "k" in m:
            thuong[i] += A["dieu_chinh"][m["k"]] + w_xh * A["xu_huong"][m["k"]]

    # Món đã xuất hiện ở các lần phối gần đây (trừ món bạn tick) bị trừ điểm nhẹ,
    # xuất hiện càng nhiều lần càng bị trừ nhiều (tối đa 3 lần).
    dem_gan = {}
    for ma in tranh_ids:
        dem_gan[ma] = dem_gan.get(ma, 0) + 1
    phat_gan = getattr(C, "PHAT_DA_GOI_Y", 0.12)
    for i, m in enumerate(pool):
        if i not in bb and m.get("id") in dem_gan:
            thuong[i] -= phat_gan * min(dem_gan[m["id"]], 3)

    # Nhiễu nhỏ cho từng món: các bộ gần ngang điểm nhau sẽ luân phiên lên đầu.
    # Chỉ ảnh hưởng thứ tự chọn, không đổi điểm phối hiển thị.
    do_nn = float(getattr(C, "DO_NGAU_NHIEN", 0.06))
    if do_nn > 0:
        thuong = thuong + rng.normal(0, do_nn, n)
    kd = [kieu_dang(m) for m in pool]
    luat = getattr(C, "LUAT_DIP", {}).get(list(C.DIP)[j_dip], {}) if j_dip is not None else {}
    if luat:
        w_kd = getattr(C, "PHAT_KIEU_DANG", 0.15)
        for i in range(n):
            thuong[i] += w_kd * ((kd[i] in luat.get("uu_tien", [])) - (kd[i] in luat.get("tranh", [])))

    # Thuộc tính cho quy tắc stylist
    mau = [mau_chu_dao(m["bytes"]) for m in pool]
    bang = [bang_mau(m["bytes"]) for m in pool]
    ho_mon = [[(ho_mau(h, s, v), r) for h, s, v, r in bang[i]] or [(ho_mau(*mau[i]), 1.0)] for i in range(n)]
    ruom = np.array([do_ruom(m) for m in pool])
    rong = np.array([do_rong(m) for m in pool])
    tex = np.stack([ho_chat_lieu(m["v"]) for m in pool])
    ma_tex = list(getattr(C, "CHAT_LIEU_HOA_TIET", {"tron": ""}))
    tex_nhan = [ma_tex[int(t.argmax())] for t in tex]
    om = np.array([m["nhom"] in ("Quần/Chân váy", "Đồ liền thân") and la_om(m["v"]) for m in pool])
    la_bot = np.array([m["nhom"] == "Giày" and (kd[i] == "bot" or "boot" in (m.get("ten") or "").lower())
                       for i, m in enumerate(pool)])
    la_ngan = np.array([k_ in getattr(C, "KIEU_NGAN", []) for k_ in kd])
    la_dai_vay = np.array([k_ in getattr(C, "KIEU_DAI_KHONG_BOT", ["vay_dai", "vlt_dai"]) for k_ in kd])
    la_khoac_arr = np.array([m["nhom"] == "Áo" and la_ao_khoac(m["v"]) for m in pool])
    hs = (Vm @ A["vp"].numpy().T - A["tb2"]) / A["dl2"]
    hs = hs - hs.mean(1, keepdims=True)
    hs = hs / (np.linalg.norm(hs, axis=1, keepdims=True) + 1e-8)
    dong_bo = hs @ hs.T

    nguong_ruom = getattr(C, "NGUONG_RUOM", 0.5)
    noi_bat = np.array([ruom[i] > nguong_ruom or (mau[i][1] > 0.5 and mau[i][2] > 0.4 and ho_mau(*mau[i]) not in TRUNG_TINH)
                        for i in range(n)])
    TL = getattr(C, "TY_TRONG_DIEN_TICH", {"Áo": 0.35, "Quần/Chân váy": 0.3, "Đồ liền thân": 0.65,
                                            "Giày": 0.1, "Túi xách": 0.1, "Phụ kiện": 0.04})
    w_mau = getattr(C, "TRONG_SO_MAU", 1.0)
    w_db = getattr(C, "TRONG_SO_DONG_BO", 0.25)
    w_mt = getattr(C, "TRONG_SO_MAU_THEO", 0.2)
    w_ht = getattr(C, "TRONG_SO_HOA_TIET", 0.3)
    w_form = getattr(C, "TRONG_SO_FORM", 0.25)
    nguong_ho = getattr(C, "NGUONG_CUNG_HO", 0.8)
    toi_da_ruom = getattr(C, "TOI_DA_MON_RUOM", 1)
    phat_lap = getattr(C, "PHAT_LAP_LAI", 0.06)
    phat_bot = getattr(C, "PHAT_BOT_KHI_KHONG_NGAN", 0.10)
    thuong_bot = getattr(C, "THUONG_BOT_NGAN_OM", 0.06)

    theo = {nh: [i for i, m in enumerate(pool) if m["nhom"] == nh] for nh in C.NHOM}
    da_tick = {nh: [i for i in bb if pool[i]["nhom"] == nh] for nh in C.NHOM}
    theo["Phụ kiện"] = [i for i in theo["Phụ kiện"] if not giong_tui_xach(pool[i]["v"])]

    da_dung = np.zeros(n)
    tranh_ids = set(tranh_ids)
    for i, m in enumerate(pool):
        if i not in bb and m["nguon"] == "kho" and m["nhom"] in PHU_KIEN_NHOM and m.get("id") in tranh_ids:
            da_dung[i] = 1

    # ----- Quy tắc màu sắc
    def quy_tac_mau(idx):
        phan = {}
        for i in idx:
            w = TL.get(nhom_arr[i], 0.1)
            for ho, r in ho_mon[i]:
                phan[ho] = phan.get(ho, 0.0) + w * r
        tong_p = sum(phan.values()) or 1.0
        chinh = [h_ for h_, p in phan.items() if p / tong_p >= 0.08]
        sac = [h_ for h_ in chinh if h_ not in TRUNG_TINH]
        d = -0.10 * max(0, len(chinh) - 3)                                       # tối đa 3 màu chính
        if not sac:
            d += 0.03                                                            # toàn trung tính: dễ phối
        ty = sorted((phan[h_] / tong_p for h_ in chinh), reverse=True)
        t3 = (ty + [0.0, 0.0, 0.0])[:3]
        d += 0.10 * (0.5 - 0.5 * sum(abs(a - b) for a, b in zip(t3, (0.6, 0.3, 0.1))))   # 60-30-10
        so_bin = sorted(int(h_[4:]) for h_ in sac)
        if len(so_bin) >= 2 and all(min((b1 - b2) % 12, (b2 - b1) % 12) <= 1
                                    for b1, b2 in itertools.combinations(so_bin, 2)):
            d += 0.04                                                            # phối cùng tông
        if len(sac) == 1 and phan[sac[0]] / tong_p <= 0.25:
            d += 0.04                                                            # một màu nhấn
        nhieu_mau = len(sac) >= 2 or any(ruom[i] > nguong_ruom for i in idx if not la_pk[i])
        if nhieu_mau:
            d -= 0.04 * sum(nhom_arr[i] == "Phụ kiện" for i in idx)             # nhiều màu → giảm phụ kiện
        d -= 0.08 * max(0, int(noi_bat[idx].sum()) - 1)                         # tối đa một món nổi bật
        g = [i for i in idx if nhom_arr[i] == "Giày"]
        t = [i for i in idx if nhom_arr[i] == "Túi xách"]
        if g and t:                                                              # giày và túi cùng tông/phong cách
            d += 0.03 if (cung_tong(mau[g[0]], mau[t[0]]) or dong_bo[g[0], t[0]] > 0.5) else -0.03
        return d

    # ----- Quy tắc theo món chính, họa tiết, form, bốt
    def theo_mon_chinh(idx):
        neo = [i for i in idx if i in bb] or idx[:1]
        khac = [i for i in idx if i not in neo]
        if not khac:
            return 0.0
        lap_mau = float(np.mean([max(khop_mau(mau[i], bang[a]) for a in neo) for i in khac]))
        dm = max(lap_mau, dong_nhat_mau([mau[i] for i in khac])) - 0.5
        dh = []
        for i in [i for i in khac if not la_pk[i]]:
            cung_ho = max(float(tex[i] @ tex[a]) for a in neo)
            if cung_ho >= nguong_ho:
                dh.append(0.5)
            elif ruom[i] <= nguong_ruom:
                dh.append(0.2)
            else:
                dh.append(-0.5)
        return w_mt * dm + w_ht * (float(np.mean(dh)) if dh else 0.0)
    def qua_ruom(idx):
        ban = [i for i in idx if not la_pk[i] and ruom[i] > nguong_ruom]
        ho = {tex_nhan[i] for i in ban}
        phat = max(0, len(ho) - toi_da_ruom)
        if phat and len(ban) > 1 and all(max(khop_mau(mau[i], bang[j]) for j in ban if j != i) >= 0.6 for i in ban):
            phat *= 0.5                                                          # mix họa tiết cùng bảng màu
        d = -w_ht * phat
        if {"cham_bi", "ke_soc"} <= ho:
            d -= w_ht * 0.5                                                      # chấm bi + kẻ sọc
        return d

    def diem_form(idx):
        ao_i = [i for i in idx if nhom_arr[i] == "Áo" and not la_khoac_arr[i]]
        duoi_i = [i for i in idx if nhom_arr[i] == "Quần/Chân váy"]
        if not ao_i or not duoi_i:
            return 0.0
        ra, rd = max(rong[i] for i in ao_i), max(rong[i] for i in duoi_i)
        return w_form * (0.5 * max(abs(ra - rd), (1 - ra) * (1 - rd)) - ra * rd)

    def luat_bot(idx):
        if not la_bot[idx].any():
            return 0.0
        if la_dai_vay[idx].any():
            return -1.0
        if (la_ngan & om)[idx].any():
            return thuong_bot
        if la_ngan[idx].any():
            return 0.0
        return -phat_bot

    def tong(idx):
        cap = list(itertools.combinations(idx, 2))
        lap = [da_dung[i] for i in idx if i not in bb]
        return (float(np.mean([Pc[a, b] for a, b in cap])) if cap else 0.0) \
            + float(np.mean(thuong[idx])) \
            - phat_lap * (float(np.mean(lap)) if lap else 0.0) \
            + w_mau * quy_tac_mau(idx) \
            + w_db * (float(np.mean([dong_bo[a, b] for a, b in cap])) if cap else 0.0) \
            + theo_mon_chinh(idx) + qua_ruom(idx) + diem_form(idx) + luat_bot(idx) \
            + w_st * (float(np.mean([so_thich[a, b] for a, b in cap])) if cap else 0.0)

    def con_cho(idx):
        return tinh_gioi_han[idx].sum() <= gioi_han

    def loc_chua_dung(ung):
        if not getattr(C, "KHONG_LAP_PHU_KIEN", True):
            return ung
        return [x for x in ung if da_dung[x] == 0] or ung

    def chon_mot(idx, nhom):
        if da_tick.get(nhom):
            idx.append(da_tick[nhom][0])
            return
        ung = loc_chua_dung([x for x in theo.get(nhom, []) if x not in idx and con_cho(idx + [x])])
        if ung:
            idx.append(max(ung, key=lambda x: tong(idx + [x])))

    # ----- Phần thân outfit
    ao_tick = da_tick["Áo"][:2]
    loi_tick = set(ao_tick + da_tick["Quần/Chân váy"] + da_tick["Đồ liền thân"])
    khoac = {i for i in theo["Áo"] if la_khoac_arr[i]}
    ao_trong = [i for i in theo["Áo"] if i not in khoac]
    quan = theo["Quần/Chân váy"]
    chon_than = bool(thanh_phan) and bool({"ao", "quan", "vay_lien"} & tp)
    muon_ao = (not chon_than) or "ao" in tp or bool(ao_tick)
    muon_quan = (not chon_than) or "quan" in tp or bool(da_tick["Quần/Chân váy"])
    muon_vay = (not chon_than) or "vay_lien" in tp or bool(da_tick["Đồ liền thân"])
    if len(ao_tick) == 2:
        ao_opts = [ao_tick]
    elif len(ao_tick) == 1 and ao_tick[0] in khoac:
        ao_opts = [[a, ao_tick[0]] for a in ao_trong]
    elif len(ao_tick) == 1:
        ao_opts = [[ao_tick[0]]]
    else:
        ao_opts = [[a] for a in ao_trong]
    quan_opts = [[q] for q in quan]
    loi = []
    if muon_ao and muon_quan:
        loi += [A_ + Q_ for A_ in ao_opts for Q_ in quan_opts]
    elif muon_ao:
        loi += ao_opts
    elif muon_quan:
        loi += quan_opts
    if muon_vay and (not ao_tick or (len(ao_tick) == 1 and ao_tick[0] in khoac)):
        loi += [[d] + ao_tick for d in theo["Đồ liền thân"]]
    loi = [l for l in loi if loi_tick <= set(l) and con_cho(l)]

    def khac_du(idx, cu):
        rieng = [i for i in idx if i not in bb]
        cu_rieng = [i for i in cu if i not in bb]
        so_khac = sum(1 for i in rieng if not (cu_rieng and giong[i, cu_rieng].any()))
        return so_khac >= min(2, len(rieng))

    def them_khoac(idx):
        if any(i in khoac for i in idx):
            return
        ung = loc_chua_dung([x for x in khoac if x not in idx and con_cho(idx + [x])])
        if ung:
            idx.append(max(ung, key=lambda x: tong(idx + [x])))

    # Tủ đồ có giày / túi / phụ kiện của bạn thì phần thân lấy toàn món cửa hàng vẫn hợp lệ
    co_pk_tu = any(
        not la_kho[i]
        for nh in ("Giày", "Túi xách", "Phụ kiện")
        for i in theo.get(nh, [])
    )

    # ----- Chọn lần lượt từng outfit
    chon = []
    for _ in range(so_bo):
        loi_dung_duoc = loi
        if getattr(C, "KHONG_LAP_PHAN_THAN", True) and chon:
            loi_dung_duoc = [l for l in loi if all(da_dung[i] == 0 for i in l if i not in bb)] or loi
        ung_vien = []
        for l in sorted(loi_dung_duoc, key=lambda l: -tong(l)):
            # Lấy đủ 60 ứng viên HỢP LỆ (có ít nhất một món của bạn), thay vì cắt
            # 60 cách ghép đầu rồi mới lọc: trước đây nếu 60 cách đầu toàn món cửa
            # hàng thì không còn bộ nào và trang báo "chưa phối được".
            if len(ung_vien) >= 60:
                break
            if not (bb or co_pk_tu or (~la_kho[list(l)]).any()):
                continue
            idx = list(l)
            if "ao_khoac" in tp:
                them_khoac(idx)
            if "giay" in tp or da_tick["Giày"]:
                chon_mot(idx, "Giày")
            if "tui" in tp or da_tick["Túi xách"]:
                chon_mot(idx, "Túi xách")
            if da_tick["Phụ kiện"]:
                idx += [x for x in da_tick["Phụ kiện"] if x not in idx]
            elif "phu_kien" in tp:
                chon_mot(idx, "Phụ kiện")
            if (~la_kho[idx]).any() or bb:
                ung_vien.append((tong(idx), idx))
        ung_vien.sort(key=lambda x: -x[0])
        moi = next((idx for _, idx in ung_vien if all(khac_du(idx, c[0]) for c in chon)), None)
        if moi is None:
            break
        chon.append((moi, diem_bo(P, moi)))
        for i in moi:
            if i not in bb:
                da_dung[giong[i]] += 1
    return chon, pool


# ================= BỘ SƯU TẬP DỰNG SẴN (dùng lại hàm phoi, không cần tủ đồ người dùng)
@st.cache_data(show_spinner=False, max_entries=30)
def bo_suu_tap(j_pc, so_bo=5, hat=0):
    """Các bộ đồ dựng sẵn từ kho cửa hàng cho một phong cách.

    Lấy vài áo / váy liền hợp phong cách nhất làm "món chính", rồi để hàm phoi
    ghép quần, giày, túi, phụ kiện từ kho như khi phối cho người dùng.
    hat cố định nên bộ sưu tập ổn định giữa các lần mở trang.
    Trả về [{"mon": [món...], "diem": điểm}, ...]
    """
    neo, da_co = [], set()
    for nh, so in (("Áo", 4), ("Đồ liền thân", 2)):
        for k, _ in _top_kho_theo_nhom([], nh, None, so * 4, j_pc):
            m = _mon_kho(k)
            if m["id"] in da_co or (nh == "Áo" and la_ao_khoac(m["v"])):
                continue
            da_co.add(m["id"])
            # đánh dấu "tu" để hàm phoi coi đây là món chính của bộ
            neo.append(dict(m, nguon="tu", neo=True))
            if sum(x["nhom"] == nh for x in neo) >= so:
                break
    if not neo:
        return []

    def _sach(m):
        m = dict(m)
        m.pop("neo", None)
        m["nguon"] = "kho"
        return m

    try:
        chon, pool = phoi(neo, None, so_bo, True, (), 3, j_pc, (), None, None, hat=hat)
    except Exception:
        chon, pool = [], []

    ket = [
        {"mon": [_sach(pool[i]) for i in idx], "diem": float(d)}
        for idx, d in chon
    ]

    # Dự phòng: hàm phoi không ra đủ bộ thì ghép trực tiếp quanh từng món chính,
    # mỗi loại còn thiếu lấy món hợp nhất với các món đã có trong bộ.
    da_dung_neo = {m["id"] for b in ket for m in b["mon"]}
    for m0 in neo:
        if len(ket) >= so_bo:
            break
        if m0["id"] in da_dung_neo:
            continue
        mon_bo = [m0]
        can = (["Quần/Chân váy"] if m0["nhom"] == "Áo" else []) + ["Giày", "Túi xách", "Phụ kiện"]
        for nh in can:
            try:
                ung = _top_kho_theo_nhom(mon_bo, nh, None, 1, j_pc)
            except Exception:
                ung = []
            if ung:
                mon_bo.append(_mon_kho(ung[0][0]))
        if len(mon_bo) >= 2:
            ket.append({
                "mon": [_sach(m) for m in mon_bo],
                "diem": float(diem_bo_mon(mon_bo)),
            })
    return ket


@st.cache_data(show_spinner=False, ttl=600)
def thong_ke_kho():
    """Số sản phẩm đang bán theo loại món và theo phong cách nổi trội (cho trang Thống kê)."""
    A = _tai()
    mask = _kho_hop_le()
    sp = A["sp"][mask]
    theo_loai = sp["nhom_phoi"].value_counts().to_dict()
    ds_pc = list(getattr(C, "PHONG_CACH", {}))
    theo_pc = {}
    if ds_pc:
        pc_cua_mon = np.asarray(A["zk2"])[mask].argmax(1)
        for j in pc_cua_mon:
            theo_pc[ds_pc[int(j)]] = theo_pc.get(ds_pc[int(j)], 0) + 1
    return {"tong": int(mask.sum()), "theo_loai": theo_loai, "theo_phong_cach": theo_pc}


def ten_mau(b):
    """Tên họ màu chủ đạo của ảnh (dùng cho thống kê và nhãn bảng màu)."""
    ho = ho_mau(*mau_chu_dao(b))
    return {
        "den": "Đen", "trang": "Trắng", "xam": "Xám", "be_nau": "Be / nâu",
        "sac_0": "Đỏ", "sac_1": "Cam", "sac_2": "Vàng", "sac_3": "Xanh cốm",
        "sac_4": "Xanh lá", "sac_5": "Xanh ngọc", "sac_6": "Xanh lơ", "sac_7": "Xanh dương",
        "sac_8": "Xanh tím", "sac_9": "Tím", "sac_10": "Hồng tím", "sac_11": "Hồng",
    }.get(ho, ho)


# ================= GHÉP ẢNH
def anh_bo(ds):
    nen = Image.new("RGB", C.KICH_THUOC_BANG, C.MAU_NEN_BANG)
    dem = {"Áo": 1} if any(nh == "Đồ liền thân" for _, nh in ds) else {}
    for b, nh in ds:
        k = dem.get(nh, 0)
        dem[nh] = k + 1
        if k >= len(C.VI_TRI_BANG.get(nh, [])):
            continue
        x, y, w, h = C.VI_TRI_BANG[nh][k]
        im = Image.open(io.BytesIO(b)).convert("RGB")
        im.thumbnail((w, h))
        nen.paste(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))
    return nen



def anh_lookbook(anh_nguoi, mon_kem):
    if anh_nguoi is None:
        return None

    if isinstance(anh_nguoi, Image.Image):
        ng = anh_nguoi.convert("RGB")
    elif isinstance(anh_nguoi, (bytes, bytearray)):
        ng = Image.open(io.BytesIO(anh_nguoi)).convert("RGB")
    else:
        ng = Image.open(anh_nguoi).convert("RGB")

    cat = getattr(C, "CAT_CHAN", 0)
    if cat > 0:
        ng = ng.crop((0, 0, ng.width, int(ng.height * (1 - cat))))
    ng.thumbnail((480, 640))
    H = max(ng.height, 640)
    nen = Image.new("RGB", (ng.width + 240, H), "white")
    nen.paste(ng, (0, (H - ng.height) // 2))
    ds = mon_kem[:5]
    if ds:
        o = H // len(ds)
        for k, b in enumerate(ds):
            im = Image.open(io.BytesIO(b)).convert("RGB")
            im.thumbnail((200, o - 20))
            nen.paste(im, (ng.width + 20 + (200 - im.width) // 2, k * o + (o - im.height) // 2))
    return nen


def thu_nho(b: bytes) -> bytes:
    im = Image.open(io.BytesIO(b)).convert("RGB")
    co = getattr(C, "CO_ANH_XU_LY", 768)
    if max(im.size) <= co:
        return b
    im.thumbnail((co, co))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=92)
    return out.getvalue()


@st.cache_resource(show_spinner="Đang nạp mô hình tách nền…")
def _phien_tach_nen():
    from rembg import new_session
    return new_session(getattr(C, "MO_HINH_TACH_NEN", "u2netp"))


@st.cache_data(show_spinner="Đang tách nền ảnh…")
def tach_nen(b: bytes) -> bytes:
    from rembg import remove
    im = Image.open(io.BytesIO(thu_nho(b))).convert("RGB")
    im = remove(im, session=_phien_tach_nen()).convert("RGBA")
    khung = im.split()[3].getbbox()
    if khung:
        x0, y0, x1, y1 = khung
        le = 20
        im = im.crop((max(0, x0 - le), max(0, y0 - le), min(im.width, x1 + le), min(im.height, y1 + le)))
    nen = Image.new("RGB", im.size, "white")
    nen.paste(im, mask=im.split()[3])
    out = io.BytesIO()
    nen.save(out, "JPEG", quality=92)
    return out.getvalue()


# ================= MẶC THỬ ẢO
def mac_duoi_duoc(m_duoi):
    if m_duoi is None or not getattr(C, "MAC_PHAN_DUOI", False):
        return False
    return getattr(C, "MAC_CHAN_VAY", False) or not la_chan_vay(m_duoi["v"])


def mac_thu(anh_mau, m, m_duoi=None):
    """Mặc thử món m (và phần dưới m_duoi nếu có) lên ảnh người mẫu anh_mau."""
    from thu_do import thu_do

    def mo_ta(x):
        kd = kieu_dang(x)

        # Lấy thông tin sản phẩm gốc
        if x.get("nguon") == "kho":
            A = _tai()
            hang = A["sp"][A["sp"]["article_id"] == x.get("id")]

            if len(hang):
                h = hang.iloc[0]
                mo_ta_goc = (
                    f'{h["colour_group_name"]} '
                    f'{h["product_type_name"]}, '
                    f'{h["prod_name"]}'
                ).lower()
            else:
                mo_ta_goc = x["ten"]
        else:
            mo_ta_goc = x.get("ten", "clothing item")

        # Bổ sung chính xác độ dài và kiểu dáng
        if kd == "vay_ngan":
            return (
                f"{mo_ta_goc}, a short mini skirt, "
                "the hem must end clearly above the knee, "
                "preserve the original short length, shape and hemline. "
                "Do not turn it into a midi or long skirt."
            )

        if kd == "vay_lung":
            return (
                f"{mo_ta_goc}, a midi skirt, "
                "preserve the original length and hemline."
            )

        if kd == "vay_dai":
            return (
                f"{mo_ta_goc}, a long maxi skirt, "
                "preserve the original length and hemline."
            )

        if kd:
            return C.KIEU_DANG.get(x["nhom"], {}).get(kd, ("", ""))[1] or mo_ta_goc

        return {
            "Đồ liền thân": "a dress",
            "Quần/Chân váy": "trousers",
        }.get(x["nhom"], "a top")

    def anh(x):
        return Image.open(io.BytesIO(x["bytes"])).convert("RGB")

    loai = "dress" if m["nhom"] == "Đồ liền thân" else "upper"
    mac_duoi = loai == "upper" and mac_duoi_duoc(m_duoi)

    nen = Path(anh_mau)

    kd_nen = (
        kieu_dang(m_duoi) if mac_duoi
        else kieu_dang(m) if loai == "dress"
        else None
    ) or ""

    # Chọn ảnh người mẫu nền hợp kiểu dáng (vd. dang_manh_vay.jpg)
    if kd_nen:
        ds_nen = getattr(C, "NEN_THEO_KIEU", {}).get(
            kd_nen, ["_vay"] if kd_nen.startswith("vay") else []
        )

        for hau_to in ds_nen:
            ung_vien = nen.with_name(nen.stem + hau_to + ".jpg")
            if ung_vien.exists():
                nen = ung_vien
                break

    # Thử đúng sản phẩm được chọn
    kq = thu_do(nen, anh(m), mo_ta(m), loai)

    # Nếu có quần/chân váy thì thử thêm phần dưới
    if mac_duoi and kq is not None:
        kq = thu_do(
            kq,
            anh(m_duoi),
            mo_ta(m_duoi),
            "lower"
        )

    if kq is None:
        raise RuntimeError("thu_do không trả về ảnh")

    # Giữ khuôn mặt người mẫu gốc (nếu thu_do.py có hàm này)
    if getattr(C, "GIU_KHUON_MAT", True):
        try:
            from thu_do import giu_khuon_mat
        except ImportError:
            giu_khuon_mat = None

        if giu_khuon_mat is not None:
            kq = giu_khuon_mat(nen, kq)

    return kq