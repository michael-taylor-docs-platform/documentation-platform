from ai.ingestion.document_loader import load_documents
from ai.ingestion.frontmatter_parser import parse_frontmatter
from ai.ingestion.document_model import Document
from ai.chunking.markdown_chunker import chunk_markdown
from ai.ingestion.graph_builder import load_navigation, build_graph
from ai.ingestion.artifact_writer import write_all


docs = load_documents("docs")

documents = []
chunks = []

for doc_path in docs:

    metadata, content = parse_frontmatter(doc_path)

    doc = Document(
        path=str(doc_path),
        title=metadata.get("title", "Untitled"),
        content=content
    )

    documents.append(doc)

    chunks.extend(chunk_markdown(doc))


nav = load_navigation()

graph = build_graph(nav)

write_all(documents, chunks, graph)

import subprocess
import sys

print("Building FAISS index...")

result = subprocess.run(
    [sys.executable, "scripts/build_semantic_index.py"],
    check=True
)

print("Full rebuild complete (chunks + graph + index)")