import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.policy_chunk import PolicyChunk


load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 3072


def retrieve_policy(query: str, k: int = 3) -> list[dict[str, str]]:
    """Return the k policy sections most relevant to the query."""
    if not query.strip():
        raise ValueError("Search query cannot be empty")
    if k < 1:
        raise ValueError("k must be at least 1")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    if not response.embeddings or not response.embeddings[0].values:
        raise RuntimeError("Gemini returned no query embedding")

    query_embedding = response.embeddings[0].values
    if len(query_embedding) != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Expected {EMBEDDING_DIMENSIONS} embedding values; "
            f"got {len(query_embedding)}"
        )

    statement = (
        select(PolicyChunk)
        .order_by(PolicyChunk.embedding.cosine_distance(query_embedding))
        .limit(k)
    )

    with SessionLocal() as session:
        chunks = session.scalars(statement).all()
        return [
            {
                "source": chunk.source,
                "heading": chunk.heading,
                "content": chunk.content,
            }
            for chunk in chunks
        ]
