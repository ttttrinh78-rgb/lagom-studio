
# thu_do.py — Thử đồ ảo qua Hugging Face Spaces
# Áo: IDM-VTON (dự phòng Change-Clothes-AI)
# Quần/chân váy, váy liền: Change-Clothes-AI (dự phòng OOTDiffusion)

import os
import tempfile
import inspect
import hashlib
import shutil
from pathlib import Path

from gradio_client import Client, handle_file


SPACE = {
    "idm": "yisol/IDM-VTON",
    "cc": "jallenjia/Change-Clothes-AI",
    "ootd": "levihsu/OOTDiffusion"
}

LOAI_CC = {
    "upper": "upper_body",
    "lower": "lower_body",
    "dress": "dresses"
}

LOAI_OOTD = {
    "upper": "Upper-body",
    "lower": "Lower-body",
    "dress": "Dress"
}

THU_TU = {
    "upper": ["idm", "cc"],
    "lower": ["cc", "ootd"],
    "dress": ["cc", "ootd"]
}

KHO_ANH = Path(__file__).parent / "ket_qua" / "thu_do"
_client = {}


# ================= KẾT NỐI MÔ HÌNH

def _ket_noi(ten):
    if ten not in _client:
        tk = os.environ.get("HF_TOKEN")
        ts = inspect.signature(Client.__init__).parameters

        kw = {
            ("token" if "token" in ts else "hf_token"): tk
        } if tk else {}

        _client[ten] = Client(SPACE[ten], **kw)

    return _client[ten]


# ================= ẢNH TẠM

def _luu_tam(im):
    p = tempfile.NamedTemporaryFile(
        suffix=".jpg",
        delete=False
    ).name

    im.convert("RGB").save(p, quality=95)
    return p


def _xoa_file_tam(ds):
    for p in ds:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except OSError:
            pass


# ================= LẤY ẢNH KẾT QUẢ

def _anh_ket_qua(kq):
    x = kq

    while isinstance(x, (list, tuple)):
        if not x:
            raise ValueError("Mô hình không trả về ảnh.")
        x = x[0]

    if isinstance(x, dict):
        x = x.get("image") or x.get("path") or x.get("url")

    if isinstance(x, dict):
        x = x.get("path") or x.get("url")

    if not x:
        raise ValueError("Không tìm thấy ảnh kết quả.")

    return x


# ================= CHỌN LOẠI TRANG PHỤC

def _gia_tri_loai(cl, api, du_doan, loai):
    try:
        ps = cl.view_api(
            print_info=False,
            return_format="dict"
        )["named_endpoints"][api]["parameters"]

        p = next(
            p for p in ps
            if p.get("parameter_name") == "category"
        )

        for x in (p.get("type") or {}).get("enum") or []:
            if loai in str(x).lower():
                return x

    except Exception:
        pass

    return du_doan[loai]


# ================= MÔ TẢ GIỮ ĐÚNG SẢN PHẨM

def _mo_ta_chinh_xac(mo_ta, loai):
    yeu_cau_chung = """
    IMPORTANT GARMENT PRESERVATION:
    Use the exact clothing item shown in the garment reference image.
    Preserve its original color, shape, silhouette, neckline,
    sleeves, length, fabric appearance, texture, pattern,
    seams, buttons, straps and all visible design details.
    Do not replace it with a similar item.
    Do not invent additional clothing details.
    Do not change the garment into another clothing category.
    Keep the garment visually as close as possible to the reference.
    """

    yeu_cau_chan_tran = """
    IMPORTANT FOOTWEAR INSTRUCTION:
    The model must be barefoot.
    Both feet must be visible naturally without shoes.
    Do not generate high heels, sandals, sneakers, boots,
    slippers, socks or any other footwear.
    Do not add footwear even if it would match the outfit.
    """

    if loai == "upper":
        loai_cu_the = """
        Apply the referenced upper-body garment only.
        Preserve the existing lower-body clothing.
        """

    elif loai == "lower":
        loai_cu_the = """
        Apply the referenced lower-body garment only.
        Preserve the existing upper-body clothing.
        """

    else:
        loai_cu_the = """
        Apply the referenced one-piece dress or jumpsuit.
        Preserve the original design and length.
        """

    return (
        str(mo_ta)
        + "\n"
        + yeu_cau_chung
        + "\n"
        + loai_cu_the
        + "\n"
        + yeu_cau_chan_tran
    )


# ================= IDM-VTON

def _idm(anh_nguoi, anh_do, mo_ta, loai):
    p = _luu_tam(anh_do)

    try:
        kq = _ket_noi("idm").predict(
            dict={
                "background": handle_file(str(anh_nguoi)),
                "layers": [],
                "composite": None
            },
            garm_img=handle_file(p),
            garment_des=mo_ta,
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            api_name="/tryon"
        )

        return _anh_ket_qua(kq)

    finally:
        _xoa_file_tam([p])


# ================= CHANGE-CLOTHES-AI

def _cc(anh_nguoi, anh_do, mo_ta, loai):
    cl = _ket_noi("cc")
    p = _luu_tam(anh_do)

    try:
        kq = cl.predict(
            dict={
                "background": handle_file(str(anh_nguoi)),
                "layers": [],
                "composite": None
            },
            garm_img=handle_file(p),
            garment_des=mo_ta,
            is_checked=True,
            is_checked_crop=False,
            denoise_steps=30,
            seed=42,
            category=_gia_tri_loai(
                cl,
                "/tryon",
                LOAI_CC,
                loai
            ),
            api_name="/tryon"
        )

        return _anh_ket_qua(kq)

    finally:
        _xoa_file_tam([p])


# ================= OOTDIFFUSION

def _ootd(anh_nguoi, anh_do, mo_ta, loai):
    cl = _ket_noi("ootd")
    p = _luu_tam(anh_do)

    try:
        kq = cl.predict(
            vton_img=handle_file(str(anh_nguoi)),
            garm_img=handle_file(p),
            category=_gia_tri_loai(
                cl,
                "/process_dc",
                LOAI_OOTD,
                loai
            ),
            n_samples=1,
            n_steps=20,
            image_scale=2,
            seed=42,
            api_name="/process_dc"
        )

        return _anh_ket_qua(kq)

    finally:
        _xoa_file_tam([p])


HAM = {
    "idm": _idm,
    "cc": _cc,
    "ootd": _ootd
}


# ================= THỬ ĐỒ

def thu_do(
    anh_nguoi,
    anh_do,
    mo_ta="a clothing item",
    loai="upper"
):
    """
    anh_nguoi: đường dẫn ảnh người mẫu.
    anh_do: ảnh PIL của sản phẩm.
    mo_ta: mô tả sản phẩm.
    loai: upper, lower hoặc dress.

    Kết quả được lưu để không phải tạo lại ảnh nhiều lần.
    """

    if loai not in THU_TU:
        raise ValueError(
            "Loại trang phục không hợp lệ: " + str(loai)
        )

    if not Path(anh_nguoi).exists():
        raise FileNotFoundError(
            f"Không tìm thấy ảnh người mẫu: {anh_nguoi}"
        )

    KHO_ANH.mkdir(
        parents=True,
        exist_ok=True
    )

    mo_ta_day_du = _mo_ta_chinh_xac(
        mo_ta,
        loai
    )

    # Đưa mô tả vào mã cache để khi thay đổi yêu cầu
    # hệ thống không dùng lại ảnh thử đồ cũ.
    ma = hashlib.sha256(
        Path(anh_nguoi).read_bytes()
        + anh_do.convert("RGB").tobytes()
        + loai.encode("utf-8")
        + mo_ta_day_du.encode("utf-8")
    ).hexdigest()[:24]

    da_luu = KHO_ANH / f"{ma}.png"

    if da_luu.exists():
        return str(da_luu)

    loi = None

    for dv in THU_TU[loai]:
        try:
            ket_qua = HAM[dv](
                anh_nguoi,
                anh_do,
                mo_ta_day_du,
                loai
            )

            if not ket_qua or not Path(str(ket_qua)).exists():
                raise ValueError(
                    f"{dv} không trả về đường dẫn ảnh hợp lệ."
                )

            shutil.copy2(
                ket_qua,
                da_luu
            )

            return str(da_luu)

        except Exception as e:
            loi = e

            if "quota" in str(e).lower():
                break

    raise RuntimeError(
        f"Không thể thử đồ bằng các mô hình hiện có. Lỗi cuối: {loi}"
    ) from loi
