import os
import shutil
from pathlib import Path

SOURCE_DIR = Path("source")
DOCS_DIR = Path("docs")

def ensure_docs_dir():
    DOCS_DIR.mkdir(exist_ok=True)

def copy_markdown(file_path):
    relative_path = file_path.relative_to(SOURCE_DIR)
    destination = DOCS_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(file_path, destination)
    print(f"[MD] Copied {relative_path}")

def stub_dita_conversion(file_path):
    relative_path = file_path.relative_to(SOURCE_DIR)
    output_path = DOCS_DIR / relative_path.with_suffix(".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Temporary stub conversion (real XSLT later)
    converted = f"# Converted from DITA\n\n```\n{content}\n```"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(converted)

    print(f"[DITA] Stub converted {relative_path}")

def process_files():
    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            file_path = Path(root) / file

            if file_path.suffix.lower() == ".md":
                copy_markdown(file_path)

            elif file_path.suffix.lower() == ".dita":
                stub_dita_conversion(file_path)

            else:
                raise Exception(f"Unsupported file type: {file_path}")

if __name__ == "__main__":
    ensure_docs_dir()
    process_files()
    print("Transformation complete.")