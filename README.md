# Endo Health Blog Header Generator

A submission for the Endo Health AI Solutions Engineer challenge. The task: produce a consistent series of 10 blog header images that actually look like they belong together.

## The core idea

The tricky part of this challenge isn't generating one good image — it's getting ten images that share a visual identity while each illustrating a different topic. A naive approach (10 independent prompts) produces 10 unrelated results. So instead of writing prompts from scratch, I built a small brand system that every prompt draws from: a shared style anchor, a fixed palette, layout rules, and per-category visual directions. The prompt for each title is assembled programmatically from those shared components.

The pipeline:

1. Read blog titles from a text file
2. Map each title to a visual category based on keywords
3. Assemble a structured prompt from the brand config + category angle
4. Call the OpenAI Images API once per title
5. Save all images, the full prompts, and a contact sheet for review
6. Write a manifest so every output is traceable back to its exact prompt

## Files

- `generate_headers.py` – CLI generator
- `app.py` – small Streamlit UI
- `brand_config.json` – reusable brand constraints
- `titles_endo_sample.txt` – sample list of 10 Endo-App blog titles
- `output/` – generated images and manifest

## Running it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here
python generate_headers.py --titles titles_endo.txt --out output
```

**Mock mode** (no API call, useful for checking layout and flow):

```bash
python generate_headers.py --titles titles_endo.txt --out output --mock
```

**Streamlit app:**

```bash
streamlit run app.py
```

Live: [eh-header.streamlit.app](https://eh-header.streamlit.app/)

## Known limitations

This is a working prototype, not a production system. A few honest caveats:

**Consistency is prompt-driven, not model-driven.** There's no technical mechanism that forces the model to match previous outputs — the visual coherence depends entirely on the style anchor being specific enough. OpenAI's image API doesn't support style references or seeds that persist across calls, so two runs on the same title can look different.

**Category detection is keyword-based and German-specific.** The routing logic does a simple substring match against a fixed list of German keywords. It's fragile — a title that uses different phrasing, or titles in English, will fall through to a generic category. A classifier or embedding-based approach would be more robust.

**The brand palette is inferred, not sourced.** I derived the color palette from Endo Health's public web presence. It's a reasonable approximation, but without access to an official brand guide, it's a guess.

**No feedback loop.** The pipeline is one-shot. If a generated image is off-brand, the only option is to manually re-run that title. In a real workflow you'd want some kind of review step — even a basic visual similarity check against a reference image.

**No retry logic.** If the API returns an error halfway through a batch, the run fails and you lose partial progress. A real pipeline would checkpoint each image as it's saved.

**The "negative prompt" is just appended text.** OpenAI's image API doesn't have a dedicated negative prompt parameter. The avoidance rules are included in the main prompt as natural language, which is less reliable than true negative conditioning.

**Single output size.** Images are generated at 1536×1024 only. A real blog CMS would need multiple crops (mobile, social sharing, og:image, etc.).
