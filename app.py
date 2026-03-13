import json
import os
import subprocess
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
OUTPUT_DIR = ROOT / "output"
TITLES_PATH = ROOT / "titles_runtime.txt"
DEFAULT_TITLES = (ROOT / "titles_endo.txt").read_text(encoding="utf-8")

st.set_page_config(page_title="Endo Header Generator", layout="wide")
st.title("Endo Health Header Generator")
st.caption("Generate a consistent header-image series from a list of blog titles.")

with st.sidebar:
    st.subheader("Run settings")
    mock_mode = st.toggle("Mock mode (no API call)", value=True)
    api_key_input = st.text_input(
        "OpenAI API Key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        placeholder="sk-...",
        help="Overrides the OPENAI_API_KEY environment variable for this run.",
        disabled=mock_mode,
    )
    model = st.text_input("Model", value="gpt-image-1.5")
    quality = st.selectbox("Quality", ["high", "medium", "low"], index=0)
    size = st.selectbox("Size", ["1536x1024", "1024x1024", "1024x1536"], index=0)

st.subheader("Blog titles")
titles_text = st.text_area(
    "One title per line",
    value=DEFAULT_TITLES,
    height=260,
)

col1, col2 = st.columns([1, 3])
with col1:
    run_clicked = st.button("Generate headers", width='stretch')
with col2:
    if not mock_mode and not (api_key_input or os.getenv("OPENAI_API_KEY")):
        st.warning("OPENAI_API_KEY is not set. Enter it in the sidebar or switch to mock mode.")

if run_clicked:
    TITLES_PATH.write_text(titles_text.strip() + "\n", encoding="utf-8")
    OUTPUT_DIR.mkdir(exist_ok=True)

    cmd = [
        sys.executable,
        str(ROOT / "generate_headers.py"),
        "--titles",
        str(TITLES_PATH),
        "--out",
        str(OUTPUT_DIR),
        "--model",
        model,
        "--quality",
        quality,
        "--size",
        size,
    ]
    if mock_mode:
        cmd.append("--mock")

    run_env = os.environ.copy()
    if api_key_input:
        run_env["OPENAI_API_KEY"] = api_key_input

    with st.status("Generating series...", expanded=True) as status:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), env=run_env)
        st.code(result.stdout or "", language="bash")
        if result.returncode != 0:
            st.code(result.stderr or "", language="bash")
            status.update(label="Generation failed", state="error")
        else:
            status.update(label="Generation finished", state="complete")

manifest_path = OUTPUT_DIR / "manifest.json"
contact_sheet_path = OUTPUT_DIR / "contact_sheet.jpg"

if contact_sheet_path.exists():
    st.subheader("Series overview")
    st.image(str(contact_sheet_path), width='stretch')

if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    st.subheader("Generated files")
    cols = st.columns(2)
    for idx, item in enumerate(manifest["items"]):
        image_path = OUTPUT_DIR / item["filename"]
        with cols[idx % 2]:
            st.markdown(f"**{item['title']}**")
            if image_path.exists():
                st.image(str(image_path), width='stretch')
            st.caption(f"Category: {item['category']} · Angle: {item['visual_angle']}")
