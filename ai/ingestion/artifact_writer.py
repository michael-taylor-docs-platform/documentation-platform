import json
from pathlib import Path


def write_json(data, output_path):

    output_file = Path(output_path)

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def write_documents(documents):

    data = []

    for doc in documents:

        data.append({
            "path": doc.path,
            "title": doc.title
        })

    write_json(data, "data/documents.json")

def write_chunks(chunks):

    data = []

    for i, chunk in enumerate(chunks):

        data.append({
            "id": f"chunk_{i}",
            "document_path": chunk.document_path,
            "title": chunk.title,
            "content": chunk.content
        })

    write_json(data, "data/chunks.json")

def write_graph(graph):

    write_json(graph, "data/knowledge_graph.json")

def write_all(documents, chunks, graph):

    write_documents(documents)

    write_chunks(chunks)

    write_graph(graph)

    print("Artifacts written to /data directory")

        