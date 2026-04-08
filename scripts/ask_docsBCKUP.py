import json
import faiss
from sentence_transformers import SentenceTransformer
import re
from openai import OpenAI

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def load_index():

    index = faiss.read_index("data/kb_index.faiss")

    with open("data/chunks.json", "r", encoding="utf-8") as f:
        chunks = json.load(f)

    return index, chunks

def keyword_score(query, text):

    query_terms = re.findall(r"\w+", query.lower())

    score = 0

    for term in query_terms:
        if term in text.lower():
            score += 1

    return score

def hierarchy_score(query, title):

    query_terms = re.findall(r"\w+", query.lower())

    score = 0

    for term in query_terms:
        if term in title.lower():
            score += 4   # titles are more important

    return score

def expand_query(query):

    expansions = {
        "metadata": ["metadata", "schema", "frontmatter"],
        "validation": ["validation", "verification", "checking"],
        "pipeline": ["pipeline", "workflow", "automation"],
        "publish": ["publish", "build", "deploy"],
        "ingestion": ["ingestion", "indexing", "vectorization"]
    }

    query_terms = re.findall(r"\w+", query.lower())

    expanded_terms = set(query_terms)

    for term in query_terms:
        if term in expansions:
            expanded_terms.update(expansions[term])

    return " ".join(expanded_terms)

from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank_results(query, candidates):

    pairs = [
        (query, c[4]["content"])
        for c in candidates
    ]

    scores = reranker.predict(pairs)

    reranked = []

    for score, candidate in zip(scores, candidates):
        hybrid, vector, keyword, hierarchy, chunk = candidate
        reranked.append((score, hybrid, vector, keyword, hierarchy, chunk))

    reranked.sort(reverse=True)

    return [
        (hybrid, vector, keyword, hierarchy, chunk)
        for _, hybrid, vector, keyword, hierarchy, chunk in reranked
    ]

def mmr_select(candidates, model, query_embedding, k=12, lambda_param=0.9):

    import numpy as np

    selected = []
    selected_embeddings = []

    # extract chunk embeddings
    chunk_embeddings = [
        model.encode(c[4]["content"], normalize_embeddings=True)
        for c in candidates
    ]

    remaining = list(range(len(candidates)))

    while len(selected) < min(k, len(candidates)):

        mmr_scores = []

        for i in remaining:

            relevance = candidates[i][0]  # hybrid score

            diversity = 0
            if selected_embeddings:
                sims = [
                    np.dot(chunk_embeddings[i], emb)
                    for emb in selected_embeddings
                ]
                diversity = max(sims)

            mmr = lambda_param * relevance - (1 - lambda_param) * diversity

            mmr_scores.append((mmr, i))

        mmr_scores.sort(reverse=True)

        best = mmr_scores[0][1]

        selected.append(candidates[best])
        selected_embeddings.append(chunk_embeddings[best])

        remaining.remove(best)

    return selected

def search(query, model, index, chunks, k=8):

    expanded_query = expand_query(query)

    query_embedding = model.encode(
        [expanded_query],
        normalize_embeddings=True
    )

    print("Expanded query:", expanded_query)

    distances, indices = index.search(query_embedding, 30)

    print("\n🔎 Searching knowledge base...\n")
    print("----- VECTOR RETRIEVAL RESULTS -----\n")

    # Debug printing only
    for rank, (idx, dist) in enumerate(zip(indices[0], distances[0])):

        if idx >= len(chunks):
            continue

        chunk = chunks[idx]

        print(f"[Vector Rank {rank+1}] Distance: {dist:.4f}")
        print(f"Document: {chunk['document_path']}")
        print(f"Title: {chunk['title']}")
        print(chunk["content"][:300])
        print("-" * 60)

    # Hybrid ranking (runs only once)
    candidates = []

    for idx, dist in zip(indices[0], distances[0]):

        if idx >= len(chunks):
            continue

        chunk = chunks[idx]

        vector_score = max(0, 1 - (dist / 2))

        keyword = keyword_score(
            query,
            chunk["title"] + " " + chunk["content"] + " " + chunk["document_path"]
        )

        hierarchy = hierarchy_score(query, chunk["title"])

        keyword_norm = min(keyword / 5, 1)
        hierarchy_norm = min(hierarchy / 8, 1)

        hybrid_score = (
            0.6 * vector_score +
            0.25 * keyword_norm +
            0.15 * hierarchy_norm
        )

        candidates.append((hybrid_score, vector_score, keyword, hierarchy, chunk))

    candidates.sort(reverse=True, key=lambda x: x[0])

    # Apply MMR diversity selection
    candidates = mmr_select(candidates, model, query_embedding, k=12)

    # Semantic reranking
    candidates = rerank_results(query, candidates)

    print("\n----- AFTER MMR DIVERSITY FILTER -----\n")

    for rank, (hybrid, vector, keyword, hierarchy, chunk) in enumerate(candidates[:10]):
        print(f"MMR Rank {rank+1}")
        print(f"Hybrid Score: {hybrid:.4f}")
        print(f"Document: {chunk['document_path']}")
        print(f"Title: {chunk['title']}")
        print("-" * 50)

    # --- Document-aware retrieval ---

    from collections import defaultdict

    doc_groups = defaultdict(list)

    for hybrid, vector, keyword, hierarchy, chunk in candidates:
        doc_groups[chunk["document_path"]].append((hybrid, vector, keyword, hierarchy, chunk))

    # score documents by best chunk
    doc_scores = []

    for doc, items in doc_groups.items():
        best_score = max(hybrid for hybrid, *_ in items)
        doc_scores.append((best_score, doc))

    doc_scores.sort(reverse=True)

    # select top documents
    top_docs = [doc for _, doc in doc_scores[:3]]

    results = []

    for doc in top_docs:
        items = sorted(doc_groups[doc], reverse=True)
        for hybrid, vector, keyword, hierarchy, chunk in items[:2]:
            results.append((hybrid, vector, keyword, hierarchy, chunk))

    print("\n----- FINAL RANKED CHUNKS -----\n")

    for rank, (hybrid, vector, keyword, hierarchy, chunk) in enumerate(results):

        print(f"Final {rank+1}")
        print(f"Hybrid Score: {hybrid:.4f}")
        print(f"Vector Score: {vector:.4f}")
        print(f"Keyword Score: {keyword:.4f}")
        print(f"Hierarchy Score: {hierarchy:.4f}")
        print(f"Document: {chunk['document_path']}")
        print(f"Title: {chunk['title']}")
        print(chunk["content"][:300])
        print("-" * 60)

    return [chunk for _, _, _, _, chunk in results]


def build_prompt(question, results):

    context = "\n\n".join(
        f"""
    DOCUMENT: {r['document_path']}
    SECTION: {r['title']}

    {r['content']}
    """
        for r in results
    )
    sources = list({r["document_path"] for r in results})

    prompt = f"""
You are an expert documentation assistant.

Use the provided documentation sections to answer the user's question.

Rules:
- Base your answer ONLY on the documentation below.
- The answer may require combining information from multiple sections.
- If the documentation implies the answer, explain it clearly.
- Do NOT invent information that is not supported by the documentation.

Documentation sections:
{context}

User question:
{question}

Answer:
"""

    return prompt, sources

def ask_llm(prompt, client):

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content

def load_graph():

    with open("data/knowledge_graph.json", "r", encoding="utf-8") as f:
        return json.load(f)

def expand_with_graph(results, graph):

    related_paths = set()

    for r in results:

        path = r["document_path"]

        if path in graph:
            neighbors = graph[path]

            for n in neighbors:
                related_paths.add(n)

    return related_paths

def add_graph_chunks(results, related_paths, chunks):

    existing = {r["document_path"] for r in results}

    for chunk in chunks:

        if chunk["document_path"] in related_paths and chunk["document_path"] not in existing:
            results.append(chunk)

            if len(results) > 12:
                break

    return results

def main():

    client = OpenAI()

    print("Loading model...")
    model = SentenceTransformer(MODEL_NAME)

    print("Loading index...")
    index, chunks = load_index()

    print("Loading knowledge graph...")
    graph = load_graph()

    print("Chunks loaded:", len(chunks))
    print("FAISS index size:", index.ntotal)

    while True:

        query = input("\nAsk a question: ")

        results = search(query, model, index, chunks)

        related_paths = expand_with_graph(results, graph)

        results = add_graph_chunks(results, related_paths, chunks)

        prompt, sources = build_prompt(query, results)

        answer = ask_llm(prompt, client)

        print("\n----- ANSWER -----\n")
        print(answer)

        print("\nSources:\n")

        for s in sources:
            print(f"• {s}")
    



if __name__ == "__main__":
    main()