from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ask_docs import (
    load_index,
    load_graph,
    search,
    expand_with_graph,
    add_graph_chunks,
    build_prompt,
    classify_query_intent
)

from openai import OpenAI

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

index = None
chunks = None
graph = None
client = None

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
def chat(req: ChatRequest):

    global model, index, chunks, graph, client

    if index is None:
        print("Loading index + graph...")
        index, chunks = load_index()
        graph = load_graph()
        client = OpenAI()
        print("Loaded.")

    query = req.message

    results = search(query, client, index, chunks)

    related_paths = expand_with_graph(results, graph)
    results = add_graph_chunks(results, related_paths, chunks)

    # --- NEW: classify intent ---
    intent = classify_query_intent(query)

    # --- pass intent into prompt ---
    prompt, sources = build_prompt(query, results, intent)

    print(f"\n[API] Query: {query}")
    print(f"[API] Intent: {intent}")

    return StreamingResponse(
        stream_llm(prompt, client),
        media_type="text/plain"
    )

def stream_llm(prompt, client):

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        stream=True
    )

    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

import os

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 10000))

    uvicorn.run(app, host="0.0.0.0", port=port)