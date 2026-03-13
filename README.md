# Endo Health Blog Header Generator

This project solves the Endo Health AI-Solutions Engineer challenge: generate a coherent series of 10 blog header images for Endo Health / Endo-App.

## What this submission demonstrates

Instead of creating 10 unrelated prompts, the workflow enforces consistency through a shared brand configuration, a reusable style anchor, category-aware visual angles, a common layout rule, and reproducible prompt logging.

The pipeline:

1. Read 10 blog titles.
2. Map each title to a visual category.
3. Build a structured image prompt from a shared brand system.
4. Generate one header image per title.
5. Save a manifest with every prompt for transparency and reproducibility.
6. Build a contact sheet to inspect the full series at once.

## Why this approach fits the challenge

The job post asks for images that are not random but connected. This implementation handles that explicitly:

- one central style anchor for the entire series
- one palette and mood system shared across all images
- topic-specific variation without losing visual identity
- exportable manifest for auditing prompts and outputs
- optional Streamlit app for the bonus "small hosted app" version

## Files

- `generate_headers.py` – CLI generator
- `app.py` – small Streamlit UI
- `brand_config.json` – reusable brand constraints
- `titles_endo_sample.txt` – sample list of 10 Endo-App blog titles
- `output/` – generated images and manifest

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export OPENAI_API_KEY=...   # or load from .env
python generate_headers.py --titles titles_endo_sample.txt --out output
```

## Run in mock mode

This creates deterministic placeholder images without calling the API. It is useful for reviewing layout and the end-to-end flow.

```bash
python generate_headers.py --titles titles_endo_sample.txt --out output --mock
```

## Run the bonus app

```bash
streamlit run app.py
```

## Notes

- The brand palette is inferred from Endo Health's public website and app presence.
- The generated images intentionally leave negative space for blog title overlays.
- The script avoids sensational or fear-based medical imagery and keeps the tone empathetic and editorial.
