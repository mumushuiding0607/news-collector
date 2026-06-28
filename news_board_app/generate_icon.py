from PIL import Image, ImageDraw, ImageFont
import math
import os

# 1024x1024 图标
size = 1024
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

cx, cy = size // 2, size // 2

# --- 深色科技感背景圆 ---
draw.ellipse([80, 80, size-80, size-80], fill=(25, 25, 25, 255))

# --- 金色外圈 ---
draw.ellipse([60, 60, size-60, size-60], outline=(255, 179, 0, 255), width=16)

# --- 刻度线（罗盘风格）---
for i in range(24):
    angle = i * 15 * math.pi / 180
    inner = 430 if i % 3 == 0 else 450
    outer = 480
    x1 = cx + inner * math.sin(angle)
    y1 = cy - inner * math.cos(angle)
    x2 = cx + outer * math.sin(angle)
    y2 = cy - outer * math.cos(angle)
    width = 6 if i % 3 == 0 else 3
    draw.line([x1, y1, x2, y2], fill=(255, 179, 0, 200), width=width)

# --- 风向标箭头 ---
arrow_points = [
    (cx + 20,  cy - 180),   # 顶部
    (cx - 140, cy - 40),    # 左下
    (cx - 60,  cy - 40),    # 左内凹
    (cx - 60,  cy + 140),   # 右下
    (cx + 60,  cy + 60),    # 底部
    (cx + 60,  cy - 60),    # 右上内凹
    (cx + 140, cy - 40),    # 右
]
draw.polygon(arrow_points, fill=(255, 179, 0, 255), outline=(255, 200, 50, 255))

# --- AI 光芒（四角星）---
def draw_star(cx, cy, r, color):
    points = []
    for i in range(8):
        angle = i * math.pi / 4
        points.append((cx + r * math.sin(angle), cy - r * math.cos(angle)))
    draw.polygon(points, fill=color)

draw_star(cx + 300, cy - 300, 30, (255, 179, 0, 255))
draw_star(cx - 300, cy - 300, 22, (255, 179, 0, 200))
draw_star(cx + 320, cy + 260, 22, (255, 179, 0, 200))
draw_star(cx - 320, cy + 280, 18, (255, 179, 0, 180))

# --- 文字 ---
try:
    font_large = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 90)
    font_small = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 55)
except:
    font_large = ImageFont.load_default()
    font_small = font_large

draw.text((cx, cy + 285), "风向标AI", fill=(255, 179, 0, 255), font=font_large, anchor="mm")
draw.text((cx, cy + 365), "WINDGUIDE AI", fill=(200, 200, 200, 200), font=font_small, anchor="mm")

# --- 保存主图标 ---
res_dir = "android/app/src/main/res"
os.makedirs(f"{res_dir}/drawable", exist_ok=True)
img.save(f"{res_dir}/drawable/ic_launcher_foreground.png")
print(f"[OK] ic_launcher_foreground.png")

# --- 生成各 mipmap 尺寸 ---
sizes = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
for name, sz in sizes.items():
    mipmap_dir = f"{res_dir}/mipmap-{name}"
    os.makedirs(mipmap_dir, exist_ok=True)
    resized = img.resize((sz, sz), Image.LANCZOS)
    resized.save(f"{mipmap_dir}/ic_launcher.png")
    print(f"  [OK] mipmap-{name}: {sz}x{sz}")

print("[Done] Icon generation complete!")