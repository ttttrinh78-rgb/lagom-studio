# app.py — Lagom Studio. Chạy: python3.12 -m streamlit run app.py
import itertools, re, hashlib, inspect
from copy import deepcopy
from html import escape as esc
from pathlib import Path
import numpy as np, streamlit as st

# Chạy bằng "python app.py" (hoặc nút ▶ Run Python File của VS Code) thì Streamlit
# không hoạt động: in hướng dẫn rồi dừng thay vì báo lỗi khó hiểu.
try:
    from streamlit.runtime import exists as _co_streamlit
    if not _co_streamlit():
        print(
            "\n  App này phải chạy bằng Streamlit. Gõ lệnh sau trong Terminal:\n"
            "      python3.12 -m streamlit run app.py\n"
        )
        raise SystemExit(0)
except ImportError:
    pass

if not hasattr(st, "cache"):
    st.cache = st.cache_data

from streamlit_cookies_manager import EncryptedCookieManager
import cai_dat as C, tai_khoan as TK, ai as AI

BASE = Path(__file__).parent
ICON = str(BASE / C.ICON_APP) if (BASE / C.ICON_APP).exists() else C.ICON_APP
st.set_page_config(page_title=C.TEN_APP, page_icon=ICON, layout="wide")

cookies = EncryptedCookieManager(
    prefix="mixme/",
    password=st.secrets["cookie_password"]
)
if not cookies.ready:
    st.stop()

if (BASE / "style.css").exists():
    st.markdown(
        f"<style>{(BASE / 'style.css').read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True
    )

# Chặn Google Dịch tự dịch giao diện. Streamlit mới: st.html chạy được script
# (unsafe_allow_javascript); bản cũ hơn: dùng components.html (iframe cùng origin).
JS_KHONG_DICH = """
<script>
const d = window.parent.document;
d.documentElement.setAttribute('translate', 'no');
d.documentElement.lang = 'vi';
d.body.classList.add('notranslate');

if (!d.querySelector('meta[name="google"]')) {
    const m = d.createElement('meta');
    m.name = 'google';
    m.content = 'notranslate';
    d.head.appendChild(m);
}
</script>
"""
if "unsafe_allow_javascript" in inspect.signature(st.html).parameters:
    st.html(JS_KHONG_DICH, unsafe_allow_javascript=True)
else:
    # Chỉ nạp khi cần, vì Streamlit mới báo components.v1.html sắp bị bỏ
    import streamlit.components.v1 as components
    components.html(JS_KHONG_DICH, height=0)


MAC_PHAN_DUOI = getattr(C, "MAC_PHAN_DUOI", False)

CHU_THICH_LB = (
    "Người mẫu mặc thử áo và quần/chân váy (ảnh do AI tạo) · bên phải: các món còn lại của bộ"
    if MAC_PHAN_DUOI else
    "Người mẫu mặc thử phần áo (ảnh do AI tạo) · bên phải: các món còn lại của bộ"
)

SO_ANH_CACHE = 60      # số ảnh tải lên đã xử lý được giữ lại trong phiên
SO_ANH_THU_CACHE = 20  # số ảnh mặc thử được giữ lại trong phiên


def badge(s):
    k = "rat" if s >= C.NGUONG_RAT_HOP else "kha" if s >= C.NGUONG_KHA_HOP else "it"
    chu, mau = C.NHAN_DIEM[k]
    return (
        f'<span class="badge badge-{k}">'
        f'<i style="background:{mau}"></i>{chu} · {s * 100:.0f}%</span>'
    )


def hero(mo_ta="", giua=False, anh=None):
    import base64

    lop = "hero center" if giua else "hero"
    phu = f'<p class="hero-sub">{mo_ta}</p>' if mo_ta else ""

    chip = "".join(
        f'<span class="hero-chip">{c}</span>'
        for c in getattr(C, "CHIP_TRANG_CHU", [])
    ) if anh else ""

    hinh = (
        f'<img class="hero-img" src="data:image/jpeg;base64,'
        f'{base64.b64encode(Path(anh).read_bytes()).decode()}">'
        if anh else ""
    )

    st.markdown(
        f'<div class="{lop}">'
        f'<div class="hero-text">'
        f'<div class="logo">{C.LOGO_HTML}</div>'
        f'<p class="tagline">{C.KHAU_HIEU}</p>'
        f'{phu}{chip}</div>{hinh}</div>',
        unsafe_allow_html=True
    )


def tieu_de(chu, phu="", nhan=""):
    """Tiêu đề trang: canh giữa, chữ có chân, nằm trên một khung trắng mờ."""
    st.markdown(
        '<div class="page-heading">'
        + (f'<span class="nhan-vien">{nhan}</span>' if nhan else "")
        + f'<div class="page-title">{chu}</div>'
        + (f'<div class="page-sub">{phu}</div>' if phu else "")
        + '</div>',
        unsafe_allow_html=True
    )


def muc_tieu_de(chu, phu=""):
    """Tiêu đề một khu vực trong trang."""
    st.markdown(
        f'<div class="muc-tieu-de"><b>{chu}</b>'
        + (f'<span>{phu}</span>' if phu else "")
        + '</div>',
        unsafe_allow_html=True
    )


def nhom_tieu_de(chu, phu=None):
    """Nhãn nhóm nhỏ (vd. ÁO · 12)."""
    st.markdown(
        f'<div class="nhom-tieu-de">{esc(str(chu))}'
        + (f'<span>{phu}</span>' if phu not in (None, "") else "")
        + '</div>',
        unsafe_allow_html=True
    )


def html(chuoi):
    """Hiện một đoạn HTML (gộp về một dòng để Markdown không hiểu nhầm phần thụt lề)."""
    st.markdown(
        " ".join(d.strip() for d in chuoi.splitlines() if d.strip()),
        unsafe_allow_html=True
    )


def anh_b64(b):
    """Ảnh (bytes) → data URI để nhúng vào HTML."""
    import base64

    if b[:8] == b"\x89PNG\r\n\x1a\n":
        loai = "png"
    elif b[8:12] == b"WEBP":
        loai = "webp"
    else:
        loai = "jpeg"

    return f"data:image/{loai};base64,{base64.b64encode(b).decode()}"


@st.cache_data(show_spinner=False)
def _doc_anh_b64(duong_dan, lan_sua, rong):
    import io
    from PIL import Image

    im = Image.open(duong_dan).convert("RGB")
    im.thumbnail((rong, rong * 2))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=88)
    return anh_b64(out.getvalue())


def anh_tep_b64(duong_dan, rong=560):
    """Ảnh trong thư mục dự án → data URI đã thu nhỏ (None nếu không có tệp).

    Nhận cả tên bị trình duyệt đổi khi tải về (vd. "mau_mac_thu (1).jpg")
    và đuôi .png/.jpeg. Chỉ nhớ kết quả khi tệp có thật, kèm thời điểm sửa
    tệp, nên thay ảnh lúc app đang chạy vẫn hiện ảnh mới.
    """
    p = Path(duong_dan)
    ung_vien = [p] + sorted(
        x for x in p.parent.glob(p.stem + "*")
        if x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and x != p
    )

    for x in ung_vien:
        if x.is_file():
            try:
                return _doc_anh_b64(str(x), x.stat().st_mtime, rong)
            except Exception:
                continue

    return None


def o_anh(b, tag="", lop=""):
    """Ô ảnh vuông nền nhạt, có nhãn nhỏ ở góc trên."""
    return (
        f'<div class="o-anh {lop}">'
        + (f'<span class="o-anh-tag">{esc(tag)}</span>' if tag else "")
        + f'<img src="{anh_b64(b)}" alt=""></div>'
    )


def dai_mau(ds_bytes):
    """Dải màu chủ đạo của các món (chỉ để hiển thị)."""
    import colorsys

    o = []

    for b in ds_bytes:
        try:
            h, s_, v = AI.mau_chu_dao(b)
            r, g, x = colorsys.hsv_to_rgb(h / 360, s_, v)
            o.append(
                f'<span style="background:rgb({r * 255:.0f},'
                f'{g * 255:.0f},{x * 255:.0f})"></span>'
            )
        except Exception:
            pass

    return f'<div class="dai-mau">{"".join(o)}</div>' if o else ""


def nhan_muc(chu, tieu, phu=""):
    """Tiêu đề khu vực kiểu mẫu: nhãn nhỏ dạng viên thuốc, tiêu đề chữ có chân, mô tả."""
    html(
        f'<div class="muc-giua">'
        f'<span class="nhan-vien">{chu}</span>'
        f'<div class="muc-giua-tieu">{tieu}</div>'
        + (f'<div class="muc-giua-phu">{phu}</div>' if phu else "")
        + '</div>'
    )


NHAN_NGAN = {
    "Áo": "Áo",
    "Quần/Chân váy": "Quần / váy",
    "Đồ liền thân": "Váy liền",
    "Giày": "Giày",
    "Túi xách": "Túi",
    "Phụ kiện": "Phụ kiện",
}


# ================= ẢNH MẪU NHÚNG SẴN CHO BANNER TRANG CHỦ
# Chỉ dùng khi không tìm thấy tệp ANH_MAC_THU_MAU / ANH_TRUOC_MAU khai báo trong cai_dat.py.
# Muốn đổi ảnh: sửa hai dòng đó trong cai_dat.py (tệp luôn được ưu tiên).
ANH_MAC_THU_NHUNG = "data:image/jpeg;base64,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EIQhBdehNE0QhCE4gQmpNE0QhCEJohOGiZdU/ZmEHp2B/uEEkZDYFwwmsJ8YAQhCcAmiEITWEIQhCaj0IQhBohOGlEMgYFkEDI0Z+YT0dccJoglpCEITSazWfBCEIQnxQhCD4Aegw1rczQsRojGldyG7IzbRINGXWakIQSIQhCE0hCEIQhCEITU0QS0QnygAQmiEINaWWroPCGkGAsFH/ZYSZtNytaYJftsILcQ13hDWbik7K5MnRRWsWohCEIQhCfCAITgEIThhNJpCcMIQmpCCNLKQo2N9thb+6GdzKIhKXYvQt5sbIQ1wyIT0PuJ5sazr0ML5Muu2UNMBri2YlSJMWlNIQhCEIQhCEIQhCEIQnwz44QnFCEIQhCEGsDarex1zX3gRz1CFMUeUP/1gSW2kt9YQuGcjOF8E4YTWEIQhCE0aIQhOKE5CEIQhCcEIQnIrgX4NfCuJ8SHw/wD/2gAMAwEAAgADAAAAEPtnlkjjgqskjtnklu+m2gsrilkjkhnomptkginsikqjovvtllgpn/4Hikhkgluluqjsmikiipphsikuqpgsuvtjtq4DgjshsgnkvvumkvkjmoishpomhupsillEJycmkpromhqvqpirjspmvkrgmksilonukIqPx1rrughhljkuvmmvvgusjtgnhhlltpqkaWfzjpmsmlosvlqlppmjvjkkvjphgkpvgolrNbMjlvmjqqrtquhrkmvjstrspnnnnptqrrp8Y88pognviggoitqkorjLPFDjgIBEIENPbi0jfTysGDGAFGAAACBjggthijighghggxy2EFXfqQsYgAghgggglrggggsopggmholthnUGKGmlvfAglgogggktnghggnpgqgggilp5oPwPKNF7mzjiglgjopgqggoggoogkggil92O43Pej5lfwwkssogggjtgirjgggjmjqgg3309jdNZ46/xwksggqgggvjsqsggkihgxggsOrFeDF0Z5N4wgggggggxojtosgkpggggggrzIAQibOLRygggggkiggtsplhhhjggjoggggQ3KugjNHpFAgggggqggnogotqgpggpgiggp1HiyTi/YjpwhgAAgglokgggvvgkiiiggggqv93fhoqYc6QlggglghihsggksihlggmwghOCOfxPjpHeow0CABjoimtiggoiggkoogggkg9O58po4vkfxQgClggmghqisgvggggugghqKRuZC78y7wI5glolghl67mrkigggkgggglnyRwKf0ylzixaiEghgggpugghpgoglgmtst1AfzJXu6+17QKTdDogggglgsnohigggghjiMAIvJWlxkxtReRzCgholuokkhgqjgkhigiik81SeL+6t8+gUogoggihmohglgkogqigosgggluKd92ukepAggoklrholgmqgghhigtggjgghtobD7gkyiAijqlgrsggopkgghmkqoggosgkppWd37EFqAlgkggqpglkusuqpigkspkovig26E023QVUAokqglkkvmgoitorqjmsghigqlt410zaBVYStkolhphhqwgikilqjpjj0qhqnAWtD502BZIklihkokgqggjgpnohggknghoumwYEDIdTUhghggsogutjjsholqgoglo4lgi83QyVuVtUQigogggggisoksklpggggoikglSbJzBnRIByViiggiogvoogjvgighrggxgktRef/ADMhEeEMIY4pZKoIJYJIIJKIIIYMI4PxNWOpG9wlCAgIIIIIoYIoILbIrKoIKpYIIaMnucZ144qK8oIKpaJJZIIIIIII4aIa4pYJZfrF9Z9iwglWBoIK5IJpIII5YIILIYIILKIssnSa66s13OfSoaqJKIKorI5IrrKKIJIJLK/4NT1ZPuNlx0aJr4a7Iorrr5IqoIpY6oYIJYqNJYvhsrPcKYLKJb6a6rILYJQ4J4oo5Lb767YoZS3UcqIJYqrYKBLr7AoJijZpjwbro67bpb5hoLRIYzzgCY45bTLY6Y74YQwQ55o7q4+f9a14I3MxPCQh7DDjCoDTSrCIoTaL5bqA6rv6dkOk+zE9bzDJDbyIgBICYID7LjLJIaDAIAANEINIAMIIDSLKbKoDLrYL/8QAIREAAwACAwADAQEBAAAAAAAAAAERITEQQEEgMFFQYXH/2gAIAQMBAT8Q6DRH8IQQkGjH8BBo0omF976CgwvCGUL31whoTNuCVbMDe/gGLCDDaWRazvkyA2Y/ci7Lj+BsMiC0g+9GPbuglFEIzIZaGy2u2lXBJRNCwPgQpMpRBI+1DyyAb4WUJixKDYTK7NLQlcPwyOJx6KUDb7BcV9ZAZj9P+iKVEYQXOBYCRzrqm43D91HjCP2MPJD8CUwErFPKZJrsOhUa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"
ANH_TRUOC_NHUNG = "data:image/jpeg;base64,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"


# ================= HÌNH MINH HỌA (SVG tự vẽ, không dùng ảnh ngoài)
HINH_HERO = """
<svg class="hinh-hero" viewBox="0 0 440 300" xmlns="http://www.w3.org/2000/svg"
     font-family="Be Vietnam Pro, sans-serif">
  <defs>
    <filter id="bong" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#7a4a5c" flood-opacity=".14"/>
    </filter>
  </defs>
  <circle cx="150" cy="118" r="86" fill="#f6cfdc" opacity=".55"/>
  <ellipse cx="180" cy="270" rx="140" ry="10" fill="#e9d6dc" opacity=".6"/>
  <g stroke="#8d7b86" stroke-width="5" stroke-linecap="round" fill="none">
    <line x1="58" y1="58" x2="302" y2="58"/>
    <line x1="74" y1="58" x2="60" y2="258"/>
    <line x1="286" y1="58" x2="300" y2="258"/>
    <line x1="60" y1="258" x2="300" y2="258" stroke-width="4"/>
  </g>
  <circle cx="60" cy="262" r="5" fill="#8d7b86"/>
  <circle cx="300" cy="262" r="5" fill="#8d7b86"/>
  <g stroke="#8d7b86" stroke-width="2" fill="none" stroke-linecap="round">
    <path d="M118 58 v8 M96 80 L118 66 L140 80"/>
    <path d="M195 58 v8 M172 80 L195 66 L218 80"/>
    <path d="M262 58 v8 M244 80 L262 68 L280 80"/>
  </g>
  <path d="M106 80 L130 80 L133 102 L127 106 L150 182 L86 182 L109 106 L103 102 Z"
        fill="#eaa3ba" stroke="#c5587b" stroke-width="1.5" stroke-dasharray="4 3"/>
  <path d="M108 106 L128 106" stroke="#c5587b" stroke-width="1.5"/>
  <path d="M170 82 L184 76 Q195 84 206 76 L220 82 L234 100 L221 107 L216 100 L216 152 L174 152
           L174 100 L169 107 L156 100 Z" fill="#a9c3ec" stroke="#7c9bd0" stroke-width="1.5"/>
  <path d="M244 80 L280 80 L285 176 L268 176 L262 116 L256 176 L239 176 Z"
        fill="#f2d77a" stroke="#d8b54a" stroke-width="1.5"/>
  <path d="M292 44 C 308 26, 326 30, 336 50" stroke="#c5587b" stroke-width="1.6"
        fill="none" stroke-dasharray="3 4"/>
  <path d="M331 46 L337 52 L339 43" stroke="#c5587b" stroke-width="1.6" fill="none"/>
  <g filter="url(#bong)">
    <rect x="318" y="60" width="114" height="156" rx="14" fill="#fff"/>
  </g>
  <text x="330" y="83" font-size="10" font-weight="700" fill="#2d2329">Bộ của bạn</text>
  <rect x="383" y="72" width="40" height="15" rx="7.5" fill="#f8e3ea"/>
  <text x="403" y="82.5" font-size="7.5" font-weight="700" fill="#c5587b" text-anchor="middle">Hợp 96%</text>
  <path d="M331 100 L340 96 Q347 101 354 96 L363 100 L370 110 L363 114 L360 110 L360 136
           L334 136 L334 110 L331 114 L324 110 Z" fill="#a9c3ec"/>
  <path d="M384 96 L414 96 L418 146 L405 146 L399 114 L393 146 L380 146 Z" fill="#f2d77a"/>
  <path d="M328 166 Q334 154 344 158 L356 166 Q366 168 366 174 L328 174 Z" fill="#eaa3ba"/>
  <rect x="386" y="160" width="30" height="22" rx="5" fill="#a9c3ec"/>
  <path d="M393 160 Q401 148 409 160" stroke="#7c9bd0" stroke-width="2" fill="none"/>
  <circle cx="334" cy="198" r="5" fill="#eaa3ba"/>
  <circle cx="346" cy="198" r="5" fill="#a9c3ec"/>
  <circle cx="358" cy="198" r="5" fill="#f2d77a"/>
  <text x="368" y="201" font-size="7" fill="#8a7d84">Màu cân bằng</text>
</svg>
"""

HINH_VONG = """
<svg class="hinh-vong" viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg">
  <g transform="rotate(-90 110 110)" fill="none" stroke-width="38">
    <circle cx="110" cy="110" r="72" stroke="#d97f9c" stroke-dasharray="145.8 306.6"/>
    <circle cx="110" cy="110" r="72" stroke="#b6cbef" stroke-dasharray="145.8 306.6"
            stroke-dashoffset="-150.8"/>
    <circle cx="110" cy="110" r="72" stroke="#f0dc8a" stroke-dasharray="145.8 306.6"
            stroke-dashoffset="-301.6"/>
  </g>
  <g font-family="Playfair Display, Georgia, serif" font-weight="700" font-size="17"
     fill="#2d2329" text-anchor="middle">
    <text x="172" y="78">1</text>
    <text x="110" y="184">2</text>
    <text x="48" y="78">3</text>
  </g>
  <g font-family="Be Vietnam Pro, sans-serif" font-size="7" fill="#5b4d55" text-anchor="middle">
    <text x="172" y="89">Nhận diện</text>
    <text x="110" y="195">Hài hòa màu</text>
    <text x="48" y="89">Hoàn thiện</text>
  </g>
  <text x="110" y="110" font-family="Playfair Display, Georgia, serif" font-size="19"
        font-weight="700" fill="#2d2329" text-anchor="middle">Lagom</text>
  <text x="110" y="126" font-family="Playfair Display, Georgia, serif" font-size="10"
        font-style="italic" fill="#8a7d84" text-anchor="middle">Studio</text>
</svg>
"""


# ================= NHẬT KÝ SỬ DỤNG (cho trang Thống kê)
# Mỗi dòng một sự kiện JSON trong ket_qua/nhat_ky.jsonl. Không lưu ảnh hay tên
# tài khoản, chỉ lưu mã băm tài khoản để đếm số người dùng.
NHAT_KY = BASE / "ket_qua" / "nhat_ky.jsonl"


def ghi_nhat_ky(loai, **du_lieu):
    import json, datetime

    try:
        NHAT_KY.parent.mkdir(parents=True, exist_ok=True)
        dong = {
            "luc": datetime.datetime.now().isoformat(timespec="seconds"),
            "nd": hashlib.md5(str(st.session_state.get("user", "")).encode()).hexdigest()[:8],
            "loai": loai,
            **du_lieu,
        }
        with open(NHAT_KY, "a", encoding="utf-8") as f:
            f.write(json.dumps(dong, ensure_ascii=False) + "\n")
    except Exception:
        pass  # nhật ký hỏng không được làm hỏng app


def doc_nhat_ky():
    import json

    if not NHAT_KY.exists():
        return []

    ds = []
    with open(NHAT_KY, encoding="utf-8") as f:
        for dong in f:
            try:
                ds.append(json.loads(dong))
            except ValueError:
                continue
    return ds


def _cat_cache(d, toi_da):
    """Bỏ các mục cũ nhất để cache trong phiên không phình mãi."""
    while len(d) > toi_da:
        d.pop(next(iter(d)))


def xu_ly_anh(f):
    """Thu nhỏ, tách nền, tính vector cho ảnh tải lên.

    Kết quả được nhớ trong phiên, nên mỗi lần bấm nút bất kỳ
    (Streamlit chạy lại cả trang) không phải tách nền lại từ đầu.
    Trả về (bytes ảnh, vector, lỗi tách nền hoặc None).
    """
    raw = f.getvalue()
    k = (hashlib.md5(raw).hexdigest(), TACH_NEN)
    cache = st.session_state.setdefault("_anh_cache", {})

    if k not in cache:
        b, loi = AI.thu_nho(raw), None

        if TACH_NEN:
            try:
                b = AI.tach_nen(b)
            except Exception as e:
                loi = str(e)

        cache[k] = (b, AI.vector(b), loi)
        _cat_cache(cache, SO_ANH_CACHE)

    return cache[k]


def khoa_thu(anh_mau, *ds_mon):
    """Khóa nhận diện một lần mặc thử: người mẫu + các món được mặc."""
    h = hashlib.md5(str(anh_mau).encode())

    for m in ds_mon:
        if m is None:
            continue
        b = m.get("bytes")
        h.update(
            bytes(b) if isinstance(b, (bytes, bytearray))
            else str(m.get("id")).encode()
        )

    return h.hexdigest()


# ================= ĐĂNG NHẬP GOOGLE
try:
    CO_GOOGLE = "auth" in st.secrets
except Exception:
    CO_GOOGLE = False

def _da_dang_nhap_google():
    """True nếu đã đăng nhập Google; mọi lỗi cấu hình đều coi như chưa đăng nhập."""
    try:
        return bool(getattr(st.user, "is_logged_in", False)) and bool(st.user.email)
    except Exception:
        return False


if CO_GOOGLE and "user" not in st.session_state and _da_dang_nhap_google():
    email = st.user.email.lower()

    try:
        ten_hien_thi = st.user.name or email
    except Exception:
        ten_hien_thi = email

    st.session_state.update(
        user="g_" + re.sub(r"[^a-z0-9]", "_", email),
        ten_hien_thi=ten_hien_thi,
        google=True
    )


# ================= KHÔI PHỤC ĐĂNG NHẬP BẰNG COOKIE
if "user" not in st.session_state:
    try:
        ten_cookie = cookies.get("user")
    except Exception:
        ten_cookie = None

    if ten_cookie and TK.tai_khoan_ton_tai(ten_cookie):
        st.session_state.update(
            user=ten_cookie,
            ten_hien_thi=ten_cookie
        )


# ================= TRANG ĐĂNG NHẬP
if "user" not in st.session_state:
    _, giua, _ = st.columns([1, 1.2, 1])

    with giua:
        st.write("")
        hero(C.MO_TA_TRANG_CHU, giua=True)

        with st.container(border=True, key="khung_dang_nhap"):
            if CO_GOOGLE:
                st.button(
                    "Tiếp tục với Google",
                    icon=":material/login:",
                    on_click=st.login,
                    type="primary",
                    use_container_width=True
                )

                st.markdown(
                    "<div class='hoac'>hoặc</div>",
                    unsafe_allow_html=True
                )

            t1, t2 = st.tabs(["Đăng nhập", "Tạo tài khoản"])

            with t1, st.form("dn", border=False):
                ten = st.text_input(
                    "Tên đăng nhập",
                    autocomplete="username"
                )
                mk = st.text_input(
                    "Mật khẩu",
                    type="password",
                    autocomplete="current-password"
                )

                if st.form_submit_button(
                    "Đăng nhập",
                    type="primary",
                    use_container_width=True
                ):
                    if TK.dang_nhap(ten, mk):
                        ten = ten.strip().lower()
                        cookies["user"] = ten
                        cookies.save()

                        st.session_state.update(
                            user=ten,
                            ten_hien_thi=ten
                        )
                        st.rerun()
                    else:
                        st.error("Sai tên đăng nhập hoặc mật khẩu.")

            with t2, st.form("dk", border=False):
                ten = st.text_input(
                    "Tên đăng nhập",
                    help="3–20 ký tự: chữ thường không dấu, số, dấu gạch dưới",
                    autocomplete="username"
                )
                mk = st.text_input(
                    "Mật khẩu",
                    type="password",
                    autocomplete="new-password"
                )
                mk2 = st.text_input(
                    "Nhập lại mật khẩu",
                    type="password",
                    autocomplete="new-password"
                )

                if st.form_submit_button(
                    "Tạo tài khoản",
                    type="primary",
                    use_container_width=True
                ):
                    loi = TK.dang_ky(ten, mk, mk2)

                    if loi:
                        st.error(loi)
                    else:
                        st.success(
                            "Tạo tài khoản thành công. Mời bạn đăng nhập."
                        )

    st.stop()


U = st.session_state.user
st.session_state.setdefault("trang", "home")


def di(trang):
    st.session_state.trang = trang


def phan_trang(khoa, so_trang, vi_tri="tren"):
    """Thanh chuyển trang."""
    tr = min(
        max(st.session_state.get(khoa, 1), 1),
        so_trang
    )
    st.session_state[khoa] = tr

    def dat(gia_tri):
        st.session_state[khoa] = min(
            max(gia_tri, 1),
            so_trang
        )

    a, b, c, d, e = st.columns([1, 1.4, 2, 1.4, 1])

    a.button(
        "«",
        key=f"{khoa}_{vi_tri}_dau",
        on_click=dat,
        args=(1,),
        disabled=tr == 1,
        use_container_width=True
    )

    b.button(
        "‹ Trước",
        key=f"{khoa}_{vi_tri}_lui",
        on_click=dat,
        args=(tr - 1,),
        disabled=tr == 1,
        use_container_width=True
    )

    c.markdown(
        f"<div class='trang-so'>Trang <b>{tr}</b> / {so_trang}</div>",
        unsafe_allow_html=True
    )

    d.button(
        "Sau ›",
        key=f"{khoa}_{vi_tri}_toi",
        on_click=dat,
        args=(tr + 1,),
        disabled=tr == so_trang,
        use_container_width=True
    )

    e.button(
        "»",
        key=f"{khoa}_{vi_tri}_cuoi",
        on_click=dat,
        args=(so_trang,),
        disabled=tr == so_trang,
        use_container_width=True
    )

    return tr


# ================= TÙY CHỌN PHỐI ĐỒ
# Giá trị lưu ở khóa "tc_<tên>" (không phải khóa của ô chọn), nên ô chọn có thể
# hiện ở trang này hay trang khác, hoặc không hiện, mà lựa chọn vẫn được giữ.
NGUON_DS = ["Chỉ tủ đồ", "Tủ đồ + cửa hàng"]

DS_MAU = sorted(
    p.stem for p in (BASE / "nguoi_mau").glob("*.jpg")
    if not any(x in p.stem for x in ("_vay", "_short", "_lung"))
)

_mau_mac_dinh = getattr(C, "NGUOI_MAU_MAC_DINH", "")

for _k, _v in {
    "nguon": NGUON_DS[1],
    "dip": None,
    "pc": None,
    "so_bo": int(C.SO_BO_MAC_DINH),
    "tach_nen": True,
    "mau": _mau_mac_dinh if _mau_mac_dinh in DS_MAU else (DS_MAU[0] if DS_MAU else None),
    "xem": "chon",
    "ch_nhom": list(C.NHOM)[0],
}.items():
    st.session_state.setdefault(f"tc_{_k}", _v)

if DS_MAU and st.session_state.tc_mau not in DS_MAU:
    st.session_state.tc_mau = DS_MAU[0]


def _luu_tc(k, bat_buoc=False):
    v = st.session_state.get(f"w_{k}")

    # Ô bắt buộc (vd. nguồn món) bị bấm bỏ chọn: giữ giá trị cũ
    if v is None and bat_buoc:
        return

    st.session_state[f"tc_{k}"] = v


def o_tc(ham, k, nhan, bat_buoc=False, mac_dinh=None, **kw):
    """Vẽ một ô tùy chọn; giá trị đọc từ và lưu vào st.session_state['tc_<k>']."""
    st.session_state.setdefault(f"tc_{k}", mac_dinh)
    st.session_state[f"w_{k}"] = st.session_state[f"tc_{k}"]
    return ham(nhan, key=f"w_{k}", on_change=_luu_tc, args=(k, bat_buoc), **kw)


def bang_tuy_chon(muc=("nguon", "dip", "pc", "so_bo", "mau", "tach_nen")):
    """Bảng tùy chọn phối đồ (cột trái ở trang Phối đồ và Chấm bộ)."""
    with st.container(border=True, key="khung_tuy_chon"):
        html("<div class='panel-tieu-de'>Tùy chọn phối đồ</div>")

        if "nguon" in muc:
            o_tc(
                st.segmented_control, "nguon", "Nguồn món đồ",
                bat_buoc=True, options=NGUON_DS
            )

        if "dip" in muc:
            o_tc(
                st.pills, "dip", C.NHAN_DIP, options=list(C.DIP),
                help="Bấm lại vào dịp đang chọn để bỏ chọn."
            )

        if "pc" in muc and getattr(C, "PHONG_CACH", None):
            o_tc(
                st.pills, "pc", "Phong cách", options=list(C.PHONG_CACH),
                help="Không chọn: Lagom Studio tự đoán theo món của bạn."
            )

        if "so_bo" in muc:
            o_tc(
                st.slider, "so_bo", "Số outfit gợi ý",
                min_value=1, max_value=5, step=1
            )

        if "mau" in muc and DS_MAU:
            o_tc(
                st.selectbox, "mau", "Người mẫu thử đồ", options=DS_MAU,
                format_func=lambda x: C.TEN_NGUOI_MAU.get(x, x)
            )
            st.image(
                str(BASE / "nguoi_mau" / f"{st.session_state.tc_mau}.jpg"),
                width=90
            )

        if "tach_nen" in muc:
            o_tc(st.toggle, "tach_nen", "Tự tách nền ảnh tải lên")


ket_hop = st.session_state.tc_nguon != NGUON_DS[0]
toi_da_kho = C.SO_MON_KHO_TOI_DA if ket_hop else 0

dip = st.session_state.tc_dip
j_dip = list(C.DIP).index(dip) if dip in C.DIP else None

pc = st.session_state.tc_pc
j_pc = (
    list(C.PHONG_CACH).index(pc)
    if pc in getattr(C, "PHONG_CACH", {}) else None
)

so_bo = int(st.session_state.tc_so_bo)
TACH_NEN = bool(st.session_state.tc_tach_nen)

anh_mau = (
    BASE / "nguoi_mau" / f"{st.session_state.tc_mau}.jpg"
    if st.session_state.tc_mau else None
)


# ================= THANH ĐIỀU HƯỚNG TRÊN CÙNG
def _chon_menu():
    v = st.session_state.get("nav")

    # Bấm lại mục đang mở thì giữ nguyên trang
    if v:
        st.session_state.trang = v


# Cửa hàng và Bộ đồ đã lưu nằm trong mục "Tủ đồ" của menu
NHOM_MENU = {"cua_hang": "tu_do", "da_luu": "tu_do"}
st.session_state["nav"] = NHOM_MENU.get(st.session_state.trang, st.session_state.trang)
if st.session_state["nav"] not in C.MENU:
    st.session_state["nav"] = list(C.MENU)[0]
ten_nd = str(st.session_state.get("ten_hien_thi", U))

with st.container(key="topbar"):
    c_logo, c_nav, c_nut = st.columns(
        [1.55, 4.75, 1.6], vertical_alignment="center"
    )

    with c_logo:
        html(
            f'<div class="brand">'
            f'<span class="brand-mark">{C.TEN_APP[:1]}</span>'
            f'<div><div class="brand-ten">{C.LOGO_HTML}</div>'
            f'<div class="brand-phu">{C.KHAU_HIEU}</div></div></div>'
        )

    with c_nav:
        st.segmented_control(
            "Điều hướng",
            options=list(C.MENU),
            format_func=lambda k: C.MENU[k],
            key="nav",
            on_change=_chon_menu,
            label_visibility="collapsed"
        )

    with c_nut:
        a, b = st.columns([2.1, 1], vertical_alignment="center")

        a.button(
            "Món mới",
            icon=":material/add:",
            type="primary",
            key="nut_mon_moi",
            on_click=di,
            args=("tu_do",),
            use_container_width=True,
            help="Tải ảnh món mới vào tủ đồ"
        )

        with b.popover(
            ":material/person:",
            help=f"Tài khoản: {ten_nd}",
            use_container_width=True
        ):
            html(f"<div class='sb-chao'>Xin chào<b>{esc(ten_nd)}</b></div>")

            if st.button(
                "Đăng xuất",
                icon=":material/logout:",
                use_container_width=True
            ):
                la_google = st.session_state.get("google")

                if "user" in cookies:
                    del cookies["user"]
                    cookies.save()

                st.session_state.clear()

                if la_google:
                    st.logout()
                else:
                    st.rerun()


# ================= THANH CHỌN CON CỦA MỤC "TỦ ĐỒ"
TRANG_TU_DO = {
    "tu_do": "Tủ đồ của tôi",
    "cua_hang": "Cửa hàng",
    "da_luu": "Bộ đồ đã lưu",
}


def _chon_trang_tu_do():
    v = st.session_state.get("w_trang_tu_do")
    if v:
        st.session_state.trang = v


def thanh_tu_do():
    """Ba trang con của mục Tủ đồ: tủ đồ, cửa hàng, bộ đã lưu."""
    st.session_state["w_trang_tu_do"] = st.session_state.trang
    _, g, _ = st.columns([1, 1.3, 1])
    with g:
        st.segmented_control(
            "Trang trong mục Tủ đồ",
            options=list(TRANG_TU_DO),
            format_func=TRANG_TU_DO.get,
            key="w_trang_tu_do",
            on_change=_chon_trang_tu_do,
            label_visibility="collapsed"
        )


# ================= CHỌN LOẠI MÓN VÀ KIỂU DÁNG
def chon_loai_kieu(v, key):
    """Ô Loại món và Kiểu dáng."""
    goi_y = AI.doan_nhom(v)

    nh = st.selectbox(
        "Loại món (AI tự đoán)",
        list(C.NHOM),
        index=list(C.NHOM).index(goi_y),
        key=f"{key}_n",
    )

    kd_ds = getattr(C, "KIEU_DANG", {}).get(nh, {})
    kd = None

    if kd_ds:
        ma_ds = list(kd_ds)
        kd_ai = AI.kieu_dang(dict(v=v, nhom=nh))

        kd = st.selectbox(
            "Kiểu dáng (AI tự đoán)",
            ma_ds,
            index=ma_ds.index(kd_ai) if kd_ai in ma_ds else 0,
            key=f"{key}_kd_{nh}",
            format_func=lambda x, d=kd_ds: d[x][0]
        )

    return nh, kd


# ================= THẺ TẢI ẢNH
def the_tai_anh(ten):
    ver = st.session_state.setdefault(f"{ten}_ver", 0)
    so = st.session_state.setdefault(f"{ten}_so", C.SO_THE_BAN_DAU)

    p, ds, cols = f"{ten}{ver}", [], st.columns(C.SO_COT_THE)

    for i in range(so):
        with cols[i % C.SO_COT_THE], st.container(border=True, key=f"the_up_{p}_{i}"):
            f = st.file_uploader(
                f"Món {i + 1}",
                type=["jpg", "jpeg", "png", "webp"],
                key=f"{p}_f{i}"
            )

            if f is None:
                st.caption(
                    "Chụp trên nền trơn, đủ sáng. "
                    "Tải ảnh lên để chọn loại món và kiểu dáng."
                )
                continue

            b, v, loi = xu_ly_anh(f)

            if loi:
                st.caption(
                    f"Không tách nền được, dùng ảnh gốc. ({loi})"
                )

            st.image(b, width=C.CO_ANH_THE)

            nh, kd = chon_loai_kieu(
                v,
                f"{p}_{i}_{len(b)}"
            )

            ten_mon = st.text_input(
                "Tên món (tùy chọn)",
                key=f"{p}_t{i}",
                placeholder=f"{nh} {i + 1}"
            )

            ds.append(
                dict(
                    bytes=b,
                    v=v,
                    nhom=nh,
                    ten=ten_mon or f"{nh} {i + 1}",
                    kieu_dang=kd
                )
            )

    if st.button("Thêm ô tải ảnh", icon=":material/add:", key=f"{p}_them"):
        st.session_state[f"{ten}_so"] += 1
        st.rerun()

    return ds


def lam_moi_the(ten):
    st.session_state[f"{ten}_ver"] += 1
    st.session_state[f"{ten}_so"] = C.SO_THE_BAN_DAU
# ================= ĐỔI / ẨN / QUAY LẠI MỘT MÓN TRONG OUTFIT
def doi_mon(n, i, an, j_dip_, j_pc_):
    """Thay món trong outfit; lưu trạng thái trước đó để người dùng có thể quay lại."""
    (chon, pool), bb_cu = st.session_state.kq_phoi
    idx, diem_cu = chon[n]
    m = pool[i]

    # Lưu lịch sử riêng cho outfit đang thao tác.
    lich_su = st.session_state.setdefault("lich_su_doi", {})
    lich_su.setdefault(n, []).append({
        "idx": list(idx),
        "diem": diem_cu,
        "an_id": m.get("id") if an and m.get("nguon") == "kho" else None,
    })

    if an and m.get("nguon") == "kho":
        AI.an_mon_kho(m["id"])

    loai_tru = st.session_state.setdefault("da_doi", set())
    loai_tru.add(m.get("id"))

    dang_dung = {pool[x].get("id") for c, _ in chon for x in c}
    moi = AI.thay_mon(pool, idx, i, j_dip_, j_pc_, loai_tru | dang_dung)

    if moi is not None:
        pool.append(dict(moi, nguon="kho"))
        idx2 = [len(pool) - 1 if x == i else x for x in idx]
    else:
        idx2 = [x for x in idx if x != i]

    chon[n] = (idx2, AI.diem_bo_mon([pool[x] for x in idx2]))
    st.session_state.kq_phoi = ((chon, pool), bb_cu)


def quay_lai_mon(n):
    """Khôi phục lần thay đổi gần nhất của riêng outfit n."""
    lich_su = st.session_state.get("lich_su_doi", {})

    if not lich_su.get(n):
        return

    (chon, pool), bb_cu = st.session_state.kq_phoi
    truoc = lich_su[n].pop()

    chon[n] = (truoc["idx"], truoc["diem"])

    if truoc.get("an_id"):
        AI.bo_an_mon_kho(truoc["an_id"])

    st.session_state.kq_phoi = ((chon, pool), bb_cu)


# ================= THẺ BỘ ĐỒ DỰNG SẴN (Bộ sưu tập, trang chủ)
O_THEO_NHOM = {
    "Áo": "ao",
    "Quần/Chân váy": "duoi",
    "Đồ liền thân": "duoi",
    "Giày": "giay",
    "Túi xách": "tui",
    "Phụ kiện": "pk",
}


def _phoi_voi_mon_chinh(mon_bo):
    """Đưa món chính của bộ (áo / váy liền) vào danh sách món cửa hàng rồi sang trang Phối đồ."""
    chinh = next(
        (m for m in mon_bo if m["nhom"] in ("Áo", "Đồ liền thân") and "k" in m),
        next((m for m in mon_bo if "k" in m), None)
    )
    if chinh is not None:
        ds = st.session_state.setdefault("kho_chon", [])
        if chinh["k"] not in ds:
            ds.append(chinh["k"])
    st.session_state.tc_xem = "chon"
    di("phoi")


def _danh_gia_bo(mon_bo):
    """Đặt các món của bộ lên bàn phối ở trang Chấm bộ."""
    ban = {}
    for m in mon_bo:
        o = O_THEO_NHOM.get(m["nhom"])
        if o == "ao" and "ao" in ban:
            o = "khoac"
        if o and o not in ban:
            ban[o] = dict(m)
    st.session_state.ban_phoi = ban
    di("cham")


def _luu_bo_san(mon_bo):
    TK.luu_bo(U, [dict(m) for m in mon_bo])
    ghi_nhat_ky("luu_bo", nguon="bo_suu_tap")
    st.toast("Đã lưu vào Bộ đồ đã lưu")


def the_bo_san(bo, tieu, khoa, nut=True):
    """Thẻ một bộ đồ dựng sẵn: dãy ảnh món, dải màu, tên màu, các nút."""
    mon_bo = bo["mon"]

    with st.container(border=True, key=f"khung_bst_{khoa}"):
        ten_mau_bo = []
        for m in mon_bo:
            try:
                t = AI.ten_mau(m["bytes"])
            except Exception:
                t = None
            if t and t not in ten_mau_bo:
                ten_mau_bo.append(t)

        html(
            f'<div class="bo-dau"><span class="bo-ten">{esc(tieu)}</span>'
            f'<span class="badge">Điểm phối {bo["diem"] * 100:.0f}%</span></div>'
            '<div class="day-anh">'
            + "".join(
                '<div class="day-anh-o">'
                + o_anh(m["bytes"])
                + f'<div class="o-loai">{esc(NHAN_NGAN.get(m["nhom"], m["nhom"]))}</div>'
                + f'<div class="o-ten nho">{esc(m["ten"])}</div></div>'
                for m in mon_bo
            )
            + "</div>"
            + dai_mau([m["bytes"] for m in mon_bo])
            + (f'<div class="dai-mau-chu">{" · ".join(ten_mau_bo[:5])}</div>' if ten_mau_bo else "")
        )

        if nut:
            st.button(
                "Phối với món chính",
                icon=":material/auto_awesome:",
                type="primary",
                key=f"bst_phoi_{khoa}",
                on_click=_phoi_voi_mon_chinh,
                args=(mon_bo,),
                use_container_width=True
            )

            # Hai việc phụ: nút chữ nhỏ, không tranh chỗ với nút chính
            a, b, _ = st.columns([1, 1, 0.6])
            a.button(
                "Chấm điểm bộ",
                icon=":material/grading:",
                type="tertiary",
                key=f"bst_cham_{khoa}",
                on_click=_danh_gia_bo,
                args=(mon_bo,)
            )
            b.button(
                "Lưu bộ",
                icon=":material/favorite:",
                type="tertiary",
                key=f"bst_luu_{khoa}",
                on_click=_luu_bo_san,
                args=(mon_bo,)
            )


def lay_bo_suu_tap(j, so_bo=5):
    """Bộ sưu tập của phong cách thứ j (đã nhớ sẵn sau lần dựng đầu)."""
    try:
        return AI.bo_suu_tap(j, so_bo)
    except Exception as e:
        st.warning(f"Chưa dựng được bộ sưu tập: {e}")
        return []


# ================= HIỂN THỊ MỘT OUTFIT
def hien_bo(
    tieu,
    mon,
    idx,
    hop,
    anh_thu=None,
    nut_thu=True,
    bb=frozenset(),
    vi_tri=None
):
    khung = "x" if vi_tri is None else vi_tri

    with st.container(border=True, key=f"khung_bo_{khung}"):
        so_kho = sum(mon[i].get("nguon") == "kho" for i in idx)

        phu = (
            f"{len(idx) - so_kho} món của bạn"
            + (
                f" + {so_kho} món gợi ý từ cửa hàng"
                if so_kho else ""
            )
        )

        html(
            f'<div class="bo-dau"><span class="bo-ten">{tieu}</span>'
            f'{badge(hop)}</div><div class="bo-phu">{phu}</div>'
        )

        if vi_tri is not None:
            so_lan = len(
                st.session_state.get("lich_su_doi", {}).get(vi_tri, [])
            )

            if so_lan:
                st.button(
                    f"Quay lại món trước ({so_lan})",
                    icon=":material/undo:",
                    key=f"quay_lai_{vi_tri}_{so_lan}",
                    on_click=quay_lai_mon,
                    args=(vi_tri,)
                )

        # ---- Lưới thẻ món
        SO_COT_MON = 5
        cot_mon = st.columns(SO_COT_MON)

        for n, i in enumerate(idx):
            m = mon[i]
            la_chon = i in bb

            kd = AI.ten_kieu_dang(AI.kieu_dang(m), m["nhom"])
            nguon = "Món bạn chọn" if la_chon else C.NGUON[m.get("nguon", "tu")]
            ma_hien = (
                f" · Mã {esc(str(m['id']))}"
                if str(m.get("id", "")).startswith("XH-") else ""
            )

            with cot_mon[n % SO_COT_MON]:
                # Tên món có thể do người dùng khác đặt (món chia sẻ lên cửa hàng),
                # nên phải escape trước khi đưa vào HTML.
                html(
                    o_anh(
                        m["bytes"],
                        "Món bạn chọn" if la_chon else NHAN_NGAN.get(m["nhom"], m["nhom"]),
                        "chon" if la_chon else ""
                    )
                    + f'<div class="o-ten">{esc(m["ten"])}</div>'
                    + f'<div class="o-phu">'
                    + (f"{esc(kd)} · " if kd else "")
                    + f"{nguon}{ma_hien}</div>"
                )

                if vi_tri is not None and not la_chon:
                    st.button(
                        "Đổi món",
                        icon=":material/swap_horiz:",
                        key=f"doi_{vi_tri}_{i}",
                        on_click=doi_mon,
                        args=(vi_tri, i, False, j_dip, j_pc),
                        use_container_width=True,
                        help="Món này không hợp outfit: đổi sang món khác cùng loại"
                    )

                    if m.get("nguon") == "kho":
                        st.button(
                            "Không gợi ý",
                            icon=":material/block:",
                            key=f"an_{vi_tri}_{i}",
                            on_click=doi_mon,
                            args=(vi_tri, i, True, j_dip, j_pc),
                            use_container_width=True,
                            help="Không thích món này: ẩn khỏi toàn bộ web và đổi món khác"
                        )

        html(
            dai_mau([mon[i]["bytes"] for i in idx])
            + '<div class="dai-mau-chu">Bảng màu của bộ đồ</div>'
        )

        a, b = st.columns(2)

        a.image(
            AI.anh_bo([
                (mon[i]["bytes"], mon[i]["nhom"])
                for i in idx
            ]),
            caption="Bảng phối đồ",
            width=C.CO_ANH_BO
        )

        chinh = sorted(
            [
                i for i in idx
                if mon[i]["nhom"] in ("Áo", "Đồ liền thân")
            ],
            key=lambda i: (
                mon[i]["nhom"] != "Đồ liền thân",
                AI.diem_ao_khoac(mon[i]["v"])
            )
        )

        duoi = [
            i for i in idx
            if mon[i]["nhom"] == "Quần/Chân váy"
        ]

        mac_duoi = bool(
            chinh
            and duoi
            and mon[chinh[0]]["nhom"] == "Áo"
            and AI.mac_duoi_duoc(mon[duoi[0]])
        )

        da_mac = set(chinh[:1]) | (
            set(duoi[:1]) if mac_duoi else set()
        )

        kem = [
            mon[i]["bytes"]
            for i in idx
            if i not in da_mac
        ]

        # Ảnh mặc thử được nhớ theo (người mẫu + món mặc), nên không mất
        # khi trang chạy lại sau một cú bấm khác.
        anh_cache = st.session_state.setdefault("anh_thu_cache", {})
        k_thu = (
            khoa_thu(
                anh_mau,
                mon[chinh[0]],
                mon[duoi[0]] if duoi else None
            )
            if chinh and anh_mau is not None else None
        )

        with b:
            if anh_thu:
                st.image(
                    AI.anh_lookbook(anh_thu, kem),
                    caption=CHU_THICH_LB,
                    width=C.CO_ANH_BO + 120
                )

            elif anh_mau is None:
                st.info(
                    "Thêm ảnh người mẫu vào thư mục nguoi_mau "
                    "để mặc thử."
                )

            elif not chinh:
                st.info(
                    "Bộ này chưa có áo hoặc váy liền để mặc thử."
                )

            else:
                da_thu = k_thu in anh_cache

                if nut_thu and st.button(
                    "Mặc thử lại" if da_thu
                    else "Mặc thử lên người mẫu",
                    icon=":material/refresh:" if da_thu
                    else ":material/checkroom:",
                    key=f"td_{tieu}",
                    use_container_width=True
                ):
                    with st.spinner("AI đang mặc thử (1–3 phút)…"):
                        try:
                            kq = AI.mac_thu(
                                anh_mau,
                                mon[chinh[0]],
                                mon[duoi[0]] if duoi else None
                            )

                            # Dịch vụ có thể trả None thay vì báo lỗi
                            if kq is None:
                                raise RuntimeError("dịch vụ không trả về ảnh")

                            # Ảnh dạng file (BytesIO...) → đổi ra bytes để
                            # dùng lại được nhiều lần
                            if hasattr(kq, "read"):
                                if hasattr(kq, "seek"):
                                    kq.seek(0)
                                kq = kq.read()

                            anh_cache[k_thu] = kq
                            _cat_cache(anh_cache, SO_ANH_THU_CACHE)

                        except Exception as e:
                            anh_cache.pop(k_thu, None)
                            st.error(
                                "Dịch vụ thử đồ đang bận hoặc tạm dừng, "
                                f"thử lại sau. ({e})"
                            )

                if anh_cache.get(k_thu) is not None:
                    try:
                        st.image(
                            AI.anh_lookbook(anh_cache[k_thu], kem),
                            caption=CHU_THICH_LB,
                            width=C.CO_ANH_BO + 120
                        )
                    except Exception as e:
                        anh_cache.pop(k_thu, None)
                        st.warning(
                            "Không hiển thị được ảnh mặc thử, "
                            f"bấm mặc thử lại. ({e})"
                        )

        if vi_tri is not None:
            k_ph = f"ph_{khoa_thu('', *[mon[i] for i in idx])}"
            da_ph = st.session_state.setdefault("da_phan_hoi", {})

            if k_ph in da_ph:
                st.caption(
                    "Cảm ơn bạn, đã ghi nhận: "
                    + ("**Hợp**" if da_ph[k_ph] else "**Chưa hợp**")
                )
            else:
                h1, h2, h3 = st.columns([1.4, 1, 1.2], vertical_alignment="center")
                h1.caption("Bộ này có hợp với bạn không?")
                for col, (nhan, gt) in zip((h2, h3), (("Hợp", True), ("Chưa hợp", False))):
                    if col.button(nhan, key=f"{k_ph}_{gt}_{vi_tri}", use_container_width=True):
                        da_ph[k_ph] = gt
                        ghi_nhat_ky(
                            "phan_hoi", hop=gt,
                            phong_cach=st.session_state.get("pc_hien_tai") or "Tự chọn",
                            diem=round(float(hop), 4)
                        )
                        st.rerun()

        if st.button(
            "Lưu bộ đồ này",
            icon=":material/favorite:",
            type="primary",
            key=f"luu_bo_{tieu}_{vi_tri}"
        ):
            TK.luu_bo(U, [mon[i] for i in idx])
            ghi_nhat_ky("luu_bo", nguon="phoi_do")
            st.toast(
                "Đã lưu bộ đồ. Lagom Studio sẽ học từ bộ này "
                "để gợi ý hợp gu bạn hơn."
            )



trang = st.session_state.trang


# ================= TRANG CHỦ
if trang == "home":
    tu = TK.doc_tu_do(U)

    anh_sau = (
        anh_tep_b64(str(BASE / getattr(C, "ANH_MAC_THU_MAU", "mau_mac_thu.jpg")))
        or ANH_MAC_THU_NHUNG
    )
    # Ảnh "Trước": ảnh riêng cho trang chủ nếu có, không thì dùng người mẫu đang chọn
    anh_truoc = anh_tep_b64(
        str(BASE / getattr(C, "ANH_TRUOC_MAU", "mau_truoc.jpg")), 300
    ) or (anh_tep_b64(str(anh_mau), 300) if anh_mau else None) or ANH_TRUOC_NHUNG

    # ---- Banner
    with st.container(key="hero"):
        trai, phai = st.columns([1.1, 1], vertical_alignment="center")

        with trai:
            html(
                f'''
                <span class="nhan-vien">Phối đồ thông minh</span>
                <div class="hero-brand">{C.LOGO_HTML}</div>
                <div class="hero-slogan">{getattr(C, "SLOGAN", "Mặc đẹp hơn, theo cách của bạn")}</div>
                <div class="hero-mo-ta">{C.MO_TA_TRANG_CHU}</div>
                '''
            )

            n1, n2, _ = st.columns([1.15, 1, 0.5])
            n1.button(
                "Bắt đầu phối đồ",
                type="primary",
                key="hero_phoi",
                on_click=di,
                args=("phoi",),
                use_container_width=True
            )
            n2.button(
                "Xem tủ đồ",
                key="hero_tu",
                on_click=di,
                args=("tu_do",),
                use_container_width=True
            )

        with phai:
            if anh_sau:
                html(
                    '<div class="hero-anh">'
                    '<div class="hero-vet hero-vet-1"></div><div class="hero-vet hero-vet-2"></div>'
                    f'<figure class="hero-anh-chinh"><img src="{anh_sau}" alt="Ảnh mặc thử">'
                    '<span class="hero-anh-nhan">Ảnh do AI tạo</span></figure>'
                    + (
                        f'<figure class="hero-anh-truoc"><img src="{anh_truoc}" alt="Người mẫu">'
                        '<figcaption>Trước</figcaption></figure>'
                        if anh_truoc else ""
                    )
                    + '<div class="hero-the">'
                    '<div class="hero-the-dau"><b>Mặc thử ảo</b><span>Hợp 96%</span></div>'
                    '<div class="hero-the-mau"><i style="background:#e7c4d6"></i>'
                    '<i style="background:#d3b8e6"></i><i style="background:#f4e7ee"></i>'
                    '<small>Bảng màu cân bằng</small></div></div>'
                    '<div class="hero-chip-noi">✦ Phối từ tủ đồ của bạn</div>'
                    '</div>'
                )
            else:
                html(HINH_HERO)

    # ---- Tính năng
    nhan_muc(
        "Tính năng",
        "Mọi thứ bạn cần để có bộ đồ ưng ý",
        "Bấm vào từng thẻ để bắt đầu"
    )

    MAU_THE = ["hong", "xanh", "vang", "hong"]

    for n, (col, t) in enumerate(zip(st.columns(len(C.TINH_NANG)), C.TINH_NANG)):
        k, so, *giua, tieu, mo_ta = t
        nho = giua[0] if giua else ""

        with col, st.container(border=True, key=f"feat_{MAU_THE[n % 4]}_{k}"):
            html(
                f'<div class="feat-so">{so}</div>'
                + (f'<span class="feat-nho">{nho}</span>' if nho else "")
                + f'<div class="feat-title">{tieu}</div>'
                f'<div class="feat-desc">{mo_ta}</div>'
            )

            st.button(
                "Khám phá",
                icon=":material/arrow_forward:",
                key=f"vao_{k}",
                type="tertiary",
                on_click=di,
                args=(k,)
            )

    # ---- Quy trình
    nhan_muc(
        "Quy trình",
        "Lagom Studio làm việc thế nào?",
        "Ba bước từ tấm ảnh bạn tải lên đến bộ trang phục hoàn chỉnh"
    )

    _, giua_qt, _ = st.columns([0.12, 1, 0.12])

    with giua_qt, st.container(border=True, key="khung_quy_trinh"):
        v, d = st.columns([1, 1.25], vertical_alignment="center")

        with v:
            html(HINH_VONG)

        with d:
            html(
                '''
                <div class="buoc buoc-hong"><b>1</b><div>
                <div class="buoc-ten">Nhận diện món đồ</div>
                <div class="buoc-mo-ta">Mô hình CLIP đọc ảnh để biết đó là áo, quần,
                giày hay phụ kiện, cùng kiểu dáng và phong cách của món.</div></div></div>
                <div class="buoc buoc-xanh"><b>2</b><div>
                <div class="buoc-ten">Cân bằng màu sắc</div>
                <div class="buoc-mo-ta">Chấm độ hợp giữa từng cặp món, áp dụng quy tắc
                phối màu và họa tiết của stylist.</div></div></div>
                <div class="buoc buoc-vang"><b>3</b><div>
                <div class="buoc-ten">Dựng bộ hoàn chỉnh</div>
                <div class="buoc-mo-ta">Ghép thành outfit theo dịp và phong cách,
                gợi ý món còn thiếu và cho bạn mặc thử lên người mẫu.</div></div></div>
                '''
            )

    # ---- Bộ đồ nổi bật từ cửa hàng (bộ đầu tiên của 3 phong cách đầu)
    ds_pc_noi_bat = list(getattr(C, "PHONG_CACH", {}))[:3]

    if ds_pc_noi_bat:
        nhan_muc(
            "Bộ sưu tập",
            "Bộ đồ nổi bật từ cửa hàng",
            "Dựng sẵn theo từng phong cách, bấm để phối hoặc chấm điểm"
        )

        with st.spinner("Đang dựng bộ đồ nổi bật…"):
            cot_nb = st.columns(len(ds_pc_noi_bat))
            for j, (col, ten_pc_nb) in enumerate(zip(cot_nb, ds_pc_noi_bat)):
                bst = lay_bo_suu_tap(j)
                if bst:
                    with col:
                        the_bo_san(bst[0], f"{ten_pc_nb} · Bộ 1", f"home_{j}")

        _, g_nb, _ = st.columns([1, 1, 1])
        g_nb.button(
            "Xem toàn bộ bộ sưu tập",
            icon=":material/arrow_forward:",
            key="home_xem_bst",
            on_click=di,
            args=("bo_suu_tap",),
            use_container_width=True
        )

    # ---- Tủ đồ
    dem = {
        n: sum(m["nhom"] == n for m in tu)
        for n in C.NHOM
    }

    nhan_muc("Tủ đồ", "Tủ đồ của bạn", "Tổng quan những món bạn đã lưu")

    so_lieu = [
        ("Tổng số món", len(tu), "Trong tủ đồ của bạn"),
        ("Áo", dem.get("Áo", 0), "Áo, sơ mi, áo khoác"),
        (
            "Quần & váy",
            dem.get("Quần/Chân váy", 0) + dem.get("Đồ liền thân", 0),
            "Quần, chân váy, váy liền"
        ),
        (
            "Giày, túi, phụ kiện",
            dem.get("Giày", 0) + dem.get("Túi xách", 0)
            + dem.get("Phụ kiện", 0),
            "Món hoàn thiện outfit"
        ),
    ]

    for col, (nhan, so, chu) in zip(st.columns(4), so_lieu):
        with col:
            html(
                f'<div class="home-stat-card">'
                f'<div class="home-stat-label">{nhan}</div>'
                f'<div class="home-stat-number">{so}</div>'
                f'<div class="home-stat-caption">{chu}</div></div>'
            )

    if not tu:
        st.info(
            "Bắt đầu bằng cách bấm **Món mới** ở góc trên "
            "và tải ảnh vài món bạn đang có."
        )


# ================= TỦ ĐỒ
elif trang == "tu_do":
    thanh_tu_do()

    tieu_de(
        "Tủ đồ của tôi",
        "Tải ảnh những món bạn đang có, mỗi ảnh một món. "
        "Lagom Studio tự nhận ra loại món và kiểu dáng.",
        "Bộ sưu tập"
    )

    with st.container(border=True, key="khung_tai_anh"):
        t1, t2 = st.columns([3, 1.2], vertical_alignment="center")
        t1.markdown(
            "<div class='panel-tieu-de'>Thêm món mới</div>"
            "<div class='panel-phu'>Mỗi ô một ảnh, chụp trên nền trơn, đủ sáng.</div>",
            unsafe_allow_html=True
        )
        with t2:
            o_tc(st.toggle, "tach_nen", "Tự tách nền ảnh")

        moi = the_tai_anh("td")

    chia_se = False

    if moi:
        chia_se = st.checkbox(
            "Chia sẻ các món này lên cửa hàng Lagom Studio",
            value=getattr(C, "CHIA_SE_MAC_DINH", True),
            help=(
                "Người dùng khác sẽ thấy ảnh món đồ trong trang "
                "Cửa hàng và trong gợi ý outfit, nhưng không thấy "
                "tên tài khoản của bạn."
            )
        )

    if moi and st.button(
        f"Lưu {len(moi)} món vào tủ đồ",
        icon=":material/save:",
        type="primary"
    ):
        mau_moi = []
        for m in moi:
            try:
                mau_moi.append(AI.ten_mau(m["bytes"]))
            except Exception:
                mau_moi.append(None)
        ghi_nhat_ky(
            "tai_anh",
            mon=[{"nhom": m["nhom"], "mau": t} for m, t in zip(moi, mau_moi)]
        )

        for m in moi:
            TK.luu_mon(
                U,
                m["bytes"],
                m["nhom"],
                m["ten"],
                m["v"],
                m.get("kieu_dang")
            )

            if chia_se:
                AI.chia_se_mon(
                    m["bytes"],
                    m["v"],
                    m["nhom"],
                    m["ten"],
                    m.get("kieu_dang")
                )

        lam_moi_the("td")
        st.toast(f"Đã lưu {len(moi)} món")
        st.rerun()

    tu = TK.doc_tu_do(U)

    st.divider()
    muc_tieu_de("Tủ đồ của bạn", f"{len(tu)} món")

    if not tu:
        st.info(
            "Tủ đồ còn trống. Tải ảnh các món bạn có ở phía trên."
        )

    # Cả loại lạ từ phiên bản cũ
    cac_loai = (
        list(C.NHOM)
        + sorted({m["nhom"] for m in tu} - set(C.NHOM))
    )

    for nh in cac_loai:
        ds = [
            m for m in tu
            if m["nhom"] == nh
        ]

        if not ds:
            continue

        nhom_tieu_de(nh, len(ds))

        cols = st.columns(C.SO_COT_TU_DO)

        for n, m in enumerate(ds):
            with cols[n % C.SO_COT_TU_DO], st.container(border=True, key=f"the_tu_{m['id']}"):
                st.image(m["bytes"], width=C.CO_ANH_THE)
                kd = AI.ten_kieu_dang(AI.kieu_dang(m), m["nhom"]) if nh in C.NHOM else ""
                st.caption(m["ten"] + (f" · {kd}" if kd else ""))

                nut_sua, nut_xoa = st.columns(2)

                # ---- Sửa tên, loại, kiểu dáng
                with nut_sua.popover(
                    "Sửa",
                    use_container_width=True,
                    help="Sửa tên, loại món, kiểu dáng"
                ):
                    ten_moi = st.text_input(
                        "Tên món",
                        value=m["ten"],
                        key=f"sua_t_{m['id']}"
                    )
                    ds_loai = list(C.NHOM)
                    nh_moi = st.selectbox(
                        "Loại món",
                        ds_loai,
                        index=ds_loai.index(m["nhom"]) if m["nhom"] in ds_loai else 0,
                        key=f"sua_n_{m['id']}",
                    )
                    kd_ds = getattr(C, "KIEU_DANG", {}).get(nh_moi, {})
                    kd_moi = None
                    if kd_ds:
                        ma_ds = list(kd_ds)
                        kd_hien = m.get("kieu_dang") if m.get("kieu_dang") in ma_ds else \
                            AI.kieu_dang(dict(m, nhom=nh_moi, kieu_dang=None))
                        kd_moi = st.selectbox(
                            "Kiểu dáng",
                            ma_ds,
                            index=ma_ds.index(kd_hien) if kd_hien in ma_ds else 0,
                            key=f"sua_kd_{m['id']}_{nh_moi}",
                            format_func=lambda x, d=kd_ds: d[x][0]
                        )
                    if st.button(
                        "Lưu thay đổi",
                        key=f"sua_ok_{m['id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        TK.sua_mon(
                            U, m["id"],
                            ten=ten_moi.strip() or m["ten"],
                            nhom=nh_moi,
                            kieu_dang=kd_moi
                        )
                        st.toast("Đã cập nhật món đồ")
                        st.rerun()

                # ---- Xóa (có hỏi lại)
                with nut_xoa.popover(
                    "Xóa",
                    use_container_width=True,
                    help="Xóa món này"
                ):
                    st.write("Xóa món này khỏi tủ đồ?")
                    if st.button(
                        "Xóa",
                        key=f"xoa_{m['id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        TK.xoa_mon(U, m["id"])
                        st.rerun()

# ================= CỬA HÀNG
elif trang == "cua_hang":
    thanh_tu_do()

    tieu_de(
        "Cửa hàng",
        "Sản phẩm có sẵn của Lagom Studio, món hợp xu hướng hiện trước. Chọn để đưa vào "
        "outfit ở trang Phối đồ, hoặc thêm vào tủ nếu bạn đã mua.",
        "Gợi ý mua sắm"
    )

    if st.button(
        "Cập nhật cửa hàng",
        icon=":material/refresh:",
        help="Thêm các món người dùng mới chia sẻ (mất khoảng nửa phút)"
    ):
        AI._tai.clear()
        for ham in ("bo_suu_tap", "thong_ke_kho"):
            if hasattr(getattr(AI, ham, None), "clear"):
                getattr(AI, ham).clear()
        st.rerun()

    kho = AI.kho_cua_hang()
    chon_kho = st.session_state.setdefault("kho_chon", [])

    def doi_chon(k):
        ds_chon = st.session_state.kho_chon
        if k in ds_chon:
            ds_chon.remove(k)
        else:
            ds_chon.append(k)

    o_tc(
        st.pills, "ch_nhom", "Loại", bat_buoc=True,
        options=list(C.NHOM), label_visibility="collapsed"
    )
    nh = st.session_state.tc_ch_nhom

    c2, c3 = st.columns([2, 1])
    tu_khoa = c2.text_input(
        "Tìm theo tên",
        placeholder="blouse, jeans, sandal…",
        key="ch_tim"
    )
    mau = c3.selectbox(
        "Màu",
        ["Tất cả"] + sorted(kho["colour_group_name"].dropna().unique()),
        key="ch_mau"
    )

    ds = kho[kho["nhom_phoi"] == nh]

    if tu_khoa:
        ds = ds[ds["prod_name"].str.contains(tu_khoa, case=False, na=False, regex=False)]

    if mau != "Tất cả":
        ds = ds[ds["colour_group_name"] == mau]

    st.caption(
        f"Đã chọn {len(chon_kho)} món từ cửa hàng để phối · "
        "sang trang Phối đồ để ghép outfit"
    )

    if len(ds) == 0:
        st.info("Không có sản phẩm nào khớp bộ lọc.")
    else:
        moi_trang = 15
        so_trang = (len(ds) - 1) // moi_trang + 1
        khoa_trang = f"ch_trang_{nh}_{tu_khoa}_{mau}"

        st.caption(f"{len(ds):,} món")
        so = phan_trang(khoa_trang, so_trang, "tren")
        cols = st.columns(C.SO_COT_TU_DO)

        for n, k in enumerate(ds.index[(so - 1) * moi_trang: so * moi_trang]):
            k = int(k)
            m = AI.mon_kho(k)

            with cols[n % C.SO_COT_TU_DO], st.container(border=True, key=f"the_ch_{k}"):
                st.image(m["bytes"], width=C.CO_ANH_THE)
                kd = AI.ten_kieu_dang(AI.kieu_dang(m), m["nhom"])
                st.caption(m["ten"] + (f" · {kd}" if kd else ""))

                if str(m.get("id", "")).startswith("XH-"):
                    st.caption(f"Mã sản phẩm: {m['id']}")

                st.checkbox(
                    "Chọn để phối",
                    value=k in chon_kho,
                    key=f"kc_{k}",
                    on_change=doi_chon,
                    args=(k,)
                )

                if st.button(
                    "Thêm vào tủ",
                    icon=":material/add:",
                    key=f"kt_{k}",
                    use_container_width=True
                ):
                    TK.luu_mon(
                        U, m["bytes"], m["nhom"],
                        m["ten"], m["v"], m.get("kieu_dang")
                    )
                    st.toast("Đã thêm vào tủ đồ")

        st.write("")
        phan_trang(khoa_trang, so_trang, "duoi")


# ================= PHỐI ĐỒ
elif trang == "phoi":
    tieu_de(
        "Phối đồ",
        "Chọn món bạn muốn mặc, Lagom Studio ghép thành outfit theo dịp và phong cách. "
        "Đổi lựa chọn bất cứ lúc nào, outfit tự cập nhật.",
        "Stylist AI"
    )

    tu = TK.doc_tu_do(U)
    kho_chon = [
        AI.mon_kho(k)
        for k in st.session_state.get("kho_chon", [])
    ]

    if not tu and not kho_chon:
        st.info("Tủ đồ của bạn đang trống.")
        st.button(
            "Tới tủ đồ",
            icon=":material/arrow_forward:",
            on_click=di,
            args=("tu_do",),
            type="primary"
        )
    else:
        tat_ca = tu + kho_chon

        # Món đã tick lưu ở "tc_chon_<id>", nên không mất khi chuyển sang xem kết quả
        bb = [
            i for i, m in enumerate(tu)
            if st.session_state.get(f"tc_chon_{m['id']}")
        ]
        bb += list(range(len(tu), len(tat_ca)))

        TP = {
            "ao": "Áo",
            "quan": "Quần/Chân váy",
            "vay_lien": "Váy liền",
            "ao_khoac": "Áo khoác",
            "giay": "Giày",
            "tui": "Túi xách",
            "phu_kien": "Phụ kiện"
        }

        trai, phai = st.columns([1, 2.7], gap="large")

        # ======== Cột trái: tùy chọn + thành phần + nút phối
        with trai:
            bang_tuy_chon(("nguon", "dip", "pc", "so_bo", "mau"))

            with st.container(border=True, key="khung_thanh_phan"):
                html(
                    "<div class='panel-tieu-de'>Outfit gồm</div>"
                    "<div class='panel-phu'>Không chọn ô nào = đầy đủ tất cả</div>"
                )

                tp_chon = []
                cot_tp = st.columns(2)

                for n, (k, nhan) in enumerate(TP.items()):
                    if cot_tp[n % 2].checkbox(nhan, key=f"tp_{k}"):
                        tp_chon.append(k)

                tp_chon = tuple(tp_chon)

            dem = {
                n: sum(tat_ca[i]["nhom"] == n for i in bb)
                for n in C.NHOM
            }

            ao_da_tick = [
                tat_ca[i] for i in bb
                if tat_ca[i]["nhom"] == "Áo"
            ]

            mau_thuan = (
                dem.get("Áo", 0) > 2
                or dem.get("Quần/Chân váy", 0) > 1
                or dem.get("Đồ liền thân", 0) > 1
                or dem.get("Giày", 0) > 1
                or dem.get("Túi xách", 0) > 1
                or (
                    dem.get("Đồ liền thân", 0)
                    and (
                        dem.get("Áo", 0) > 1
                        or dem.get("Quần/Chân váy", 0)
                        or (
                            ao_da_tick
                            and not AI.la_ao_khoac(ao_da_tick[0]["v"])
                        )
                    )
                )
            )

            khoa = (
                tuple(sorted(str(tat_ca[i].get("id", "")) for i in bb)),
                j_dip, j_pc, ket_hop, so_bo, toi_da_kho,
                len(tu), tp_chon
            )

            if mau_thuan:
                st.warning(
                    "Các món đã chọn không mặc chung được: mỗi bộ tối đa 2 áo "
                    "(ví dụ áo + áo khoác), 1 quần/chân váy, 1 đôi giày, "
                    "1 túi; váy liền chỉ đi cùng áo khoác."
                )
                st.session_state.pop("kq_phoi", None)

            else:
                st.caption(
                    f"Đã chọn {len(bb)} món"
                    + (f" · dịp {dip}" if j_dip is not None else "")
                    + (
                        " · kết hợp món từ cửa hàng"
                        if ket_hop else " · chỉ dùng đồ trong tủ"
                    )
                )

                da_co_kq = "kq_phoi" in st.session_state
                bam = st.button(
                    "Phối lại bộ khác" if da_co_kq
                    else "Phối đồ với món đã chọn" if bb
                    else "Gợi ý outfit từ cả tủ",
                    icon=":material/refresh:" if da_co_kq else ":material/auto_awesome:",
                    type="primary",
                    use_container_width=True
                )

                tu_dong = (
                    "kq_phoi" in st.session_state
                    and st.session_state.get("khoa_phoi") != khoa
                )

                if bam or tu_dong:
                    with st.spinner("AI đang phối đồ…"):
                        kq = AI.phoi(
                            tat_ca, j_dip, so_bo, ket_hop, bb,
                            toi_da_kho, j_pc,
                            st.session_state.get("da_goi_y", []),
                            tp_chon or None,
                            [b["V"] for b in TK.doc_bo(U)]
                        )

                        st.session_state.kq_phoi = (kq, set(bb))
                        st.session_state.khoa_phoi = khoa

                        ghi_nhat_ky(
                            "phoi",
                            phong_cach=pc or "Tự chọn",
                            dip=dip,
                            bo=[
                                {
                                    "diem": round(float(d_), 4),
                                    "kho": [
                                        int(kq[1][i]["k"]) for i in idx_
                                        if kq[1][i].get("nguon") == "kho" and "k" in kq[1][i]
                                    ],
                                }
                                for idx_, d_ in kq[0]
                            ],
                        )
                        st.session_state.da_doi = set()
                        st.session_state.lich_su_doi = {}

                        chon_moi, pool_moi = kq
                        # Nhớ mọi món vừa gợi ý (trừ món bạn tick) để lần sau
                        # Lagom Studio ưu tiên món khác, tránh lặp lại bộ cũ
                        moi_ids = [
                            pool_moi[i]["id"]
                            for idx, _ in chon_moi
                            for i in idx
                            if i not in bb and pool_moi[i].get("id") is not None
                        ]

                        nho = getattr(C, "SO_NHO_GOI_Y", 30)
                        st.session_state.da_goi_y = (
                            st.session_state.get("da_goi_y", []) + moi_ids
                        )[-max(nho, 1):] if nho else []

                if bam:
                    st.session_state.tc_xem = "ket_qua"
                    # Vẽ lại ngay để nút đổi thành "Phối lại bộ khác"
                    # (không phối lại lần nữa vì khóa phối đã khớp)
                    st.rerun()

        # ======== Cột phải: chọn món / xem bộ đồ
        with phai:
            co_kq = "kq_phoi" in st.session_state

            html(
                '<div class="cac-buoc">'
                f'<span class="xong">1</span>Chọn món'
                f'<i></i><span class="xong">2</span>Thiết lập'
                f'<i></i><span class="{"xong" if co_kq else ""}">3</span>Bộ đồ'
                '</div>'
            )

            o_tc(
                st.segmented_control, "xem", "Xem", bat_buoc=True,
                options=["chon", "ket_qua"],
                format_func={
                    "chon": f"Chọn món ({len(bb)})",
                    "ket_qua": "Bộ đồ gợi ý"
                }.get,
                label_visibility="collapsed"
            )

            if st.session_state.tc_xem == "chon":
                cac_loai = list(C.NHOM) + sorted(
                    {m["nhom"] for m in tu} - set(C.NHOM)
                )

                for nh in cac_loai:
                    ds = [
                        (i, m)
                        for i, m in enumerate(tu)
                        if m["nhom"] == nh
                    ]

                    if not ds:
                        continue

                    nhom_tieu_de(nh, len(ds))
                    cols = st.columns(C.SO_COT_TU_DO)

                    for n, (i, m) in enumerate(ds):
                        with cols[n % C.SO_COT_TU_DO], st.container(
                            border=True, key=f"the_ph_{m['id']}"
                        ):
                            st.image(m["bytes"], width=C.CO_ANH_THE)
                            o_tc(
                                st.checkbox, f"chon_{m['id']}", m["ten"],
                                mac_dinh=False
                            )

                if kho_chon:
                    nhom_tieu_de("Món chọn từ cửa hàng", "luôn có trong outfit")
                    cols = st.columns(C.SO_COT_TU_DO)

                    for n, m in enumerate(kho_chon):
                        with cols[n % C.SO_COT_TU_DO], st.container(
                            border=True, key=f"the_kc_{n}"
                        ):
                            st.image(m["bytes"], width=C.CO_ANH_THE)
                            st.caption(m["ten"])

                    if st.button("Bỏ chọn món cửa hàng"):
                        st.session_state.kho_chon = []
                        st.rerun()

            elif not co_kq:
                st.info(
                    "Chưa có bộ đồ nào. Chọn món ở mục **Chọn món**, "
                    "hoặc bấm nút phối đồ ở cột bên trái."
                )

            else:
                (chon, pool), bb_cu = st.session_state.kq_phoi

                ten_pc = pc
                if (
                    j_pc is None
                    and bb_cu
                    and getattr(C, "TU_DOAN_PHONG_CACH", True)
                ):
                    j_tu = AI.doan_phong_cach(
                        [pool[i]["v"] for i in bb_cu]
                    )
                    if j_tu is not None:
                        ten_pc = list(C.PHONG_CACH)[j_tu]

                html(
                    '<div class="kq-tieu-de">'
                    + (
                        f"Outfit theo phong cách <em>{esc(ten_pc)}</em>"
                        if ten_pc else "Outfit gợi ý cho bạn"
                    )
                    + "</div>"
                )

                st.session_state["pc_hien_tai"] = ten_pc or "Tự chọn"

                if ten_pc and not pc:
                    st.caption("Phong cách Lagom Studio tự chọn theo món của bạn.")

                so_bo_luu = len(TK.doc_bo(U))
                if so_bo_luu:
                    st.caption(
                        f"Lagom Studio đang học gu của bạn từ {so_bo_luu} bộ đồ đã lưu."
                    )

                if not chon:
                    st.warning(
                        "Chưa phối được bộ hoàn chỉnh. Thử chọn "
                        "'Tủ đồ + cửa hàng', hoặc tải thêm đồ vào tủ."
                    )
                else:
                    if len(chon) < so_bo:
                        st.caption(
                            f"Tủ đồ hiện chỉ đủ tạo {len(chon)} outfit khác nhau."
                        )

                    # Nhãn tab cố định, nên tab đang xem không bị nhảy khi đổi món
                    for n, (tab, (idx, hop)) in enumerate(
                        zip(st.tabs([f"Bộ {n + 1}" for n in range(len(chon))]), chon)
                    ):
                        with tab:
                            hien_bo(
                                f"Outfit {n + 1}",
                                pool, idx, hop,
                                bb=bb_cu,
                                vi_tri=n
                            )


# ================= CHẤM BỘ TỰ PHỐI
elif trang == "cham":
    tieu_de(
        "Chấm bộ tự phối",
        "Dựng bộ đồ từ tủ của bạn, Lagom Studio chấm điểm ngay và gợi ý cách phối đẹp hơn.",
        "Đánh giá outfit"
    )

    trai_c, phai_c = st.columns([1, 2.7], gap="large")

    with trai_c:
        bang_tuy_chon(("dip", "mau", "tach_nen"))

    with phai_c:
        O = {
            "ao": ("Áo", ["Áo"]),
            "khoac": ("Áo khoác · tùy chọn", ["Áo"]),
            "duoi": ("Quần, chân váy, váy liền", ["Quần/Chân váy", "Đồ liền thân"]),
            "giay": ("Giày", ["Giày"]),
            "tui": ("Túi xách", ["Túi xách"]),
            "pk": ("Phụ kiện", ["Phụ kiện"])
        }

        THU_TU_O = ["ao", "khoac", "duoi", "giay", "tui", "pk"]
        S = st.session_state.setdefault("ban_phoi", {})
        tu = TK.doc_tu_do(U)

        def hop_chon_mon(o):
            nhoms = O[o][1]
            khac = [m for k, m in S.items() if k != o]
            # Món đã nằm ở ô khác (vd. cùng một chiếc áo cho ô Áo và ô Áo khoác)
            da_o_khac = {m.get("id") for m in khac if m.get("id")}

            t1, t2, t3 = st.tabs([
                "Tủ đồ của tôi",
                "Cửa hàng",
                "Tải ảnh mới"
            ])

            with t1:
                ds = [
                    m for m in tu
                    if m["nhom"] in nhoms and m["id"] not in da_o_khac
                ]

                if not ds:
                    st.info(
                        "Tủ đồ chưa có món loại này. "
                        "Thử tab Cửa hàng hoặc Tải ảnh mới."
                    )

                cols = st.columns(4)

                for n, m in enumerate(ds):
                    with cols[n % 4]:
                        st.image(m["bytes"], width=120)
                        st.caption(m["ten"])

                        if st.button(
                            "Chọn",
                            key=f"hc_tu_{o}_{m['id']}",
                            use_container_width=True
                        ):
                            S[o] = dict(m, nguon="tu")
                            st.rerun()

            with t2:
                kho = AI.kho_cua_hang()

                a, b = st.columns([2, 1])
                tu_khoa = a.text_input(
                    "Tìm theo tên",
                    key=f"hc_tim_{o}",
                    placeholder="blouse, jeans, sandal…"
                )
                mau = b.selectbox(
                    "Màu",
                    ["Tất cả"] + sorted(
                        kho["colour_group_name"].dropna().unique()
                    ),
                    key=f"hc_mau_{o}"
                )

                xep = []
                for nh in nhoms:
                    xep += AI.xep_hang_kho(khac, nh, j_dip)

                xep.sort(key=lambda x: -x[1])

                if tu_khoa or mau != "Tất cả":
                    loc = kho

                    if tu_khoa:
                        loc = loc[
                            loc["prod_name"].str.contains(
                                tu_khoa, case=False, na=False, regex=False
                            )
                        ]

                    if mau != "Tất cả":
                        loc = loc[
                            loc["colour_group_name"] == mau
                        ]

                    giu = set(loc.index)
                    xep = [x for x in xep if x[0] in giu]

                if not xep:
                    st.info("Không có món nào khớp bộ lọc.")

                else:
                    so_trang = (len(xep) - 1) // 12 + 1

                    st.caption(
                        f"{len(xep):,} món · "
                        "sắp xếp theo mức hợp với các món bạn đã chọn"
                    )

                    trang_hop = phan_trang(
                        f"hc_trang_{o}_{tu_khoa}_{mau}",
                        so_trang,
                        "hop"
                    )

                    cols = st.columns(4)

                    for n, (k, _) in enumerate(
                        xep[(trang_hop - 1) * 12: trang_hop * 12]
                    ):
                        m = AI.mon_kho(k)

                        with cols[n % 4]:
                            st.image(m["bytes"], width=120)
                            st.caption(m["ten"])

                            if st.button(
                                "Chọn",
                                key=f"hc_kho_{o}_{m['id']}",
                                use_container_width=True
                            ):
                                S[o] = m
                                st.rerun()

            with t3:
                f = st.file_uploader(
                    "Ảnh món đồ (nền trơn, đủ sáng)",
                    type=["jpg", "jpeg", "png", "webp"],
                    key=f"hc_f_{o}"
                )

                if f is not None:
                    b, v, _ = xu_ly_anh(f)
                    st.image(b, width=160)

                    nh, kd = chon_loai_kieu(v, f"hc_{o}_{len(b)}")

                    if nh not in nhoms:
                        st.warning(
                            f"Ô này dành cho: {', '.join(nhoms)}."
                        )

                    ten_mon = st.text_input(
                        "Tên món (tùy chọn)",
                        key=f"hc_t_{o}"
                    )

                    if nh in nhoms and st.button(
                        "Dùng món này",
                        type="primary",
                        key=f"hc_ok_{o}"
                    ):
                        S[o] = dict(
                            bytes=b,
                            v=v,
                            nhom=nh,
                            ten=ten_mon or nh,
                            nguon="tu",
                            moi=True,
                            kieu_dang=kd
                        )
                        st.rerun()

        lam_hop = getattr(st, "dialog", None) or getattr(
            st, "experimental_dialog"
        )
        mo_hop = lam_hop("Chọn món cho bộ đồ", width="large")(hop_chon_mon)

        def bang_nhiet(mon, P):
            ten = [esc(m["ten"][:16]) for m in mon]
            dau = "".join(f"<th>{t}</th>" for t in ten)
            hang = ""

            for i in range(len(mon)):
                o_html = ""

                for j in range(len(mon)):
                    if i == j:
                        o_html += "<td class='cheo'>–</td>"
                    else:
                        s = float(P[i, j])
                        mau_chu = "#fff" if s > 0.55 else "#2b2228"
                        o_html += (
                            f"<td style='background:rgba(180,70,106,"
                            f"{max(s, 0.08):.2f});color:{mau_chu}'>"
                            f"{s * 100:.0f}</td>"
                        )

                hang += f"<tr><th class='dong'>{ten[i]}</th>{o_html}</tr>"

            return (
                "<table class='bang-nhiet'>"
                f"<tr><th></th>{dau}</tr>{hang}</table>"
            )

        muc_tieu_de("Bàn phối đồ", "Chọn từng món, điểm cập nhật ngay")

        for hang_o in (
            ["ao", "khoac", "duoi"],
            ["giay", "tui", "pk"]
        ):
            for c, o in zip(st.columns(3), hang_o):
                with c, st.container(border=True, key=f"the_o_{o}"):
                    st.markdown(
                        f'<div class="o-nhan">{O[o][0]}</div>',
                        unsafe_allow_html=True
                    )
                    m = S.get(o)

                    if m:
                        st.image(m["bytes"], width=C.CO_ANH_THE)
                        st.caption(m["ten"])

                        a, b = st.columns(2)

                        if a.button(
                            "Đổi",
                            key=f"o_doi_{o}",
                            use_container_width=True
                        ):
                            mo_hop(o)

                        if b.button(
                            "Bỏ",
                            key=f"o_bo_{o}",
                            use_container_width=True
                        ):
                            S.pop(o)
                            st.rerun()

                    else:
                        st.markdown(
                            "<div class='o-trong'>+</div>",
                            unsafe_allow_html=True
                        )

                        if st.button(
                            "Chọn món",
                            key=f"o_chon_{o}",
                            use_container_width=True
                        ):
                            mo_hop(o)

        cac_o = [o for o in THU_TU_O if o in S]
        mon = [S[o] for o in cac_o]

        if len(mon) < 2:
            st.info("Chọn ít nhất 2 món, Lagom Studio sẽ chấm điểm ngay.")

        else:
            V = [m["v"] for m in mon]
            P = AI.ma_tran_diem(V)
            idx = list(range(len(mon)))
            hop = AI.diem_bo(P, idx)
            diem100 = round(hop * 100)

            k_cham = khoa_thu("cham", *mon)
            if st.session_state.get("_cham_cuoi") != k_cham:
                st.session_state["_cham_cuoi"] = k_cham
                ghi_nhat_ky("cham", diem=round(float(hop), 4), so_mon=len(mon))

            muc = (
                "rat" if hop >= C.NGUONG_RAT_HOP
                else "kha" if hop >= C.NGUONG_KHA_HOP
                else "it"
            )

            nhan_xet = {
                "rat": "Bộ đồ rất hài hòa",
                "kha": "Khá ổn, có thể tinh chỉnh thêm",
                "it": "Các món chưa hợp nhau lắm"
            }[muc]

            st.divider()
            muc_tieu_de("Phiếu chấm điểm")

            trai, phai = st.columns([1, 1.4])

            with trai, st.container(border=True, key="khung_diem"):
                st.markdown(
                    f"<div class='diem-the'>"
                    f"<div class='diem-so' style='color:{C.NHAN_DIEM[muc][1]}'>"
                    f"{diem100}</div>"
                    f"<div class='diem-thang'>/ 100 điểm</div>"
                    f"<div class='diem-nhan-xet'>{nhan_xet}</div></div>",
                    unsafe_allow_html=True
                )

            with phai, st.container(border=True, key="khung_dip"):
                st.markdown(
                    "<div class='the-tieu-de'>Bộ này hợp để"
                    "<small>AI ước lượng</small></div>",
                    unsafe_allow_html=True
                )

                pct = np.clip(50 + 20 * AI.phu_hop_dip(V), 0, 100)

                for ten_dip, p in sorted(
                    zip(C.DIP, pct),
                    key=lambda x: -x[1]
                ):
                    st.progress(
                        int(p) / 100,
                        text=f"{ten_dip} · {int(p)}%"
                    )

            with st.container(border=True, key="khung_nhiet"):
                st.markdown(
                    "<div class='the-tieu-de'>Các món hợp nhau đến đâu"
                    "<small>ô càng đậm càng hợp, thang 100</small></div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    bang_nhiet(mon, P),
                    unsafe_allow_html=True
                )

            yeu = int(np.argmin([
                np.mean([P[a, b] for b in idx if b != a])
                for a in idx
            ]))

            o_yeu = cac_o[yeu]

            muc_tieu_de("Gợi ý cải thiện")
            st.write(
                f"Món kém hợp nhất với cả bộ: **{mon[yeu]['ten']}**. "
                "Thử thay bằng:"
            )

            dang_dung = {m.get("id") for m in mon}
            khac = [m for i, m in enumerate(mon) if i != yeu]

            ung = [
                dict(m, nguon="tu")
                for m in tu
                if m["nhom"] in O[o_yeu][1]
                and m["id"] not in dang_dung
            ]

            for nh in O[o_yeu][1]:
                ung += [
                    m for m, _ in AI.top_kho(khac, nh, j_dip, 5)
                    if m["id"] not in dang_dung
                ]

            ket = []

            for cm in ung:
                V2 = [
                    cm["v"] if i == yeu else m["v"]
                    for i, m in enumerate(mon)
                ]
                ket.append((
                    AI.diem_bo(AI.ma_tran_diem(V2), idx),
                    cm
                ))

            ket = sorted(
                [x for x in ket if x[0] > hop],
                key=lambda x: -x[0]
            )[:3]

            if not ket:
                st.caption(
                    "Chưa tìm được món giúp bộ đồ đẹp hơn. "
                    "Bộ này đã khá ổn!"
                )

            for c, (d2, m2) in zip(st.columns(3), ket):
                with c, st.container(border=True, key=f"the_gy_{m2.get('id')}"):
                    st.image(m2["bytes"], width=C.CO_ANH_THE)
                    st.caption(
                        f"{m2['ten']} · {C.NGUON[m2.get('nguon', 'tu')]}"
                    )
                    st.markdown(
                        f"Điểm bộ đồ: **{diem100} → {round(d2 * 100)}**"
                    )

                    if st.button(
                        "Thay thử",
                        key=f"thay_{m2.get('id')}",
                        use_container_width=True
                    ):
                        S[o_yeu] = m2
                        st.rerun()

            muc_tieu_de("Bảng phối đồ và mặc thử")
            hien_bo("Bộ đồ của bạn", mon, idx, hop)

            a, b = st.columns(2)
            moi = [m for m in mon if m.get("moi")]

            if moi and a.button(
                f"Lưu {len(moi)} món mới vào tủ đồ",
                icon=":material/save:",
                use_container_width=True
            ):
                for m in moi:
                    TK.luu_mon(
                        U, m["bytes"], m["nhom"],
                        m["ten"], m["v"], m.get("kieu_dang")
                    )
                    m["moi"] = False

                st.toast("Đã lưu vào tủ đồ")

            if b.button(
                "Làm lại bộ khác",
                icon=":material/restart_alt:",
                use_container_width=True
            ):
                st.session_state.ban_phoi = {}
                st.rerun()


# ================= BỘ ĐỒ ĐÃ LƯU
elif trang == "da_luu":
    thanh_tu_do()

    tieu_de(
        "Bộ đồ đã lưu",
        "Những bộ bạn đã lưu, chỉ bạn thấy. "
        "Lagom Studio học từ các bộ này để gợi ý hợp gu bạn hơn.",
        "Bộ sưu tập"
    )

    ds_bo = TK.doc_bo(U)

    if not ds_bo:
        st.info(
            "Chưa có bộ nào. Ở trang Phối đồ, "
            "bấm **Lưu bộ đồ này** dưới outfit bạn thích."
        )

    cols = st.columns(3)

    for n, b in enumerate(reversed(ds_bo)):
        with cols[n % 3], st.container(border=True, key=f"khung_luu_{b['id']}"):
            html(
                f'<div class="bo-dau"><span class="bo-ten">Bộ {len(ds_bo) - n}</span>'
                f'<span class="badge badge-nhe">{len(b["mon"])} món</span></div>'
                '<div class="day-anh">'
                + "".join(
                    '<div class="day-anh-o">'
                    + o_anh(m["bytes"])
                    + f'<div class="o-phu">{esc(NHAN_NGAN.get(m["nhom"], m["nhom"]))}</div>'
                    + f'<div class="o-ten nho">{esc(m["ten"])}</div></div>'
                    for m in b["mon"]
                )
                + "</div>"
                + dai_mau([m["bytes"] for m in b["mon"]])
            )

            if st.button(
                "Xóa bộ này",
                icon=":material/delete:",
                key=f"xoa_bo_{b['id']}"
            ):
                TK.xoa_bo(U, b["id"])
                st.rerun()


# ================= BỘ SƯU TẬP
elif trang == "bo_suu_tap":
    tieu_de(
        "Bộ sưu tập",
        "Những bộ đồ Lagom Studio dựng sẵn từ kho theo từng phong cách. Mỗi bộ có áo và quần "
        "(hoặc váy liền), giày, túi, phụ kiện. Bấm \"Phối với món chính\" để dùng món chính "
        "của bộ làm điểm xuất phát rồi tùy chỉnh theo ý bạn.",
        "Cảm hứng"
    )

    ds_pc_bst = list(getattr(C, "PHONG_CACH", {}))

    if not ds_pc_bst:
        st.info("Chưa khai báo phong cách nào trong cai_dat.py (mục PHONG_CACH).")
    else:
        st.session_state.setdefault("tc_bst_pc", ds_pc_bst[0])
        _, g_pc, _ = st.columns([0.08, 1, 0.08])
        with g_pc:
            o_tc(
                st.pills, "bst_pc", "Phong cách", bat_buoc=True,
                options=ds_pc_bst, label_visibility="collapsed"
            )

        ten_bst = st.session_state.tc_bst_pc
        j_bst = ds_pc_bst.index(ten_bst) if ten_bst in ds_pc_bst else 0

        with st.spinner(f"Đang dựng bộ sưu tập {ten_bst}… (lần đầu mất khoảng nửa phút)"):
            bst = lay_bo_suu_tap(j_bst)

        if not bst:
            st.info(
                "Kho cửa hàng chưa đủ món để dựng bộ cho phong cách này. "
                "Bấm **Dựng lại bộ sưu tập** bên dưới để thử lại."
            )

        cot_bst = st.columns(2, gap="medium")
        for n, bo in enumerate(bst):
            with cot_bst[n % 2]:
                the_bo_san(bo, f"{ten_bst} · Bộ {n + 1}", f"bst_{j_bst}_{n}")

        st.write("")
        _, g_dl, _ = st.columns([1, 0.8, 1])
        if g_dl.button(
            "Dựng lại bộ sưu tập",
            icon=":material/refresh:",
            key="bst_dung_lai",
            use_container_width=True,
            help="Xóa bộ sưu tập đã nhớ và dựng lại từ kho hiện tại"
        ):
            getattr(AI.bo_suu_tap, "clear", lambda: None)()
            st.rerun()


# ================= THỐNG KÊ
elif trang == "thong_ke":
    from collections import Counter
    import datetime as _dt

    tieu_de(
        "Thống kê",
        "Khách đang quan tâm phong cách và màu nào, bộ đồ nào được khách thấy \"Hợp\", "
        "món nào trong kho được gợi ý nhiều và món nào chưa từng được dùng.",
        "Dành cho cửa hàng"
    )

    nk = doc_nhat_ky()
    theo_loai = {}
    for e in nk:
        theo_loai.setdefault(e.get("loai"), []).append(e)

    tai = [m for e in theo_loai.get("tai_anh", []) for m in e.get("mon", [])]
    lan_phoi = theo_loai.get("phoi", [])
    so_bo_dung = sum(len(e.get("bo", [])) for e in lan_phoi)
    cham = theo_loai.get("cham", [])
    ph = theo_loai.get("phan_hoi", [])
    so_hop = sum(1 for e in ph if e.get("hop"))

    def the_so(nhan, so, chu, lop):
        return (
            f'<div class="tk-so {lop}"><div class="tk-so-so">{so}</div>'
            f'<div class="tk-so-nhan">{nhan}</div>'
            f'<div class="tk-so-chu">{chu}</div></div>'
        )

    def thanh_ngang(tieu, cap, mau_thanh=None, rong_nhat=None):
        """Thẻ danh sách thanh ngang: [(nhãn, số)]."""
        if not cap:
            return (
                f'<div class="tk-the"><div class="tk-tieu">{tieu}</div>'
                '<div class="tk-trong">Chưa có dữ liệu</div></div>'
            )
        lon = rong_nhat or max(v for _, v in cap) or 1
        dong = "".join(
            f'<div class="tk-dong"><span class="tk-nhan">'
            + (f'<i style="background:{mau_thanh[k]}"></i>' if mau_thanh and k in mau_thanh else "")
            + f'{esc(str(k))}</span>'
            f'<span class="tk-thanh"><b style="width:{max(v / lon * 100, 3):.0f}%"></b></span>'
            f'<span class="tk-gt">{v:,}</span></div>'
            for k, v in cap
        )
        return f'<div class="tk-the"><div class="tk-tieu">{tieu}</div>{dong}</div>'

    MAU_TEN = {
        "Đen": "#2d2329", "Trắng": "#f4f1ee", "Xám": "#a7a2a6", "Be / nâu": "#b98f6b",
        "Đỏ": "#d1495b", "Cam": "#f08a4b", "Vàng": "#f2cc5b", "Xanh cốm": "#b5d36b",
        "Xanh lá": "#6fb67a", "Xanh ngọc": "#5bc0b4", "Xanh lơ": "#6cb8e6",
        "Xanh dương": "#4f73c9", "Xanh tím": "#7a6fd0", "Tím": "#a678d6",
        "Hồng tím": "#d27bc9", "Hồng": "#ec8fb0",
    }

    # ---- Hàng 1: số tổng
    diem_tb = (
        f" · điểm TB {sum(e.get('diem', 0) for e in cham) / len(cham) * 100:.0f}"
        if cham else ""
    )
    html(
        '<div class="tk-hang4">'
        + the_so("Ảnh món đã phân tích", len(tai), "Món khách tải vào tủ đồ", "hong")
        + the_so("Số bộ đồ đã dựng", so_bo_dung, f"Qua {len(lan_phoi)} lượt phối", "xanh")
        + the_so("Lượt chấm outfit", len(cham), "Bộ khách tự phối" + diem_tb, "vang")
        + the_so(
            "Khách thấy \"Hợp\"",
            f"{so_hop / len(ph) * 100:.0f}%" if ph else "chưa có",
            f"Trên {len(ph)} lượt phản hồi" if ph else "Chưa có phản hồi nào",
            "tim"
        )
        + "</div>"
    )

    # ---- Hàng 2
    pc_dung = Counter(e.get("phong_cach", "Tự chọn") for e in lan_phoi).most_common(6)
    mau_tai = Counter(m["mau"] for m in tai if m.get("mau")).most_common(6)
    loai_tai = Counter(m["nhom"] for m in tai).most_common(6)

    hom_nay = _dt.date.today()
    ngay7 = [hom_nay - _dt.timedelta(days=i) for i in range(6, -1, -1)]
    dem_ngay = Counter(e.get("luc", "")[:10] for e in nk)
    cot = [(d, dem_ngay.get(d.isoformat(), 0)) for d in ngay7]
    lon_ngay = max([v for _, v in cot] + [1])
    bieu_do_ngay = (
        '<div class="tk-the"><div class="tk-tieu">Lượt dùng 7 ngày qua</div><div class="tk-cot">'
        + "".join(
            f'<div class="tk-cot-o"><span class="tk-cot-so">{v or ""}</span>'
            f'<b style="height:{max(v / lon_ngay * 100, 2):.0f}%"></b>'
            f'<small>{d.strftime("%d/%m")}</small></div>'
            for d, v in cot
        )
        + "</div></div>"
    )

    html(
        '<div class="tk-hang4">'
        + thanh_ngang("Phong cách được dùng nhiều nhất", pc_dung)
        + thanh_ngang("Màu chủ đạo của món khách tải lên", mau_tai, MAU_TEN)
        + thanh_ngang("Loại món khách tải lên", loai_tai)
        + bieu_do_ngay
        + "</div>"
    )

    # ---- Hàng 3
    ty_le = []
    for ten_pc_tk, ds_e in sorted(
        {e.get("phong_cach", "Tự chọn"): None for e in ph}.items()
    ):
        ds_ph = [e for e in ph if e.get("phong_cach", "Tự chọn") == ten_pc_tk]
        ty_le.append((ten_pc_tk, round(sum(e.get("hop") for e in ds_ph) / len(ds_ph) * 100)))
    ty_le.sort(key=lambda x: -x[1])

    try:
        tk_kho = AI.thong_ke_kho()
    except Exception:
        tk_kho = {"tong": 0, "theo_loai": {}, "theo_phong_cach": {}}

    html(
        '<div class="tk-hang3">'
        + thanh_ngang("Tỉ lệ \"Hợp\" theo phong cách (%)", ty_le, rong_nhat=100)
        + thanh_ngang(
            "Kho đồ theo phong cách nổi trội",
            sorted(tk_kho["theo_phong_cach"].items(), key=lambda x: -x[1])
        )
        + thanh_ngang(
            "Kho đồ theo loại",
            sorted(tk_kho["theo_loai"].items(), key=lambda x: -x[1])
        )
        + "</div>"
    )

    # ---- Món được gợi ý nhiều nhất
    dem_mon = Counter(k for e in lan_phoi for b in e.get("bo", []) for k in b.get("kho", []))
    muc_tieu_de(
        "Món được gợi ý nhiều nhất",
        "tính trên dữ liệu sử dụng thật"
    )

    if not dem_mon:
        st.info("Chưa có lượt phối nào. Số liệu sẽ hiện khi khách bắt đầu phối đồ.")
    else:
        top_mon = dem_mon.most_common(10)
        cot_mon = st.columns(5)
        for n, (k, so_lan) in enumerate(top_mon):
            try:
                m = AI.mon_kho(k)
            except Exception:
                continue
            with cot_mon[n % 5]:
                html(
                    o_anh(m["bytes"], NHAN_NGAN.get(m["nhom"], m["nhom"]))
                    + f'<div class="o-ten">{esc(m["ten"])}</div>'
                    f'<span class="badge badge-nhe">{so_lan} lần</span>'
                )

        if tk_kho["tong"]:
            st.caption(
                f"Đã có {len(dem_mon):,} trên {tk_kho['tong']:,} sản phẩm "
                f"({len(dem_mon) / tk_kho['tong'] * 100:.1f}%) xuất hiện trong ít nhất "
                "một bộ đã gợi ý cho khách."
            )


# ================= GIỚI THIỆU
elif trang == "gioi_thieu":
    tieu_de(
        "Giới thiệu",
        f"{C.TEN_APP} giúp bạn phối đồ vừa đủ, hài hòa từng chi tiết: từ những món "
        "bạn đang có, cộng thêm vài món gợi ý từ cửa hàng khi cần.",
        "Về chúng tôi"
    )

    _, g_gt, _ = st.columns([0.1, 1, 0.1])
    with g_gt:
        html(
            f'''
            <div class="gt-luoi">
              <div class="gt-the hong"><div class="gt-so">01</div>
                <div class="gt-ten">Hiểu từng món đồ</div>
                <div class="gt-mo-ta">Mô hình thị giác CLIP đọc ảnh để nhận ra loại món, kiểu dáng,
                màu chủ đạo và phong cách. Bạn có thể sửa lại nếu AI đoán sai.</div></div>
              <div class="gt-the xanh"><div class="gt-so">02</div>
                <div class="gt-ten">Chấm độ hợp như stylist</div>
                <div class="gt-mo-ta">Mô hình học sâu chấm độ hợp giữa từng cặp món, kết hợp các quy tắc
                phối màu (tối đa 3 màu, tỉ lệ 60-30-10), họa tiết, form dáng và dịp mặc.</div></div>
              <div class="gt-the vang"><div class="gt-so">03</div>
                <div class="gt-ten">Thử trước khi mặc</div>
                <div class="gt-mo-ta">Mặc thử ảo đưa bộ đồ lên người mẫu có dáng gần với bạn, giữ nguyên
                khuôn mặt, để bạn xem màu và dáng trên người.</div></div>
            </div>
            <div class="gt-khoi">
              <div class="gt-khoi-tieu">Vì sao là <em>Lagom</em>?</div>
              <p>"Lagom" trong tiếng Thụy Điển nghĩa là <b>vừa đủ</b>: không thiếu, không thừa.
              {C.TEN_APP} không khuyến khích mua thêm thật nhiều, mà giúp bạn mặc đẹp hơn với
              những gì đang có, chỉ gợi ý món mới khi nó thật sự làm bộ đồ hoàn chỉnh hơn.</p>
            </div>
            <div class="gt-khoi">
              <div class="gt-khoi-tieu">Lưu ý</div>
              <p>Điểm phối và ảnh mặc thử do AI tạo, mang tính tham khảo. Ảnh món đồ bạn tải lên
              chỉ dùng trong tủ đồ của bạn, trừ khi bạn chọn chia sẻ lên cửa hàng.</p>
              <p class="gt-nho">{getattr(C, "CHAN_TRANG", "")}</p>
            </div>
            '''
        )


# ================= CHÂN TRANG
html(
    f'<div class="chan-trang"><div class="chan-logo">{C.LOGO_HTML}</div>'
    f'<div class="chan-slogan">{C.KHAU_HIEU}</div>'
    f'<small>{getattr(C, "CHAN_TRANG", "")}</small></div>'
)