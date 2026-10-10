"""Generate high-resolution branded QR code for the 30-min sample story."""
from pathlib import Path
import qrcode
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
URL = "https://shubham2025-ai.github.io/SHEHARNAAMA_BRANDATHON/sample-story.html"

qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_M,
    box_size=12,
    border=3,
)
qr.add_data(URL)
qr.make(fit=True)

# Generate crisp PNG
img = qr.make_image(fill_color="#33312F", back_color="#F9F6F0").convert("RGB")
img.save(PROJECT_ROOT / "assets" / "img" / "qr-sample.png")

# Generate crisp SVG with background
matrix = qr.get_matrix()
size = len(matrix)
svg_parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="100%" height="100%" role="img" aria-label="Scan QR Code to open 30-Minute Sample Story">',
    f'  <rect width="{size}" height="{size}" fill="#F9F6F0" rx="2"/>',
    '  <path fill="#33312F" d="'
]

path_cmds = []
for r, row in enumerate(matrix):
    for c, val in enumerate(row):
        if val:
            path_cmds.append(f'M{c},{r}h1v1h-1z')

svg_parts.append(' '.join(path_cmds))
svg_parts.append('"/>')
svg_parts.append('</svg>')

with open(PROJECT_ROOT / "assets" / "img" / "qr-sample.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(svg_parts))

print("QR code SVG and PNG generated successfully for:", URL)
