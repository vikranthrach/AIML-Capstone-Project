# Zepto Support Assistant — Module 3

An offline-first, RAG-based customer support assistant service built for Zepto policy resolution using FastAPI, LangGraph, SentenceTransformers, and ChromaDB.

---

## 1. Pipeline Architecture

```
                       +----------------------+
                       | Incoming User Query |
                       +----------+-----------+
                                  |
                                  v
                       +----------------------+
                       |   classify_intent    |
                       +----------+-----------+
                                  |
            +---------------------+---------------------+
            | (policy_question)                         | (general_question)
            v                                           v
+-----------------------+                   +----------------------+
|  retrieve_and_answer  |                   |    direct_answer     |
|  - ChromaDB Vector    |                   |  - Returns fixed     |
|    Search (Top-3)     |                   |    fallback message  |
|  - Generates Answer   |                   +----------+-----------+
+-----------+-----------+                              |
            |                                          |
            +---------------------+--------------------+
                                  |
                                  v
                       +----------------------+
                       |  Pydantic Validated  |
                       |    AskResponse JSON  |
                       +----------------------+
```

### Flow Breakdown

1. **Ingestion & Chunking (`ingest.py`)**:
   - Reads documents from `docs/doc_01.txt` through `docs/doc_08.txt`.
   - Generates normalized dense vector embeddings locally using `all-MiniLM-L6-v2` (`sentence-transformers`).
   - Persists chunk texts and vector embeddings to a local ChromaDB collection (`zepto_policies`) stored at `data/chroma_db`.

2. **Intent Classification Node (`classify_intent` in `graph.py`)**:
   - Analyzes incoming queries.
   - **MOCK Mode (`MOCK_LLM=1`)**: Uses keyword matching (`delivery`, `return`, `refund`, `membership`, `tracking`, `cancel`, `gift card`, `support hours`). Routes query to `policy_question` or `general_question`.

3. **Retrieval & Answer Generation Node (`retrieve_and_answer` in `graph.py`)**:
   - Encodes query locally and performs cosine similarity search via ChromaDB for top 3 matching chunks.
   - **MOCK Mode (`MOCK_LLM=1`)**: Formats an answer using a deterministic string template (`Based on the retrieved context: <top 200 chars>`) and assigns sources and 1.0 confidence.
   - **Real LLM Mode (`MOCK_LLM=0`)**: Formats retrieved context into `PROMPT_TEMPLATE` (`prompts.py`) and queries LLM with automatic structural retries.

4. **Direct Answer Node (`direct_answer` in `graph.py`)**:
   - Handles queries flagged as `general_question`.
   - Returns standard fallback response with empty source lists.

5. **API Layer (`main.py`)**:
   - Exposes a `POST /ask` endpoint running on Uvicorn, returning validated `AskResponse` JSON schema.

---

## 2. Local Setup & Execution

### Prerequisites
```bash
pip install -r requirements.txt
```

### Ingestion
Initialize local vector store:
```bash
python ingest.py
```

### Run FastAPI Server
```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

---

## 3. Recorded Execution Transcripts (`MOCK_LLM=1`)

### Test 1: Policy Retrieval Query (`policy_question`)

**Request**:
```bash
curl -X POST "http://127.0.0.1:7860/ask" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the delivery fee for orders below INR 149?"}'
```

**Response**:
```json
{
  "answer": "Based on the retrieved context: Zepto delivers grocery and household essentials to serviceable pin codes within 10 to 30 minutes of order confirmation, depending on the customer's delivery zone and current order volume. Standard delivery is free on orders over INR 149; orders below this threshold incur a flat INR 25 delivery fee.",
  "sources": [
    "doc_01_chunk_0",
    "doc_03_chunk_0",
    "doc_05_chunk_0"
  ],
  "confidence": 1.0
}
```

---

### Test 2: Unrelated General Query (`general_question`)

**Request**:
```bash
curl -X POST "http://127.0.0.1:7860/ask" \
     -H "Content-Type: application/json" \
     -d '{"query": "What is the capital of India?"}'
```

**Response**:
```json
{
  "answer": "I can only answer questions about Zepto policies right now.",
  "sources": [],
  "confidence": 1.0
}
```

---

## 4. Containerization (Docker)

### Build Image
```bash
docker build -t zepto-support-assistant .
```

### Run Container
```bash
docker run -p 7860:7860 zepto-support-assistant
```
Access endpoint locally at `http://localhost:7860/ask`.
