
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# ==========================================
# 1. CẤU HÌNH
# ==========================================
SIZE = 1024
S = 3
W = H = SIZE * S

BACKGROUND = (255, 245, 248)
PINK = (239, 158, 184)
LAVENDER = (160, 157, 207)
PEACH = (255, 193, 166)

# ==========================================
# 2. HÀM TẠO GRADIENT
# ==========================================
def tao_gradient(size, mau1, mau2):
    w, h = size
    img = Image.new("RGB", size)
    pixels = img.load()

    for y in range(h):
        for x in range(w):
            t = x / w * 0.45 + y / h * 0.55
            t = max(0, min(1, t))

            mau = tuple(
                int(mau1[i] * (1 - t) + mau2[i] * t)
                for i in range(3)
            )

            pixels[x, y] = mau

    return img


# ==========================================
# 3. TẠO NỀN
# ==========================================
canvas = Image.new(
    "RGBA",
    (W, H),
    (*BACKGROUND, 255)
)

# ==========================================
# 4. TẠO KHUNG VUÔNG BO GÓC
# ==========================================
icon_size = 680 * S

x = (W - icon_size) // 2
y = (H - icon_size) // 2

# Gradient hồng sang tím
icon_gradient = tao_gradient(
    (icon_size, icon_size),
    PINK,
    LAVENDER
).convert("RGBA")

# Thêm vùng ánh đào ở góc dưới
peach_layer = Image.new(
    "RGBA",
    (icon_size, icon_size),
    (0, 0, 0, 0)
)

peach_draw = ImageDraw.Draw(peach_layer)

peach_draw.ellipse(
    (
        icon_size * 0.35,
        icon_size * 0.55,
        icon_size * 1.1,
        icon_size * 1.3
    ),
    fill=(*PEACH, 75)
)

peach_layer = peach_layer.filter(
    ImageFilter.GaussianBlur(100 * S)
)

icon_gradient = Image.alpha_composite(
    icon_gradient,
    peach_layer
)

# Mask bo góc
mask = Image.new(
    "L",
    (icon_size, icon_size),
    0
)

mask_draw = ImageDraw.Draw(mask)

mask_draw.rounded_rectangle(
    (0, 0, icon_size - 1, icon_size - 1),
    radius=145 * S,
    fill=255
)

canvas.paste(
    icon_gradient,
    (x, y),
    mask
)

# ==========================================
# 5. TÌM VÀ KHAI BÁO FONT CHỮ
# ==========================================
font_paths = [
    r"C:\Windows\Fonts\Bodoni.ttf",
    r"C:\Windows\Fonts\georgia.ttf",
    r"C:\Windows\Fonts\times.ttf",
    r"C:\Windows\Fonts\GARA.TTF",
    r"C:\Windows\Fonts\cambria.ttc"
]

font_path = next(
    (p for p in font_paths if os.path.exists(p)),
    None
)

if font_path is None:
    raise FileNotFoundError(
        "Không tìm thấy font chữ. Hãy kiểm tra font Georgia hoặc Bodoni."
    )

font = ImageFont.truetype(
    font_path,
    490 * S
)

print("Font đang sử dụng:", font_path)

# ==========================================
# 6. TẠO CHỮ L VỚI GRADIENT
# ==========================================
letter = "L"

bbox = font.getbbox(letter)

letter_w = bbox[2] - bbox[0]
letter_h = bbox[3] - bbox[1]

# Căn giữa chữ
letter_x = (W - letter_w) // 2 - bbox[0] - 15 * S
letter_y = (H - letter_h) // 2 - bbox[1] + 10 * S

# ------------------------------------------
# Bóng đổ chữ
# ------------------------------------------
shadow = Image.new(
    "RGBA",
    (W, H),
    (0, 0, 0, 0)
)

shadow_draw = ImageDraw.Draw(shadow)

shadow_draw.text(
    (letter_x + 4 * S, letter_y + 9 * S),
    letter,
    font=font,
    fill=(105, 75, 120, 85)
)

shadow = shadow.filter(
    ImageFilter.GaussianBlur(9 * S)
)

canvas = Image.alpha_composite(
    canvas,
    shadow
)

# ------------------------------------------
# Mặt nạ chữ L
# ------------------------------------------
letter_mask = Image.new(
    "L",
    (W, H),
    0
)

mask_draw = ImageDraw.Draw(letter_mask)

mask_draw.text(
    (letter_x, letter_y),
    letter,
    font=font,
    fill=255
)

# ------------------------------------------
# Gradient màu ngọc trai
# ------------------------------------------
letter_gradient = Image.new(
    "RGBA",
    (W, H)
)

pixels = letter_gradient.load()

color_top = (255, 255, 255)
color_middle = (250, 226, 239)
color_bottom = (211, 195, 235)

for py in range(H):
    t = py / H

    if t < 0.5:
        k = t * 2

        color = tuple(
            int(
                color_top[i] * (1 - k)
                + color_middle[i] * k
            )
            for i in range(3)
        )

    else:
        k = (t - 0.5) * 2

        color = tuple(
            int(
                color_middle[i] * (1 - k)
                + color_bottom[i] * k
            )
            for i in range(3)
        )

    for px in range(W):
        pixels[px, py] = (*color, 255)

# Chỉ hiển thị màu bên trong chữ
letter_gradient.putalpha(letter_mask)

canvas = Image.alpha_composite(
    canvas,
    letter_gradient
)

# ==========================================
# 7. HIỆU ỨNG ÁNH SÁNG TRÊN CHỮ
# ==========================================
highlight = Image.new(
    "RGBA",
    (W, H),
    (0, 0, 0, 0)
)

highlight_draw = ImageDraw.Draw(highlight)

highlight_draw.text(
    (letter_x - 1 * S, letter_y - 2 * S),
    letter,
    font=font,
    fill=(255, 255, 255, 35)
)

highlight = Image.composite(
    highlight,
    Image.new("RGBA", (W, H), (0, 0, 0, 0)),
    letter_mask
)

canvas = Image.alpha_composite(
    canvas,
    highlight
)

# ==========================================
# 8. HÀM VẼ HỌA TIẾT ÁNH SÁNG
# ==========================================
def ve_sao(draw, cx, cy, radius, alpha=255):
    points = [
        (cx, cy - radius),
        (cx + radius * 0.16, cy - radius * 0.16),
        (cx + radius, cy),
        (cx + radius * 0.16, cy + radius * 0.16),
        (cx, cy + radius),
        (cx - radius * 0.16, cy + radius * 0.16),
        (cx - radius, cy),
        (cx - radius * 0.16, cy - radius * 0.16)
    ]

    draw.polygon(
        points,
        fill=(255, 255, 255, alpha)
    )


# ==========================================
# 9. TẠO QUẦNG SÁNG CHO NGÔI SAO
# ==========================================
glow = Image.new(
    "RGBA",
    (W, H),
    (0, 0, 0, 0)
)

glow_draw = ImageDraw.Draw(glow)

glow_draw.ellipse(
    (
        605 * S,
        255 * S,
        715 * S,
        365 * S
    ),
    fill=(255, 255, 255, 100)
)

glow_draw.ellipse(
    (
        720 * S,
        455 * S,
        770 * S,
        515 * S
    ),
    fill=(255, 255, 255, 90)
)

glow = glow.filter(
    ImageFilter.GaussianBlur(28 * S)
)

canvas = Image.alpha_composite(
    canvas,
    glow
)

# ==========================================
# 10. VẼ NGÔI SAO TRẮNG
# ==========================================
sparkles = Image.new(
    "RGBA",
    (W, H),
    (0, 0, 0, 0)
)

sparkle_draw = ImageDraw.Draw(sparkles)

# Sao lớn phía trên bên phải
ve_sao(
    sparkle_draw,
    660 * S,
    310 * S,
    55 * S
)

# Sao nhỏ phía dưới
ve_sao(
    sparkle_draw,
    745 * S,
    485 * S,
    23 * S
)

canvas = Image.alpha_composite(
    canvas,
    sparkles
)

# ==========================================
# 11. XUẤT ẢNH
# ==========================================
canvas = canvas.convert("RGB")

canvas = canvas.resize(
    (SIZE, SIZE),
    Image.Resampling.LANCZOS
)

canvas.save(
    "logo_lagom_studio.png"
)

print("ĐÃ TẠO LOGO THÀNH CÔNG!")
print("Tên ảnh: logo.png")

canvas.show()
