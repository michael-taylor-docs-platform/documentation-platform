import json
import os
import faiss
from sentence_transformers import SentenceTransformer

DATA_DIR = "data"
INDEX_FILE = os.path.join(DATA_DIR, "kb_index.faiss")
DOC_FILE = os.path.join(DATA_DIR, "chunks.json")

print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")

with open(DOC_FILE, "r", encoding="utf-8") as f:
    documents = json.load(f)

texts = [chunk["content"] for chunk in documents]

expected_count = len(documents)

if not texts:
    print("ERROR: No chunks found in kb_chunks.json")
    exit()

print(f"Total chunks: {len(texts)}")

print("Creating embeddings...")
embeddings = model.encode(
    texts,
    batch_size=64,
    show_progress_bar=True,
    normalize_embeddings=True
)

dimension = embeddings.shape[1]

index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

actual_count = index.ntotal

print(f"Validating index... ({actual_count} vectors vs {expected_count} chunks)")

if actual_count != expected_count:
    print("ERROR: FAISS index size does not match chunk count!")
    exit(1)

print("Index validation passed.")

print("Saving index...")

os.makedirs(DATA_DIR, exist_ok=True)

faiss.write_index(index, INDEX_FILE)

print("Semantic index complete.")