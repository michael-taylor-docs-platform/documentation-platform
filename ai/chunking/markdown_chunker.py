from dataclasses import dataclass


@dataclass
class Chunk:
    document_path: str
    title: str
    content: str

import re

HEADER_PATTERN = re.compile(r"^(#{1,6})\s+(.*)", re.MULTILINE)

def chunk_markdown(document):

    text = document.content
    matches = list(HEADER_PATTERN.finditer(text))

    chunks = []

    header_stack = []

    for i, match in enumerate(matches):

        level = len(match.group(1))
        header = match.group(2)

        # Adjust header hierarchy
        header_stack = header_stack[:level-1]
        header_stack.append(header)

        full_title = " > ".join(header_stack)

        start = match.end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        section_text = text[start:end].strip()

        if len(section_text) < 120:
            continue

        chunks.append(
            Chunk(
                document_path=document.path,
                title=full_title,
                content=section_text
            )
        )

    return chunks

if __name__ == "__main__":

    from ai.ingestion.document_loader import load_documents
    from ai.ingestion.frontmatter_parser import parse_frontmatter
    from ai.ingestion.document_model import Document

    docs = load_documents("docs")

    documents = []

    for doc_path in docs:

        metadata, content = parse_frontmatter(doc_path)

        doc = Document(
            path=str(doc_path),
            title=metadata.get("title", "Untitled"),
            content=content
        )

        documents.append(doc)

    total_chunks = 0

    for doc in documents:
        chunks = chunk_markdown(doc)

        print(f"\nDocument: {doc.title}")
        print(f"Chunks: {len(chunks)}")

        total_chunks += len(chunks)

    print(f"\nTotal chunks created: {total_chunks}")