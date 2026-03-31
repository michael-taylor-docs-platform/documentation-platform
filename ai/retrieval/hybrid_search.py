import json
import numpy as np
from rank_bm25 import BM25Okapi


def build_bm25(chunks):

    corpus = [c["text"].split() for c in chunks]

    bm25 = BM25Okapi(corpus)

    return bm25


def hybrid_search(query, model, index, chunks, bm25, top_k=5):

    query_vector = model.encode([query])

    D, I = index.search(query_vector, top_k * 3)

    vector_scores = {idx: score for idx, score in zip(I[0], D[0])}

    tokenized_query = query.split()

    bm25_scores = bm25.get_scores(tokenized_query)

    combined_scores = {}

    for idx in range(len(chunks)):

        v_score = vector_scores.get(idx, 999)

        k_score = bm25_scores[idx]

        combined = (1 / (1 + v_score)) + (0.5 * k_score)

        combined_scores[idx] = combined

    ranked = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)

    results = [chunks[i] for i, _ in ranked[:top_k]]

    return results