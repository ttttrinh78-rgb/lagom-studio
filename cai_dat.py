# cai_dat.py — MỌI CHỮ, MÀU, CỠ ẢNH, LUẬT PHỐI ĐỒ… NẰM Ở ĐÂY. Sửa, lưu (Ctrl+S); nhiều mục cần tắt app và chạy lại.

# ================= CHỮ HIỂN THỊ
TEN_APP = "Lagom Studio"
LOGO_HTML = "Lagom <span>Studio</span>"
ICON_APP = "logo.png"
KHAU_HIEU = "Find Your Balance. Define Your Style."
MO_TA_TRANG_CHU = "AI-POWERED FASHION STYLING"
# Menu trên cùng. "Tủ đồ" gồm 3 trang con: Tủ đồ của tôi, Cửa hàng, Bộ đồ đã lưu.
MENU = {"home": "Trang chủ", "phoi": "Phối đồ", "cham": "Chấm điểm", "bo_suu_tap": "Bộ sưu tập",
        "tu_do": "Tủ đồ", "thong_ke": "Thống kê", "gioi_thieu": "Giới thiệu"}
# Icon cạnh từng mục menu (tên icon tra ở fonts.google.com/icons)
MENU_ICON = {"home": ":material/home:", "tu_do": ":material/checkroom:",
             "cua_hang": ":material/storefront:", "phoi": ":material/auto_awesome:",
             "cham": ":material/grading:", "da_luu": ":material/favorite:",
             "bo_suu_tap": ":material/collections:", "thong_ke": ":material/bar_chart:",
             "gioi_thieu": ":material/info:"}
# Thẻ tính năng ở trang chủ: (trang, số, nhãn nhỏ, tiêu đề, mô tả)
TINH_NANG = [
    ("phoi", "01", "Từ một món", "AI-POWERED FASHION STYLING", "Chọn món muốn mặc, Lagom Studio ghép thành outfit theo dịp và gợi ý món còn thiếu."),
    ("tu_do", "02", "Tủ đồ", "Tủ đồ của bạn", "Chụp và lưu những món bạn đang có. Lagom Studio tự nhận ra áo, quần, giày, túi, phụ kiện."),
    ("cham", "03", "Chấm điểm", "Chấm bộ tự phối", "Dựng bộ của riêng bạn, xem điểm hợp nhau, mặc thử trên người mẫu và món nên thay."),
    ("bo_suu_tap", "04", "Cảm hứng", "Bộ sưu tập", "Những bộ đồ dựng sẵn từ cửa hàng theo từng phong cách, phối tiếp chỉ với một lần bấm."),
]
SLOGAN = "FIND YOUR BALANCE. DEFINE YOUR STYLE."
# Ảnh mặc thử mẫu ở trang chủ (đặt trong thư mục dự án; xóa dòng này hoặc xóa ảnh để ẩn khu này)
ANH_MAC_THU_MAU = "ket_qua/thu_do/06da0ecdc7558cfd1e4af81d_mat.jpg"   # ảnh mặc thử ở banner trang chủ
ANH_TRUOC_MAU = "nguoi_mau/dang_manh.jpg"   # ảnh "Trước" ở banner trang chủ
NHAN_DIP = "Bạn phối đồ để"
TEN_NGUOI_MAU = {"dang_manh": "Dáng mảnh", "dang_vua": "Dáng vừa", "dang_day_dan": "Dáng đầy đặn"}
NGUOI_MAU_MAC_DINH = "dang_manh"
CHIP_TRANG_CHU = ["AI phối đồ", "Mặc thử ảo", "Gợi ý mua sắm"]
CHAN_TRANG = "Đồ án môn Trí tuệ nhân tạo trong kinh doanh · 2026"

# ================= NHÃN ĐIỂM
NGUONG_RAT_HOP, NGUONG_KHA_HOP = 0.7, 0.5
NHAN_DIEM = {"rat": ("Rất hợp", "#4f9a72"), "kha": ("Khá hợp", "#d29a3a"), "it": ("Ít hợp", "#c5587b")}

# ================= KÍCH THƯỚC (điểm ảnh)
CO_ANH_THE = 160
CO_ANH_BO = 320
SO_COT_THE = 4
SO_COT_TU_DO = 5
SO_THE_BAN_DAU = 4
SO_BO_MAC_DINH = 3

# ================= BẢNG PHỐI ĐỒ: (x, y, rộng, cao) của từng loại
KICH_THUOC_BANG = (800, 700)
MAU_NEN_BANG = "white"
VI_TRI_BANG = {"Áo": [(30, 20, 300, 300), (350, 20, 220, 300)],
               "Quần/Chân váy": [(30, 330, 300, 350)],
               "Đồ liền thân": [(30, 20, 300, 660)],
               "Giày": [(350, 480, 220, 200)],
               "Phụ kiện": [(590, 20, 190, 200)],
               "Túi xách": [(590, 250, 190, 220)]}

# ================= LOẠI MÓN (AI tự đoán khi tải ảnh)
NHOM = {"Áo": {"icon": "👚", "mo_ta": "a photo of a top, shirt, blouse, t-shirt, sweater, cardigan, jacket or coat"},
        "Quần/Chân váy": {"icon": "👖", "mo_ta": "a photo of trousers, jeans, shorts or a skirt"},
        "Đồ liền thân": {"icon": "👗", "mo_ta": "a photo of a dress or a jumpsuit"},
        "Giày": {"icon": "👠", "mo_ta": "a photo of shoes, sneakers, sandals or heels"},
        "Túi xách": {"icon": "👜", "mo_ta": "a photo of a handbag, shoulder bag, tote bag or backpack"},
        "Phụ kiện": {"icon": "💍", "mo_ta": "a photo of jewelry, a hat, a belt, a scarf or sunglasses"}}

# ================= KIỂU DÁNG (AI tự đoán; người dùng sửa được khi tải ảnh)
KIEU_DANG = {
    "Quần/Chân váy": {
        "vay_ngan": ("Chân váy ngắn", "a mini skirt"),
        "vay_lung": ("Chân váy lửng", "a midi skirt"),
        "vay_dai": ("Chân váy dài", "a long maxi skirt"),
        "quan_short": ("Quần short", "shorts"),
        "quan_lung": ("Quần ống lửng", "three-quarter length cropped pants or culottes ending at mid-calf"),
        "quan_dai": ("Quần dài", "full-length trousers or jeans reaching the ankles"),
    },
    "Đồ liền thân": {
        "vlt_ngan": ("Váy liền ngắn", "a short mini dress ending above the knee"),
        "vlt_dai": ("Váy liền dài", "a long midi or maxi dress ending below the knee"),
        "jumpsuit": ("Jumpsuit, playsuit", "a jumpsuit or playsuit"),
    },
    "Giày": {
        "cao_got": ("Giày cao gót", "high heels or heeled sandals"),
        "sneaker": ("Giày thể thao", "sneakers"),
        "sandal": ("Sandal, dép", "flat sandals"),
        "bup_be": ("Giày búp bê, loafer", "ballet flats or loafers"),
        "bot": ("Bốt", "boots"),
    },
}

# ================= DỊP
DIP = {"Đi học": "a casual comfortable outfit for a female university student going to class",
       "Đi làm": "a smart elegant office outfit for a young working woman",
       "Hẹn hò": "a romantic feminine date night outfit",
       "Dạo phố": "a trendy casual streetwear outfit for the weekend",
       "Dự tiệc": "an elegant glamorous party outfit",
       "Thể thao": "a sporty athletic outfit for the gym"}
TRONG_SO_DIP = 0.15
LUAT_DIP = {   # "uu_tien" = cộng điểm, "tranh" = trừ điểm (mã theo KIEU_DANG)
    "Đi học": {"uu_tien": ["sneaker", "bup_be"], "tranh": ["cao_got"]},
    "Đi làm": {"uu_tien": ["cao_got", "bup_be"], "tranh": ["quan_short", "vay_ngan", "vlt_ngan", "sneaker"]},
    "Hẹn hò": {"uu_tien": ["cao_got", "sandal", "vay_ngan", "vay_lung", "vlt_ngan", "vlt_dai"]},
    "Dạo phố": {"uu_tien": ["sneaker", "sandal"]},
    "Dự tiệc": {"uu_tien": ["cao_got", "vlt_ngan", "vlt_dai"], "tranh": ["quan_short", "sneaker"]},
    "Thể thao": {"uu_tien": ["sneaker", "quan_short", "quan_dai"],
                 "tranh": ["cao_got", "bot", "sandal", "vay_lung", "vay_dai", "vlt_ngan", "vlt_dai"]},
}
PHAT_KIEU_DANG = 0.15

# ================= PHONG CÁCH (nhóm cập nhật theo khảo sát xu hướng)
PHONG_CACH = {
    "Tối giản (clean fit)": "a clean minimalist outfit with neutral colors and simple modern pieces",
    "Hàn Quốc": "a trendy Korean street style outfit for young women",
    "Thanh lịch": "an elegant quiet luxury outfit with classic tailored pieces in beige, cream and navy",
    "Năng động": "a casual streetwear outfit with relaxed oversized pieces and sneakers",
    "Nữ tính": "a soft feminine outfit with pastel colors, ruffles and flowy skirts",
    "Y2K": "a playful Y2K style outfit with bold colors and cropped tops",
}
TRONG_SO_PHONG_CACH = 0.2
TU_DOAN_PHONG_CACH = True
TRONG_SO_DONG_BO = 0.25
TRONG_SO_CAP_YEU = 0.20

# ================= PHỐI THEO MÓN CHÍNH (món đã tick)
TRONG_SO_MAU_THEO = 0.20   # cộng điểm món có màu gần màu món chính (màu trung tính luôn hợp)
TRONG_SO_HOA_TIET = 0.30   # mức áp dụng luật họa tiết
NGUONG_RUOM = 0.5          # món chính có độ "rườm" (họa tiết, chi tiết, nhiều màu) trên ngưỡng này → món đi kèm phải trơn
TRONG_SO_MAU = 0.1         # luật phối màu chung (không quá 2 màu nổi, tránh toàn đồ tối…)

# ================= BỐT
KIEU_NGAN = ["quan_short", "vay_ngan", "vlt_ngan"]
KIEU_DAI_KHONG_BOT = ["vay_dai", "vlt_dai"]   # váy, chân váy dài: không đi bốt
THUONG_BOT_NGAN_OM = 0.06                     # cộng điểm bốt khi phần dưới ngắn và ôm người
PHAT_BOT_KHI_KHONG_NGAN = 0.10                # trừ điểm bốt khi đi với quần dài, váy lửng

# ================= KHO CỬA HÀNG
NGUON = {"tu": "Từ tủ của bạn", "kho": "Gợi ý từ cửa hàng"}
SO_MON_KHO_MOI_NHOM = 25
SO_MON_KHO_TOI_DA = 2
PHAT_MON_KHO = 0.05
SO_GOI_Y_THAY = 3
LOAI_BO_BST, BAN_TOI_THIEU = ["Mama"], 2
LOAI_BO_TU_KHOA = ["tights", "leggings", "sock", "pantyhose", " den", "underwear", "bra", "brief",
                   "swim", "bikini", "pyjama", "night", "robe", "slipper",
                   "bumbag", "belt bag", "waist bag",
                   "platform", "wedge", "flatform", "espadrille", "chunky", "cork"]
LOAI_GIAY_DE_DAY = True
DIEU_CHINH_LOAI = {
    "sneaker": 0.08, "trainer": 0.08, "sandal": 0.06, "ballerina": 0.05, "loafer": 0.04,
    "heel": 0.07, "pump": 0.07, "slingback": 0.06, "court shoe": 0.06,
    "shoulder bag": 0.06, "tote": 0.04, "crossbody": 0.03,
}
MAU_KHONG_UA = [(15, 45), (65, 110), (300, 345)]   # cam, xanh chuối/neon, hồng cánh sen
DO_RUC_TOI_THIEU = 0.55

# ================= XU HƯỚNG (ảnh mẫu trong thư mục xu_huong\ và loi_thoi\)
TRONG_SO_XU_HUONG = 0.3    # ưu tiên món giống ảnh xu hướng
LOAI_BO_LOI_THOI = 0.3     # loại 30% kho giống ảnh lỗi thời nhất

# ================= ĐA DẠNG GỢI Ý
PHAT_DE_TINH = 0.3
PHAT_LAP_LAI = 0.06
NGUONG_GIONG = 0.9
NGUONG_GIONG_PHU_KIEN = 0.82
KHONG_LAP_PHU_KIEN = True
KHONG_LAP_PHAN_THAN = True
SO_NHO_GOI_Y = 60          # nhớ bao nhiêu món đã gợi ý gần đây (để lần sau tránh lặp)
# ---- Độ phong phú khi bấm phối nhiều lần (đặt về 0 cả ba để phối cố định như trước)
DO_NGAU_NHIEN = 0.06       # nhiễu nhỏ cho từng món: bộ gần ngang điểm sẽ luân phiên (0 = tắt)
PHAT_DA_GOI_Y = 0.12       # trừ điểm món đã gợi ý ở các lần trước, mỗi lần xuất hiện (0 = tắt)
NHIET_DO_BOC_KHO = 0.08    # độ "thoáng" khi bốc món cửa hàng: lớn = đa dạng hơn, 0 = luôn lấy top đầu
HE_SO_UNG_VIEN_KHO = 3     # bốc từ nhóm ứng viên gấp bao nhiêu lần SO_MON_KHO_MOI_NHOM

# ================= THỬ ĐỒ ẢO
MAC_PHAN_DUOI = True
MAC_CHAN_VAY = True
GIU_KHUON_MAT = True

# Người mẫu không mang giày khi thử đồ
THU_DO_CHAN_TRAN = True

# Giữ nguyên trang phục gốc tối đa
GIU_CHI_TIET_SAN_PHAM = True

TY_LE_DAU = 0.16
SO_BUOC_THU_DO = 40

# Thành phần mặc định khi không tick ô nào ở hàng "Outfit gồm thêm" (bỏ "ao_khoac" nếu không muốn luôn có áo khoác)
# Thành phần mặc định khi không tick ô nào ở hàng "Outfit gồm" (đầy đủ tất cả)
MAC_DINH_THANH_PHAN = ["ao", "quan", "vay_lien", "ao_khoac", "giay", "tui", "phu_kien"]
NGUONG_LOI_THOI = 0.82         # món cửa hàng giống bất kỳ ảnh loi_thoi nào trên ngưỡng này bị loại (giảm = loại nhiều hơn)
THEM_XU_HUONG_VAO_KHO = True   # đưa ảnh trong xu_huong\ thành sản phẩm cửa hàng, hiện đầu tiên và được ưu tiên
# ---- Chất liệu / họa tiết (AI nhận diện từ ảnh). Mã : mô tả tiếng Anh. Thêm/bớt tùy ý, phải chạy lại app.
CHAT_LIEU_HOA_TIET = {
    "ren": "lace", "jean": "denim", "da": "leather", "len": "knitted wool", "lua": "shiny satin or silk",
    "tweed": "tweed", "theu": "embroidery", "hoa": "a floral print", "ke_soc": "stripes",
    "ca_ro": "a plaid or checked pattern", "cham_bi": "polka dots", "da_thu": "an animal print like leopard or zebra",
    "tron": "plain smooth fabric with no pattern",
}
NGUONG_CUNG_HO = 0.8       # độ giống chất liệu/họa tiết để coi là "cùng họ" (0–1)
# Người mẫu nền theo kiểu dáng phần dưới (thử lần lượt, dùng file đầu tiên có trong nguoi_mau\)
# Người mẫu nền theo kiểu dáng (thử lần lượt, dùng file đầu tiên có trong nguoi_mau\)
NEN_THEO_KIEU = {
    "vay_ngan": ["_vay_ngan", "_vay"],
    "vay_lung": ["_vay"],
    "vay_dai": ["_vay_dai", "_vay"],
    "quan_short": ["_short"],
    "quan_lung": ["_lung"],             # quần ống lửng
    "vlt_ngan": ["_vay_ngan"],          # váy liền ngắn
    "vlt_dai": ["_vay_dai", "_vay"],    # váy liền dài
}
# ---- Học từ bộ đồ đã lưu
TRONG_SO_SO_THICH = 0.3    # mức ưu tiên cặp món giống cặp trong bộ đồ bạn đã lưu
NGUONG_SO_THICH = 0.8      # độ giống (theo ảnh) để coi là "giống món đã lưu" (0–1)
# Thư mục con trong xu_huong\ → loại món
THU_MUC_NHOM = {"ao": "Áo", "quan": "Quần/Chân váy", "chan_vay": "Quần/Chân váy", "vay_lien": "Đồ liền thân",
                "giay": "Giày", "tui": "Túi xách", "phu_kien": "Phụ kiện"}
CHIA_SE_MAC_DINH = True    # ô "Chia sẻ lên cửa hàng" ở trang Tủ đồ được tick sẵn hay không
# ---- Tốc độ xử lý ảnh tải lên
CO_ANH_XU_LY = 768             # thu nhỏ ảnh về tối đa bấy nhiêu điểm ảnh trước khi xử lý
MO_HINH_TACH_NEN = "u2netp"    # "u2netp" (nhanh, nhẹ) | "silueta" (cân bằng) | "u2net" (chậm, kỹ nhất)
# ---- Sửa phân loại kho cửa hàng
TU_SUA_PHAN_LOAI = True    # AI tự chuyển áo/quần/váy liền bị xếp sai loại (theo ảnh)
NGUONG_SUA_LOAI = 0.03     # AI phải chắc hơn bao nhiêu mới sửa (tăng = sửa ít hơn, an toàn hơn)
# ---- Tỷ trọng diện tích mỗi loại món khi tính tỷ lệ màu (quy tắc 3 màu, 60-30-10)
TY_TRONG_DIEN_TICH = {"Áo": 0.35, "Quần/Chân váy": 0.3, "Đồ liền thân": 0.65,
                      "Giày": 0.1, "Túi xách": 0.1, "Phụ kiện": 0.04}