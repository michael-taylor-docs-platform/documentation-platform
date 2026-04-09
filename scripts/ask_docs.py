import json
import faiss
import re
import os
import yaml

def classify_query_intent(query: str) -> str:
    q = query.lower()

    identity_keywords = [
        "who is",
        "who's",
        "tell me about",
        "about him",
        "about michael",
        "background",
        "profile",
    ]

    experience_keywords = [
        "experience",
        "worked",
        "companies",
        "career",
        "roles",
        "projects",
        "history",
        "what has he done",
    ]

    technical_keywords = [
        "how",
        "architecture",
        "design",
        "rag",
        "pipeline",
        "implementation",
        "system",
        "metadata",
        "retrieval",
    ]

    for kw in identity_keywords:
        if kw in q:
            return "identity"

    for kw in experience_keywords:
        if kw in q:
            return "experience"

    return "technical"

def load_taxonomy():
    BASE_DIR = os.path.dirname(__file__)
    path = os.path.join(BASE_DIR, "../governance/taxonomy.yaml")

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
    
def load_index():

    BASE_DIR = os.path.dirname(__file__)

    index_path = os.path.join(BASE_DIR, "../data/kb_index.faiss")
    chunks_path = os.path.join(BASE_DIR, "../data/chunks.json")

    index = faiss.read_index(index_path)

    with open(chunks_path, "r", encoding="utf-8") as f:
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

def normalize(text):
    return text.replace("-", " ").replace("_", " ").lower()

def detect_metadata(query: str, taxonomy: dict):
    q = query.lower()

    metadata = {}

    # --- category detection ---
    matched_categories = [
        c for c in taxonomy.get("categories", [])
        if c in q
    ]

    if matched_categories:
        metadata["category"] = matched_categories[0]

    # --- tag detection ---
    matched_tags = []

    q_norm = normalize(query)

    for tag in taxonomy.get("tags", []):
        if normalize(tag) in q_norm:
            matched_tags.append(tag)

    if matched_tags:
        metadata["tags"] = matched_tags

    return metadata

# from sentence_transformers import CrossEncoder

# reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

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

def mmr_select(candidates, query_embedding, k=12, lambda_param=0.9):

    selected = []
    selected_embeddings = []

    # extract chunk embeddings
    import numpy as np

    chunk_embeddings = [
        np.array(c[4]["embedding"])
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

def search(query, client, index, chunks, k=8):

    expanded_query = expand_query(query)

    intent = classify_query_intent(query)

    print("\n--- DETECTED INTENT ---")
    print(intent)

    taxonomy = load_taxonomy()
    metadata_filters = detect_metadata(query, taxonomy)

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=expanded_query
    )

    import numpy as np

    query_embedding = np.array([response.data[0].embedding]).astype("float32")
    faiss.normalize_L2(query_embedding)

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

        # --- metadata boost ---
        metadata_bonus = 0
        chunk_meta = chunk.get("metadata", {})
        category = chunk_meta.get("category")
        tags = chunk_meta.get("tags", [])

        # --- existing metadata matching ---
        for key, value in metadata_filters.items():

            if key == "tags":
                chunk_tags = chunk_meta.get("tags", [])
                matches = sum(1 for t in value if t in chunk_tags)
                metadata_bonus += 0.2 * matches

            else:
                if chunk_meta.get(key) == value:
                    metadata_bonus += 0.3

        # --- NEW: intent-based boosting ---
        if intent == "identity":
            if category == "portfolio":
                metadata_bonus += 0.25

        elif intent == "experience":
            if category == "portfolio":
                metadata_bonus += 0.15

        elif intent == "technical":
            if category == "architecture":
                metadata_bonus += 0.15
            if category == "pipeline":
                metadata_bonus += 0.10

            # tag-level boosts
            if "rag" in tags:
                metadata_bonus += 0.1
            if "semantic-search" in tags:
                metadata_bonus += 0.1

        # cap bonus
        metadata_bonus = min(metadata_bonus, 1.0)

        # --- final score ---
        hybrid_score = (
            0.6 * vector_score +
            0.25 * keyword_norm +
            0.15 * hierarchy_norm +
            metadata_bonus
        )

        candidates.append((hybrid_score, vector_score, keyword, hierarchy, chunk))

    candidates.sort(reverse=True, key=lambda x: x[0])

    # Apply MMR diversity selection
    # candidates = mmr_select(candidates, model, query_embedding, k=12)

    # Semantic reranking
    #candidates = rerank_results(query, candidates)

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
   # Adjust number of docs based on intent
    if intent == "identity":
        top_n_docs = 2
    elif intent == "experience":
        top_n_docs = 3
    else:
        top_n_docs = 3

    top_docs = [doc for _, doc in doc_scores[:top_n_docs]]

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


def build_prompt(question, results, intent):

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

User Intent: {intent}

Guidance:
- identity → summarize the person clearly and concisely
- experience → reference roles, companies, and projects
- technical → explain systems, architecture, and implementation details

You are answering questions about Michael Taylor, the author of this documentation.

Context about Michael Taylor:
- Documentation platform architect and systems designer
- Specializes in RAG systems, AI ingestion pipelines, and enterprise knowledge systems
- All provided documentation reflects his work, projects, and technical capabilities

Instructions:
- When asked about Michael Taylor, assume he is the author of all documentation provided
- Infer his experience, skills, and project complexity from the documentation
- Synthesize information across multiple documents when needed

Rules:
- Base your answer ONLY on the documentation below
- The answer may require combining information from multiple sections
- If the documentation implies the answer, explain it clearly
- Do NOT say "no information available" if the answer can be inferred from the documentation
- Do NOT invent information that is not supported by the documentation

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

    BASE_DIR = os.path.dirname(__file__)
    graph_path = os.path.join(BASE_DIR, "../data/knowledge_graph.json")

    with open(graph_path, "r", encoding="utf-8") as f:
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

#    print("Loading model...")
#    model = SentenceTransformer(MODEL_NAME)

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
        
        intent = classify_query_intent(query)
        
        prompt, sources = build_prompt(query, results, intent)

        answer = ask_llm(prompt, client)

        print("\n----- ANSWER -----\n")
        print(answer)

        print("\nSources:\n")

        for s in sources:
            print(f"• {s}")
    



if __name__ == "__main__":
    main()