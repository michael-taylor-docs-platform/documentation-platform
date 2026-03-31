import json
import faiss
from sentence_transformers import SentenceTransformer

INDEX_FILE = "data/kb_index.faiss"
DOC_FILE = "data/kb_documents.json"

model = SentenceTransformer("all-MiniLM-L6-v2")

index = faiss.read_index(INDEX_FILE)

with open(DOC_FILE, "r", encoding="utf-8") as f:
    documents = json.load(f)


def search(query, k=3):

    query_embedding = model.encode([query])

    distances, indices = index.search(query_embedding, k)

    results = []

    for i in indices[0]:
        results.append(documents[i])

    return results


if __name__ == "__main__":

    query = input("Search: ")

    results = search(query)

    for r in results:
        print("\n---")
        print(r["path"])
        print(r["text"][:500])