from pathlib import Path

# directories that should not be indexed
IGNORED_DIRECTORIES = {
    "assets",
    "images",
    "img",
    "css",
    "js"
}


def load_documents(docs_directory: str):
    """
    Discover Markdown documents inside the docs directory.

    Args:
        docs_directory (str): path to the docs folder

    Returns:
        List[Path]: sorted list of markdown file paths
    """

    docs_path = Path(docs_directory)

    markdown_files = []

    for path in docs_path.rglob("*.md"):

        # skip ignored directories
        if any(part in IGNORED_DIRECTORIES for part in path.parts):
            continue

        markdown_files.append(path)

    # deterministic ordering (important for CI builds)
    markdown_files.sort()

    return markdown_files


if __name__ == "__main__":

    docs = load_documents("docs")

    print(f"Found {len(docs)} markdown files\n")

    for doc in docs:
        print(doc)