from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


DOCS_DIR = Path("docs")

CHROMA_DIR = "data/chroma_db"
COLLECTION_NAME = "zepto_policies"

MODEL_NAME = "all-MiniLM-L6-v2"


def load_documents():
    documents = []
    ids = []
    metadatas = []

    for file_path in sorted(DOCS_DIR.glob("*.txt")):
        text = file_path.read_text(encoding="utf-8").strip()

        document_id = file_path.stem
        chunk_id = f"{document_id}_chunk_0"

        documents.append(text)
        ids.append(chunk_id)

        metadatas.append({
            "document_id": document_id,
            "chunk_id": chunk_id,
            "source": file_path.name
        })

    return documents, ids, metadatas


def create_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    return collection


def ingest():
    documents, ids, metadatas = load_documents()

    model = SentenceTransformer(MODEL_NAME)

    embeddings = model.encode(
        documents,
        normalize_embeddings=True
    ).tolist()

    collection = create_collection()

    collection.upsert(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )

    print(f"Loaded {len(documents)} documents.")
    print(f"Stored {len(embeddings)} embeddings in ChromaDB.")


if __name__ == "__main__":
    ingest()
