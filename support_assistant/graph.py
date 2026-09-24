import os
import json
from typing import TypedDict
import chromadb
from langgraph.graph import StateGraph, END
from sentence_transformers import SentenceTransformer
from pydantic import ValidationError

from models import AskResponse
from prompts import PROMPT_TEMPLATE

CHROMA_DIR = "data/chroma_db"
COLLECTION_NAME = "zepto_policies"
MODEL_NAME = "all-MiniLM-L6-v2"

# ---------------------------------------------------------
# ChromaDB & Embedding Initialization
# ---------------------------------------------------------
client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})
embedding_model = SentenceTransformer(MODEL_NAME)

class SupportState(TypedDict, total=False):
    query: str
    intent: str
    retrieved_documents: list[str]
    retrieved_ids: list[str]
    answer: str
    sources: list[str]
    confidence: float
    response: dict

def mock_llm_enabled() -> bool:
    return os.getenv("MOCK_LLM", "1") == "1"

# ---------------------------------------------------------
# Node 1: classify_intent
# ---------------------------------------------------------
def classify_intent(state: SupportState):
    query = state["query"].lower()
    keywords = [
        "delivery", "return", "refund", "membership", 
        "tracking", "cancel", "gift card", "support hours"
    ]
    
    if any(keyword in query for keyword in keywords):
        intent = "policy_question"
    else:
        intent = "general_question"

    return {"intent": intent}

# ---------------------------------------------------------
# Node 2: retrieve_and_answer
# ---------------------------------------------------------
def retrieve_and_answer(state: SupportState):
    query = state["query"]
    
    # Retrieval step runs natively in both MOCK and real modes
    query_embedding = embedding_model.encode(query, normalize_embeddings=True).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=3)

    documents = results["documents"][0] if results["documents"] else []
    ids = results["ids"][0] if results["ids"] else []

    if mock_llm_enabled():
        top_chunk = documents[0] if documents else "No relevant context found."
        snippet = top_chunk[:200]
        answer = f"Based on the retrieved context: {snippet}"

        response = AskResponse(answer=answer, sources=ids, confidence=1.0)
        return {
            "retrieved_documents": documents,
            "retrieved_ids": ids,
            "answer": response.answer,
            "sources": response.sources,
            "confidence": response.confidence,
            "response": response.model_dump()
        }

    # Optional MOCK_LLM=0 Path with schema retry logic
    context = "\n\n".join(f"[{chunk_id}]\n{doc}" for chunk_id, doc in zip(ids, documents))
    prompt = PROMPT_TEMPLATE.format(query=query, context=context)

    # Retry loop for structural JSON enforcement (max 2 retries)
    for attempt in range(3):
        try:
            # Placeholder for actual LLM call
            raw_llm_output = '{"answer": "Placeholder", "sources": [], "confidence": 1.0}' 
            data = json.loads(raw_llm_output)
            validated = AskResponse(**data)
            return {
                "retrieved_documents": documents,
                "retrieved_ids": ids,
                "answer": validated.answer,
                "sources": validated.sources,
                "confidence": validated.confidence,
                "response": validated.model_dump()
            }
        except (ValidationError, json.JSONDecodeError):
            if attempt == 2:
                # Fallback after 2 failed retries
                fallback = AskResponse(
                    answer="Error processing policy response.",
                    sources=ids,
                    confidence=0.0
                )
                return {
                    "retrieved_documents": documents,
                    "retrieved_ids": ids,
                    "answer": fallback.answer,
                    "sources": fallback.sources,
                    "confidence": fallback.confidence,
                    "response": fallback.model_dump()
                }

# ---------------------------------------------------------
# Node 3: direct_answer
# ---------------------------------------------------------
def direct_answer(state: SupportState):
    if mock_llm_enabled():
        response = AskResponse(
            answer="I can only answer questions about Zepto policies right now.",
            sources=[],
            confidence=1.0
        )
        return {
            "answer": response.answer,
            "sources": [],
            "confidence": response.confidence,
            "response": response.model_dump()
        }

    # Optional MOCK_LLM=0 path
    response = AskResponse(
        answer="I can only answer questions about Zepto policies right now.",
        sources=[],
        confidence=1.0
    )
    return {
        "answer": response.answer,
        "sources": [],
        "confidence": response.confidence,
        "response": response.model_dump()
    }

def route_by_intent(state: SupportState):
    return "retrieve_and_answer" if state["intent"] == "policy_question" else "direct_answer"

# ---------------------------------------------------------
# Build LangGraph StateGraph
# ---------------------------------------------------------
builder = StateGraph(SupportState)
builder.add_node("classify_intent", classify_intent)
builder.add_node("retrieve_and_answer", retrieve_and_answer)
builder.add_node("direct_answer", direct_answer)

builder.set_entry_point("classify_intent")
builder.add_conditional_edges(
    "classify_intent",
    route_by_intent,
    {
        "retrieve_and_answer": "retrieve_and_answer",
        "direct_answer": "direct_answer"
    }
)

builder.add_edge("retrieve_and_answer", END)
builder.add_edge("direct_answer", END)

graph = builder.compile()
