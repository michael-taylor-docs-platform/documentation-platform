"""
DITA → Markdown Static Site Build Tool

This script converts a structured DITA content repository into a fully
generated Markdown site suitable for MkDocs.

Architecture:
- Traverses the SOURCE_DIR
- If a folder contains a single .ditamap → map-driven assembly
- If no map exists → convert standalone .dita or copy .md
- Output is written deterministically to DOCS_DIR
- DOCS_DIR is treated as a build artifact and is wiped before each run

Assumptions:
- One .ditamap per folder (enforced)
- All map-referenced topics exist in the same folder as the map
- Frontmatter exists only in parent topics
- Nested chunking is not supported (by design)

Author: Michael Taylor
"""

import argparse
from pathlib import Path
import os
import shutil
import xml.etree.ElementTree as ET

DEFAULT_METADATA = {
    "category": "unknown",
    "audience": "unknown",
    "tags": "unknown",
    "project": "documentation-platform",
    "layer": "unknown",
    "status": "draft",
    "summary": "Missing summary",
}

CHUNK_MAP = {}

def clean_docs_directory():
    """
    Remove all existing content in DOCS_DIR.

    DOCS_DIR is treated as a fully generated build artifact.
    This guarantees deterministic output and prevents stale files.
    """
    if DOCS_DIR.exists():
        for item in DOCS_DIR.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

def clean_text(text):
    """
    Normalize whitespace in text nodes.

    Collapses multiple spaces and newlines into a single space.
    """
    if not text:
        return ""
    return " ".join(text.split())

def convert_element(element, base_level=2, section_depth=0):
    """
    Recursively convert a DITA XML element into Markdown.

    Parameters:
    - base_level: starting heading level (e.g., 2 → ##)
    - section_depth: depth offset for nested <section> elements

    Handles:
    - section
    - title
    - p
    - ul / ol
    - pre
    - table
    - codeblock
    - note
    """
    md = ""
    tag = element.tag.split("}")[-1]

    if tag == "section":
        title_element = element.find("./title")

        # If section has a title, render it first
        if title_element is not None:

            md += convert_element(title_element, base_level, section_depth + 1)

            new_depth = section_depth + 1

            for child in element:
                if child is title_element:
                    continue
                md += convert_element(child, base_level, new_depth)

        else:

            for child in element:
                md += convert_element(child, base_level, section_depth)

    elif tag == "title":
        heading_level = base_level + section_depth
        md += "#" * heading_level + f" {clean_text(element.text)}\n\n"

    elif tag == "p":
        md += f"{convert_inline_content(element)}\n\n"

    elif tag == "ul":
        md += convert_list(element, level=section_depth, ordered=False) + "\n"

    elif tag == "ol":
        md += convert_list(element, level=section_depth, ordered=True) + "\n"

    elif tag == "pre":
        code_text = "".join(element.itertext())
        md += "```\n"
        md += code_text.rstrip()
        md += "\n```\n\n"

    elif tag == "table":
        md += convert_table(element)

    elif tag == "codeblock":

        code_text = "".join(element.itertext())

        md += "```\n"
        md += code_text.rstrip()
        md += "\n```\n\n"

    elif tag == "note":

        note_type = element.attrib.get("type", "note").lower()

        label = note_type.capitalize()

        md += f"> **{label}:**\n>\n"

        for child in element:
            content = convert_element(child, base_level, section_depth)
            content = content.replace("\n", "\n> ")
            md += f"> {content.strip()}\n"

        md += "\n"

    else:
        print(f"[WARN] Unsupported DITA element: <{tag}>")

        for child in element:
            md += convert_element(child, base_level, section_depth)

    return md

def convert_entry(entry):
    """
    Convert a <entry> element into Markdown cell text.
    Supports inline formatting and nested elements.
    """

    parts = []

    if entry.text:
        parts.append(entry.text)

    for child in entry:
        tag = child.tag.split("}")[-1]
        text = "".join(child.itertext())

        if tag == "b":
            parts.append(f"**{text}**")

        elif tag == "i":
            parts.append(f"*{text}*")

        elif tag == "code":
            parts.append(f"`{text}`")

        else:
            parts.append(text)

        if child.tail:
            parts.append(child.tail)

    return clean_text("".join(parts))

def convert_inline(element):
    """
    Convert simple inline formatting elements (e.g., <b>).

    Currently supports:
    - <b> → bold
    """
    tag = element.tag.split("}")[-1]

    if tag == "b":
        return f"**{clean_text(''.join(element.itertext()))}**"
    elif tag == "codeph":
        return f"`{clean_text(''.join(element.itertext()))}`"

    return clean_text("".join(element.itertext()))

def convert_inline_content(element):
    """
    Convert inline content inside paragraph-level elements.

    Handles:
    - bold (<b>)
    - italic (<i>)
    - inline code (<code>)
    - mixed text + tails
    - xref
    - link

    """
    parts = []

    if element.text:
        parts.append(element.text)

    for child in element:
        tag = child.tag.split("}")[-1]

        content = "".join(child.itertext())

        if tag == "b":
            parts.append(f"**{content}**")

        elif tag == "i":
            parts.append(f"*{content}*")

        elif tag in ["code", "codeph"]:
            parts.append(f"`{content}`")

        elif tag == "xref":

            href = child.attrib.get("href", "")
            scope = child.attrib.get("scope")
            text = clean_text("".join(child.itertext()))

            if scope != "external":
                href = resolve_dita_link(href)

            if not text:
                text = href

            parts.append(f"[{text}]({href})")

        elif tag == "link":
            href = child.attrib.get("href", "")
            text = clean_text("".join(child.itertext()))

            href = resolve_dita_link(href)

            if not text:
                text = href

            parts.append(f"[{text}]({href})")

        else:
            parts.append(content)

        if child.tail:
            parts.append(child.tail)

    return clean_text("".join(parts))

def convert_list(element, level=0, ordered=False):
    md = ""
    indent = "  " * level

    for i, li in enumerate(element.findall("./li"), 1):
        prefix = f"{i}." if ordered else "-"
        line = ""

        # ✅ Capture direct text inside <li>
        if li.text and li.text.strip():
            line += clean_text(li.text)

        for child in li:
            child_tag = child.tag.split("}")[-1]

            if child_tag == "p":
                line += clean_text("".join(child.itertext()))

            elif child_tag == "ul":
                md += f"{indent}{prefix} {line}\n"
                md += convert_list(child, level + 1, ordered=False)
                line = ""

            elif child_tag == "ol":
                md += f"{indent}{prefix} {line}\n"
                md += convert_list(child, level + 1, ordered=True)
                line = ""

            if child.tail:
                line += clean_text(child.tail)

        if line:
            md += f"{indent}{prefix} {line}\n"

    return md.rstrip() + "\n"

def convert_table(table):
    """
    Convert a DITA <table> into a Markdown table.

    Supports:
    - optional <thead>
    - optional <tbody>
    - nested inline content inside <entry>
    - uneven row lengths
    - tables without headers
    """

    md = ""
    rows = []
    headers = []

    # Find tgroup (standard DITA table structure)
    tgroup = table.find("./tgroup")

    if tgroup is None:
        return ""

    # Extract header row if present
    thead = tgroup.find("./thead")
    if thead is not None:
        header_row = thead.find("./row")
        if header_row is not None:
            headers = [
                convert_entry(entry)
                for entry in header_row.findall("./entry")
            ]

    # Extract body rows
    tbody = tgroup.find("./tbody")
    if tbody is not None:
        body_rows = tbody.findall("./row")
    else:
        body_rows = tgroup.findall("./row")

    for row in body_rows:
        cells = [
            convert_entry(entry)
            for entry in row.findall("./entry")
        ]
        rows.append(cells)

    # If no header but rows exist → promote first row
    if not headers and rows:
        headers = rows.pop(0)

    # Normalize column counts
    max_cols = max(len(headers), *(len(r) for r in rows)) if rows else len(headers)

    headers += [""] * (max_cols - len(headers))

    normalized_rows = []
    for row in rows:
        normalized_rows.append(row + [""] * (max_cols - len(row)))

    # Render Markdown
    md += "| " + " | ".join(headers) + " |\n"
    md += "| " + " | ".join(["---"] * max_cols) + " |\n"

    for row in normalized_rows:
        md += "| " + " | ".join(row) + " |\n"

    md += "\n"

    return md

def copy_markdown(file_path):
    """
    Copy existing Markdown files from SOURCE_DIR to DOCS_DIR
    while preserving relative folder structure.
    """
    relative_path = file_path.relative_to(SOURCE_DIR)
    destination = DOCS_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(file_path, destination)
    print(f"[MD] Copied {relative_path}")

def dita_to_markdown(file_path):
    """
    Convert a standalone DITA topic into Markdown.

    Generates:
    - YAML frontmatter (title + metadata)
    - Body content from <conbody>

    Used for non-map-driven folders.
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    title_element = root.find("./title")
    title = title_element.text.strip() if title_element is not None else "Untitled"

    metadata = extract_metadata(root)
    metadata = normalize_metadata(metadata, title, file_path)
    frontmatter = render_frontmatter(title, metadata)

    md_output = ""

    conbody = root.find("./conbody")
    if conbody is not None:
        for child in conbody:
            md_output += convert_element(child, base_level=2, section_depth=0)

    return frontmatter + md_output

def dita_to_markdown_with_level(file_path, base_level=2, include_frontmatter=True):
    """
    Convert a DITA topic with explicit heading control.

    Used by map processing to:
    - Control heading levels
    - Suppress frontmatter for child topics
    """
    tree = ET.parse(file_path)
    root = tree.getroot()

    md_output = ""

    title_element = root.find("./title")
    title = title_element.text.strip() if title_element is not None else "Untitled"

    # default level for body sections
    child_level = base_level

    # Parent: generate frontmatter only
    if include_frontmatter:
        metadata = extract_metadata(root)
        metadata = normalize_metadata(metadata, title, file_path)
        frontmatter = render_frontmatter(title, metadata)
        md_output += frontmatter
    else:
        # Child topic heading
        child_level = base_level

        anchor = Path(file_path).stem
        md_output += f'<a id="{anchor}"></a>\n'
        md_output += f'{"#" * child_level} {title}\n\n'

    # Render body
    conbody = root.find("./conbody")
    if conbody is not None:
        for child in conbody:
            md_output += convert_element(child, base_level=child_level, section_depth=0)

    return md_output

def extract_metadata(root):
    """
    Extract metadata from <prolog><metadata><data> elements.

    Returns:
        dict of name → value pairs
    """
    metadata = {}

    # Look for <prolog><metadata><data>
    for data in root.findall(".//prolog//data"):
        name = data.attrib.get("name")
        value = data.attrib.get("value")

        if name and value:
            metadata[name] = value

    return metadata

def render_frontmatter(title, metadata):
    """
    Convert metadata dictionary into YAML frontmatter.
    """

    lines = ["---"]
    lines.append(f"title: {yaml_safe_scalar(title)}")

    for key, value in metadata.items():

        if key in ["audience", "tags"]:
            lines.append(f"{key}:")
            items = [item.strip() for item in value.split(",") if item.strip()]
            for item in items:
                lines.append(f"  - {item}")

        else:
            lines.append(f"{key}: {yaml_safe_scalar(value)}")

    lines.append("---\n")

    return "\n".join(lines)

def main():
    """
    CLI entry point.

    Arguments:
        --source  Path to DITA content root
        --docs    Output directory for generated Markdown

    Initializes global directory paths and triggers processing.
    """
    parser = argparse.ArgumentParser(
        description="DITA to Markdown conversion tool"
    )

    parser.add_argument(
        "--source",
        type=str,
        default="source",
        help="Source directory containing DITA content"
    )

    parser.add_argument(
        "--docs",
        type=str,
        default="docs",
        help="Output directory for generated Markdown"
    )

    args = parser.parse_args()

    global SOURCE_DIR
    global DOCS_DIR

    SOURCE_DIR = Path(args.source).resolve()
    DOCS_DIR = Path(args.docs).resolve()

    print(f"Source: {SOURCE_DIR}")
    print(f"Docs:   {DOCS_DIR}")

    process_files()

def normalize_metadata(metadata, title, file_path=None):
    """
    Ensure all required metadata fields exist.

    Missing fields are filled with defaults and logged.
    Returns normalized metadata dictionary.
    """

    normalized = {}
    missing = []

    for key, default in DEFAULT_METADATA.items():
        value = metadata.get(key)

        if not value:
            normalized[key] = default
            missing.append(key)
        else:
            normalized[key] = value.strip()

    if missing:
        location = f" ({file_path})" if file_path else ""
        print(f"[WARN] {title}{location} missing metadata: {', '.join(missing)}")

    return normalized

def process_files():
    """
    Traverse SOURCE_DIR and determine processing strategy per folder.

    Rules:
    - If folder contains one .ditamap → map-driven processing
    - If folder contains more than one .ditamap → error
    - If no map → convert standalone .dita or copy .md
    """
    clean_docs_directory()

    for root, dirs, files in os.walk(SOURCE_DIR):

        root_path = Path(root)

        map_files = [f for f in files if f.endswith(".ditamap")]

        if len(map_files) > 1:
            raise Exception(f"Multiple .ditamap files found in {root_path}")

        if len(map_files) == 1:
            process_map(root_path / map_files[0])
            continue  # Prevent child .dita processing

        # No map in folder → normal processing
        for file in files:
            file_path = root_path / file

            if file_path.suffix.lower() == ".md":
                copy_markdown(file_path)

            elif file_path.suffix.lower() == ".dita":
                stub_dita_conversion(file_path)

            elif file_path.suffix.lower() == ".ditamap":
                continue

            else:
                # Copy asset files (images, JS, SVG, etc.)
                relative_path = file_path.relative_to(SOURCE_DIR)
                destination = DOCS_DIR / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)

                shutil.copy2(file_path, destination)

                print(f"[ASSET] Copied {relative_path}")

def process_map(map_path):
    """
    Process a single .ditamap file.

    Behavior:
    - Generates one Markdown file per top-level topicref
    - If chunk="to-content", merges child topics into parent
    - Output filename is based on parent topic filename
    - Mirrors SOURCE_DIR structure inside DOCS_DIR

    Constraints:
    - All referenced topics must exist in the same folder
    - Only one .ditamap allowed per folder (enforced upstream)
    """
    tree = ET.parse(map_path)
    root = tree.getroot()

    map_dir = map_path.parent

    # Mirror folder structure in docs
    relative_dir = map_dir.relative_to(SOURCE_DIR)
    output_dir = DOCS_DIR / relative_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    for topicref in root.findall("./topicref"):
        href = topicref.attrib.get("href")
        chunk = topicref.attrib.get("chunk")

        if not href:
            continue

        parent_path = map_dir / href

        if not parent_path.exists():
            raise FileNotFoundError(f"Referenced topic not found: {parent_path}")

        # Convert parent (with frontmatter)
        md_output = dita_to_markdown_with_level(
            parent_path,
            base_level=2,
            include_frontmatter=True
        )

        # Merge children if chunk="to-content"
        if chunk == "to-content":

            for child in topicref.findall("./topicref"):

                child_href = child.attrib.get("href")

                if child_href:
                    child_topic = Path(child_href).name
                    parent_topic = Path(href).with_suffix(".md").name
                    CHUNK_MAP[child_topic] = parent_topic

                md_output = process_topicref(
                    child,
                    map_dir,
                    base_level=2,
                    md_output=md_output
                )

        # Output filename based on parent
        output_file = output_dir / Path(href).with_suffix(".md").name

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(md_output)

        print(f"[MAP] Generated {output_file.relative_to(DOCS_DIR)}")

def process_topicref(topicref, map_dir, base_level, md_output):

    href = topicref.attrib.get("href")

    if href:
        topic_path = map_dir / href

        md_output += dita_to_markdown_with_level(
            topic_path,
            base_level=base_level,
            include_frontmatter=False
        )

    for child in topicref.findall("./topicref"):
        md_output = process_topicref(
            child,
            map_dir,
            base_level + 1,
            md_output
        )

    return md_output

def resolve_dita_link(href):
    """
    Resolve DITA topic links, accounting for map chunking.
    """

    if not href:
        return ""

    filename = Path(href).name

    # If topic was chunked into a parent
    if filename in CHUNK_MAP:

        parent_md = CHUNK_MAP[filename]
        anchor = Path(filename).stem

        return f"{parent_md}#{anchor}"

    # Normal conversion
    return href.replace(".dita", ".md")

def stub_dita_conversion(file_path):
    """
    Convert a standalone .dita file (no map context)
    into Markdown with frontmatter.
    """
    relative_path = file_path.relative_to(SOURCE_DIR)
    output_path = DOCS_DIR / relative_path.with_suffix(".md")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    converted = dita_to_markdown(file_path)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(converted)

    print(f"[DITA] Converted {relative_path}")

def yaml_safe_scalar(value):
    if ":" in value or "#" in value:
        return f'"{value}"'
    return value

if __name__ == "__main__":
    main()