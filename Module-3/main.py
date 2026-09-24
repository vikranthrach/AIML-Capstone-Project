from fastapi import FastAPI

from models import AskRequest, AskResponse
from graph import graph


app = FastAPI(
    title="Zepto Support Assistant",
    description="Offline RAG-based Zepto policy assistant",
    version="1.0.0"
)


@app.get("/")
def root():
    return {
        "message": "Zepto Support Assistant is running"
    }


@app.post(
    "/ask",
    response_model=AskResponse
)
def ask(request: AskRequest):

    result = graph.invoke({
        "query": request.query
    })

    return AskResponse(
        answer=result["answer"],
        sources=result["sources"],
        confidence=result["confidence"]
    )
