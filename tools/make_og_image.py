"""Generates assets/img/og-image.png — the Open Graph share card (1200x630)."""
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
CREAM = (249, 246, 240)
TERRA = (173, 96, 70)
TERRA_DK = (140, 75, 54)
CHARCOAL = (51, 49, 47)
INDIGO = (102, 123, 130)
SOFT = (119, 113, 106)
SAND = (242, 230, 213)

FONTS = r"C:\Windows\Fonts"

def font(name, size):
    return ImageFont.truetype(rf"{FONTS}\{name}", size)

serif_xl = font("georgiab.ttf", 92)
serif_it = font("georgiai.ttf", 58)
sans_sm = font("arialbd.ttf", 30)
sans_xs = font("arial.ttf", 26)

img = Image.new("RGB", (W, H), CREAM)
d = ImageDraw.Draw(img)

# right panel — terracotta block with arches
d.rectangle([780, 0, W, H], fill=TERRA)
# arch cutouts (cream arches inside the terracotta panel)
for ax, aw, ay, ah in [(830, 90, 120, 210), (960, 120, 90, 260), (1110, 80, 150, 190)]:
    d.rounded_rectangle([ax, ay, ax + aw, ay + ah], radius=aw // 2, fill=TERRA_DK)
    d.rounded_rectangle([ax + 10, ay + 10, ax + aw - 10, ay + ah], radius=(aw - 20) // 2, fill=TERRA)
# dotted path inside middle arch
for y in range(120, 330, 26):
    d.ellipse([1012, y, 1024, y + 12], fill=CREAM)

# left content
d.text((90, 96), "CURATED HERITAGE WALKS · PUNE", font=sans_sm, fill=TERRA)
d.line([90, 156, 420, 156], fill=SAND, width=3)
d.text((90, 190), "The city is more", font=serif_xl, fill=CHARCOAL)
d.text((90, 296), "than its landmarks.", font=serif_xl, fill=CHARCOAL)
d.text((90, 408), "Find the stories between the landmarks.", font=serif_it, fill=TERRA)
d.text((90, 508), "SHEHARNAAMA", font=sans_sm, fill=CHARCOAL)
d.text((90, 548), "#WhatLiesBetween", font=sans_xs, fill=INDIGO)

img.save(r"D:\SHEHARNAAMA_BRANDATHON\assets\img\og-image.png", optimize=True)
print("og-image.png written")