from io import BytesIO

import requests
from PIL import Image, ImageDraw, ImageFont


def _safe_font(size: int):
    try:
        return ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", size)
    except Exception:
        return ImageFont.load_default()


def generate_thumbnail(article: dict, allow_image: bool, out_path: str = "data/thumb.jpg") -> str:
    width, height = 1200, 675
    canvas = Image.new("RGB", (width, height), (20, 24, 33))
    draw = ImageDraw.Draw(canvas)

    # only allow person/face image if allow_image=true
    if allow_image and article.get("image_url"):
        try:
            img_bin = requests.get(article["image_url"], timeout=20).content
            src = Image.open(BytesIO(img_bin)).convert("RGB").resize((width, height))
            canvas.paste(src, (0, 0))
            draw.rectangle([(0, 0), (width, height)], fill=(0, 0, 0, 110))
        except Exception:
            pass

    # fallback card (no-face safe card)
    draw.rectangle([(40, 40), (1160, 635)], outline=(90, 130, 220), width=4)
    title = (article.get("title") or "AI活用ケース").replace("\n", " ")[:80]
    topic = article.get("topic") or "AI活用"

    draw.text((80, 140), "AI SUCCESS CASE", fill=(160, 190, 255), font=_safe_font(44))
    draw.text((80, 250), title, fill=(240, 245, 255), font=_safe_font(52))
    draw.text((80, 350), f"テーマ: {topic}", fill=(180, 220, 255), font=_safe_font(36))

    canvas.save(out_path, format="JPEG", quality=90)
    return out_path
