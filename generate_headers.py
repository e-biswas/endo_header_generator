"""
Generate a consistent series of blog header images for Endo Health.

Features:
- Reads blog titles from a text file
- Builds a persistent brand-aware prompt scaffold
- Creates one image per title using OpenAI Images API
- Saves prompts, images, and a JSON manifest for reproducibility
- Optional mock mode for local preview without API calls

Usage:
    python generate_headers.py --titles titles_endo_sample.txt --out output
    python generate_headers.py --titles titles.txt --out output --mock
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import textwrap
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from PIL import Image, ImageDraw, ImageFont

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


DEFAULT_MODEL = "gpt-image-1.5"
DEFAULT_SIZE = "1536x1024"
DEFAULT_QUALITY = "high"
DEFAULT_FORMAT = "png"


@dataclass
class PromptBundle:
    title: str
    slug: str
    category: str
    visual_angle: str
    prompt: str
    negative_prompt: str
    filename: str


CATEGORY_RULES = [
    (
        "nutrition",
        ["ernährung", "trans-fettsäuren", "essen", "lebensmittel", "diät", "oatmeal"],
        "editorial still life with healthy ingredients, hands, table scene, soft lifestyle composition",
    ),
    (
        "medication",
        ["wirkstoff", "medikament", "pille", "yselty", "therapie"],
        "clean healthcare editorial still life suggesting treatment and guidance, medication context without readable labels",
    ),
    (
        "diagnostics",
        ["tests", "früherkennung", "diagnose", "ja oder nein", "e-learning"],
        "supportive modern clinical consultation scene with calm patient education feel",
    ),
    (
        "comorbidity",
        ["fibromyalgie", "diabetes", "autoimmun", "me/cfs", "fatigue"],
        "empathetic lifestyle portrait showing fatigue, coping, or self-management in a warm home or care setting",
    ),
    (
        "daily_life",
        ["endotasche", "alltag", "kündigung", "arztbesuche"],
        "organized lifestyle flat lay or everyday scene showing preparedness, calm control, and self-advocacy",
    ),
]


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = (
        value.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value[:80] or "untitled"


def load_titles(path: Path) -> List[str]:
    titles = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not titles:
        raise ValueError("No titles found in the input file.")
    return titles


def load_brand_config(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def detect_category(title: str) -> tuple[str, str]:
    title_l = title.lower()
    for category, keywords, visual_angle in CATEGORY_RULES:
        if any(keyword in title_l for keyword in keywords):
            return category, visual_angle
    return "general", "calm women-centered editorial illustration or photography-inspired healthcare scene"


def build_prompt(title: str, brand: Dict) -> PromptBundle:
    slug = slugify(title)
    category, visual_angle = detect_category(title)

    palette_text = ", ".join([f"{k} {v}" for k, v in brand["palette"].items()])
    principles = ", ".join(brand["visual_principles"])
    rules = "; ".join(brand["prompt_rules"])

    prompt = textwrap.dedent(
        f"""
        Create a website header image for the blog title: "{title}".

        Brand anchor:
        {brand['style_anchor']}

        Required series consistency:
        - Same overall art direction as the rest of the series
        - Palette alignment: {palette_text}
        - Principles: {principles}
        - Composition: {brand['layout']['composition']}
        - Safe zone: {brand['layout']['safe_zone']}
        - Topic angle: {visual_angle}

        Content guidance:
        - Interpret the title metaphorically and editorially, not literally
        - Keep the subject matter medically respectful and emotionally safe
        - Favor hope, clarity, self-efficacy, and trustworthy health communication
        - Suitable for a women's health article header on a premium digital-health website
        - No embedded text
        - No logos or watermarks
        - No collage look
        - No stock-photo cliché expressions
        - Use gentle natural light and a soft pastel color grade
        - Keep enough clean negative space for a future headline overlay
        """
    ).strip()

    negative_prompt = rules

    return PromptBundle(
        title=title,
        slug=slug,
        category=category,
        visual_angle=visual_angle,
        prompt=prompt,
        negative_prompt=negative_prompt,
        filename=f"{slug}.png",
    )


def save_b64_image(b64_data: str, path: Path) -> None:
    raw = base64.b64decode(b64_data)
    path.write_bytes(raw)


def generate_with_openai(bundle: PromptBundle, out_path: Path, model: str, size: str, quality: str, output_format: str) -> None:
    if OpenAI is None:
        raise RuntimeError("openai package is not installed. Run: pip install -r requirements.txt")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Put it in your environment or .env file.")

    client = OpenAI(api_key=api_key)

    response = client.images.generate(
        model=model,
        prompt=f"{bundle.prompt}\n\nAvoid: {bundle.negative_prompt}",
        size=size,
        quality=quality,
        output_format=output_format,
    )

    item = response.data[0]
    if not getattr(item, "b64_json", None):
        raise RuntimeError("The image response did not include b64_json data.")
    save_b64_image(item.b64_json, out_path)


def _load_font(size: int):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def generate_mock(bundle: PromptBundle, out_path: Path, brand: Dict, size: str) -> None:
    width, height = [int(x) for x in size.split("x")]
    img = Image.new("RGB", (width, height), brand["palette"]["cream"])
    draw = ImageDraw.Draw(img)

    # Background bands based on palette for a deterministic, brand-consistent mock.
    colors = [
        brand["palette"]["cream"],
        brand["palette"]["blush"],
        brand["palette"]["lavender"],
        brand["palette"]["teal"],
    ]
    band_w = width // len(colors)
    for i, color in enumerate(colors):
        draw.rectangle((i * band_w, 0, (i + 1) * band_w, height), fill=color)

    # Left focal panel.
    draw.rounded_rectangle((80, 100, 860, 924), radius=64, fill=brand["palette"]["rose"], outline=brand["palette"]["plum"], width=4)
    draw.ellipse((160, 220, 560, 620), fill=brand["palette"]["cream"], outline=brand["palette"]["plum"], width=5)
    draw.rounded_rectangle((420, 300, 760, 560), radius=36, fill=brand["palette"]["lavender"])
    draw.rounded_rectangle((490, 590, 780, 760), radius=36, fill=brand["palette"]["teal"])

    title_font = _load_font(48)
    meta_font = _load_font(28)

    wrapped_title = textwrap.fill(bundle.title, width=28)
    draw.text((945, 180), wrapped_title, font=title_font, fill=brand["palette"]["charcoal"])
    draw.text((945, 530), f"Category: {bundle.category}", font=meta_font, fill=brand["palette"]["plum"])
    draw.text((945, 585), "Mock preview (no API call)", font=meta_font, fill=brand["palette"]["plum"])
    draw.text((945, 640), "Safe zone reserved for headline", font=meta_font, fill=brand["palette"]["plum"])

    img.save(out_path)


def create_contact_sheet(image_paths: List[Path], out_path: Path, thumb_size=(480, 320), columns: int = 2) -> None:
    if not image_paths:
        return

    thumbs: List[Image.Image] = []
    for path in image_paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail(thumb_size)
        canvas = Image.new("RGB", thumb_size, "white")
        x = (thumb_size[0] - img.width) // 2
        y = (thumb_size[1] - img.height) // 2
        canvas.paste(img, (x, y))
        thumbs.append(canvas)

    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new("RGB", (thumb_size[0] * columns, thumb_size[1] * rows), "#ffffff")

    for index, thumb in enumerate(thumbs):
        x = (index % columns) * thumb_size[0]
        y = (index // columns) * thumb_size[1]
        sheet.paste(thumb, (x, y))

    sheet.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate brand-consistent header images for blog titles.")
    parser.add_argument("--titles", type=Path, required=True, help="Path to newline-separated blog titles")
    parser.add_argument("--out", type=Path, default=Path("output"), help="Output directory")
    parser.add_argument("--brand", type=Path, default=Path("brand_config.json"), help="Brand config JSON file")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="OpenAI image model")
    parser.add_argument("--size", default=DEFAULT_SIZE, help="Image size, e.g. 1536x1024")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, help="Image quality")
    parser.add_argument("--format", default=DEFAULT_FORMAT, help="Output format: png, jpeg, webp")
    parser.add_argument("--mock", action="store_true", help="Create deterministic mock images without calling the API")
    args = parser.parse_args()

    if load_dotenv is not None:
        load_dotenv()

    titles = load_titles(args.titles)
    brand = load_brand_config(args.brand)

    args.out.mkdir(parents=True, exist_ok=True)

    bundles: List[PromptBundle] = [build_prompt(title, brand) for title in titles]
    image_paths: List[Path] = []

    for idx, bundle in enumerate(bundles, start=1):
        out_path = args.out / bundle.filename
        print(f"[{idx}/{len(bundles)}] {bundle.title} -> {out_path.name}")

        if args.mock:
            generate_mock(bundle, out_path, brand, args.size)
        else:
            generate_with_openai(bundle, out_path, args.model, args.size, args.quality, args.format)

        image_paths.append(out_path)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "mock" if args.mock else "openai_api",
        "model": args.model,
        "size": args.size,
        "quality": args.quality,
        "output_format": args.format,
        "titles_file": str(args.titles),
        "brand_file": str(args.brand),
        "items": [asdict(bundle) for bundle in bundles],
    }

    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    create_contact_sheet(image_paths, args.out / "contact_sheet.jpg")
    print(f"Done. Manifest: {args.out / 'manifest.json'}")


if __name__ == "__main__":
    main()
