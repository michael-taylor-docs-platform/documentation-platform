#!/usr/bin/env python3

import os
import sys
import yaml
import difflib
from collections import OrderedDict

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DOCS_DIR = os.path.join(BASE_DIR, "docs")
TAXONOMY_FILE = os.path.join(BASE_DIR, "governance", "taxonomy.yaml")

CANONICAL_ORDER = [
    "title",
    "category",
    "audience",
    "tags",
    "project",
    "layer",
    "status",
    "summary",
]

REQUIRED_FIELDS = set(CANONICAL_ORDER)


# ----------------------------------------
# Utilities
# ----------------------------------------

def load_yaml_ordered(stream):
    """
    Load YAML while preserving key order.
    """
    class OrderedLoader(yaml.SafeLoader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping,
    )

    return yaml.load(stream, OrderedLoader)


def suggest(value, valid_list):
    matches = difflib.get_close_matches(value, valid_list, n=1, cutoff=0.6)
    return matches[0] if matches else None


def load_taxonomy():
    if not os.path.exists(TAXONOMY_FILE):
        print("❌ taxonomy.yaml not found.")
        sys.exit(1)

    with open(TAXONOMY_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def extract_frontmatter(content):
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    return parts[1]


# ----------------------------------------
# Validation
# ----------------------------------------

def validate_file(filepath, taxonomy):
    errors = []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    frontmatter_raw = extract_frontmatter(content)

    if frontmatter_raw is None:
        errors.append("Missing or malformed frontmatter block.")
        return errors

    try:
        metadata = load_yaml_ordered(frontmatter_raw)
    except Exception as e:
        errors.append(f"YAML parsing error: {str(e)}")
        return errors

    # Unknown keys
    for key in metadata.keys():
        if key not in CANONICAL_ORDER:
            errors.append(f"Unknown metadata key: {key}")

    # Missing required fields
    for field in REQUIRED_FIELDS:
        if field not in metadata:
            errors.append(f"Missing required field: {field}")

    # Order validation
    actual_order = list(metadata.keys())
    if actual_order != CANONICAL_ORDER:
        errors.append(
            "Incorrect frontmatter order.\n"
            f"    Expected: {', '.join(CANONICAL_ORDER)}"
        )

    # Type validation
    if "audience" in metadata and not isinstance(metadata["audience"], list):
        errors.append("Field 'audience' must be a list.")

    if "tags" in metadata and not isinstance(metadata["tags"], list):
        errors.append("Field 'tags' must be a list.")

    # Empty value checks
    for key, value in metadata.items():
        if value == "" or value is None:
            errors.append(f"Field '{key}' cannot be empty.")

        if isinstance(value, list) and len(value) == 0:
            errors.append(f"Field '{key}' cannot be an empty list.")

    # Taxonomy validation
    validate_taxonomy(metadata, taxonomy, errors)

    return errors


def validate_taxonomy(metadata, taxonomy, errors):

    taxonomy_map = {
        "category": taxonomy.get("categories", []),
        "project": taxonomy.get("projects", []),
        "layer": taxonomy.get("layers", []),
        "status": taxonomy.get("status", []),
        "audience": taxonomy.get("audience", []),
        "tags": taxonomy.get("tags", []),
    }

    for field, valid_values in taxonomy_map.items():
        if field not in metadata:
            continue

        value = metadata[field]

        if isinstance(value, list):
            for item in value:
                if item not in valid_values:
                    suggestion = suggest(item, valid_values)
                    if suggestion:
                        errors.append(
                            f"Invalid {field}: {item}\n"
                            f"    → Did you mean: {suggestion}?"
                        )
                    else:
                        errors.append(f"Invalid {field}: {item}")
        else:
            if value not in valid_values:
                suggestion = suggest(value, valid_values)
                if suggestion:
                    errors.append(
                        f"Invalid {field}: {value}\n"
                        f"    → Did you mean: {suggestion}?"
                    )
                else:
                    errors.append(f"Invalid {field}: {value}")


# ----------------------------------------
# Main Execution
# ----------------------------------------

def main():
    taxonomy = load_taxonomy()

    all_errors = {}
    total_files = 0

    for root, _, files in os.walk(DOCS_DIR):
        for file in files:
            if file.endswith(".md"):
                total_files += 1
                path = os.path.join(root, file)
                errors = validate_file(path, taxonomy)

                if errors:
                    all_errors[path] = errors

    if all_errors:
        print("=" * 40)
        print("❌ METADATA VALIDATION FAILED")
        print("=" * 40)
        print()

        for filepath, errors in all_errors.items():
            print(f"File: {filepath}")
            print()
            for err in errors:
                print(f"  • {err}")
            print()

        print("-" * 40)
        print(f"{len(all_errors)} file(s) failed validation.")
        print("Build aborted.")
        print("-" * 40)

        sys.exit(1)

    print("✔ Metadata validation passed.")
    print(f"Validated {total_files} file(s).")
    sys.exit(0)


if __name__ == "__main__":
    main()