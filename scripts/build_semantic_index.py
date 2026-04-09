import json
import os
import faiss
from openai import OpenAI
import numpy as np
import time

DATA_DIR = "data"
INDEX_FILE = os.path.join(DATA_DIR, "kb_index.faiss")
DOC_FILE = os.path.join(DATA_DIR, "chunks.json")

client = OpenAI()

with open(DOC_FILE, "r", encoding="utf-8") as f:
    documents = json.load(f)

texts = [chunk["content"] for chunk in documents]

expected_count = len(documents)

if not texts:
    print("ERROR: No chunks found in kb_chunks.json")
    exit()

print(f"Total chunks: {len(texts)}")

print("Creating embeddings via OpenAI...")

embeddings = []

for i, text in enumerate(texts):
    time.sleep(0.01)
    MAX_CHARS = 30000  # safe approximation (~7–8K tokens)

    try:
        safe_text = text[:MAX_CHARS]

        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=safe_text
        )

        embedding = response.data[0].embedding
        embeddings.append(embedding)

    except Exception as e:
        print(f"Error processing chunk {i}: {e}")
        raise e  # <-- DO NOT silently skip

    if (i + 1) % 50 == 0:
        print(f"Processed {i+1}/{len(texts)} chunks")

embeddings = np.array(embeddings).astype("float32")

if len(embeddings) != expected_count:
    print(f"WARNING: Only {len(embeddings)} embeddings created out of {expected_count}")

faiss.normalize_L2(embeddings)

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