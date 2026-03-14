"""
Generate a consistent series of blog header images for Endo Health.

Features:
- Reads blog titles from a text file
- Builds a persistent brand-aware prompt scaffold
- Creates one image per title using OpenAI Images API
- Saves prompts, images, and a JSON manifest for reproducibility

Usage:
    python generate_headers.py --titles titles_endo_sample.txt --out output
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
from typing import Any, Dict, List, Optional

from PIL import Image

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


CATEGORIES = {
    "nutrition": "editorial still life with healthy ingredients, hands, table scene, soft lifestyle composition",
    "medication": "clean healthcare editorial still life suggesting treatment and guidance, medication context without readable labels",
    "diagnostics": "supportive modern clinical consultation scene with calm patient education feel",
    "comorbidity": "empathetic lifestyle portrait showing fatigue, coping, or self-management in a warm home or care setting",
    "daily_life": "organized lifestyle flat lay or everyday scene showing preparedness, calm control, and self-advocacy",
    "general": "calm women-centered editorial illustration or photography-inspired healthcare scene",
}

_CLASSIFY_SYSTEM = """
You are a visual category classifier for a women's health blog.
Given a blog title, return a JSON object with two fields:
  "category": one of: nutrition, medication, diagnostics, comorbidity, daily_life, general
  "visual_angle": a single sentence describing the ideal photographic or illustrative approach for a header image
Respond with raw JSON only, no markdown fences.
"""


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


def detect_category(title: str, client: Optional[Any] = None) -> tuple[str, str]:
    """Classify a blog title into a visual category using the LLM.

    Falls back to the 'general' category if the API is unavailable or
    returns an unexpected response.
    """
    if client is None:
        return "general", CATEGORIES["general"]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": title},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
            max_completion_tokens=120,
        )
        raw = response.choices[0].message.content or ""
        data = json.loads(raw)
        category = data.get("category", "general")
        if category not in CATEGORIES:
            category = "general"
        visual_angle = data.get("visual_angle") or CATEGORIES[category]
        return category, visual_angle
    except Exception as exc:
        print(f"[detect_category] warning: classification failed ({exc}), falling back to 'general'", flush=True)
        return "general", CATEGORIES["general"]


def build_prompt(title: str, brand: Dict, client: Optional[Any] = None) -> PromptBundle:
    slug = slugify(title)
    category, visual_angle = detect_category(title, client)

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


def generate_with_openai(bundle: PromptBundle, out_path: Path, client: Any, model: str, size: str, quality: str, output_format: str) -> None:
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
    args = parser.parse_args()

    if load_dotenv is not None:
        load_dotenv()

    titles = load_titles(args.titles)
    brand = load_brand_config(args.brand)

    args.out.mkdir(parents=True, exist_ok=True)

    if OpenAI is None:
        raise RuntimeError("openai package is not installed. Run: pip install -r requirements.txt")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Put it in your environment or .env file.")
    openai_client = OpenAI(api_key=api_key)

    bundles: List[PromptBundle] = [build_prompt(title, brand, openai_client) for title in titles]
    image_paths: List[Path] = []

    for idx, bundle in enumerate(bundles, start=1):
        out_path = args.out / bundle.filename
        print(f"[{idx}/{len(bundles)}] {bundle.title} -> {out_path.name}")

        generate_with_openai(bundle, out_path, openai_client, args.model, args.size, args.quality, args.format)

        image_paths.append(out_path)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
