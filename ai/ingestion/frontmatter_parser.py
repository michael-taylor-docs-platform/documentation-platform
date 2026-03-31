import yaml
import re


FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n(.*)$",
    re.DOTALL
)


def parse_frontmatter(file_path):

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    match = FRONTMATTER_PATTERN.match(content)

    if not match:
        return {}, content

    frontmatter_raw = match.group(1)
    body = match.group(2)

    metadata = yaml.safe_load(frontmatter_raw)

    return metadata, body


if __name__ == "__main__":

    example = parse_frontmatter("source/example.md")

    print(example["metadata"])