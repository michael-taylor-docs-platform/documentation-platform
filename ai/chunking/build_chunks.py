import json
from ai.ingestion.document_loader import load_documents
from ai.ingestion.frontmatter_parser import parse_frontmatter
from ai.ingestion.document_model import Document
from ai.chunking.markdown_chunker import chunk_markdown

OUTPUT_FILE = "data/kb_chunks.json"


def build_chunks():

    docs = load_documents("docs")

    all_chunks = []
    skipped = 0

    for doc_path in docs:

        metadata, content = parse_frontmatter(doc_path)

        doc = Document(
            path=str(doc_path),
            title=metadata.get("title", "Untitled"),
            content=content
        )

        chunks = chunk_markdown(doc)

        for chunk in chunks:

            content = chunk.content.strip()

            if len(content) < 40:
                skipped += 1
                continue

            all_chunks.append({
                "document_path": chunk.document_path,
                "title": chunk.title,
                "content": content
            })

    print(f"Total chunks created: {len(all_chunks)}")
    print(f"Skipped empty chunks: {skipped}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2)


if __name__ == "__main__":
    build_chunks()