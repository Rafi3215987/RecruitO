import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.policy_chunk import PolicyChunk


load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 3072
HEADING_PATTERN = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")


def split_policy_markdown(markdown: str) -> list[tuple[str, str]]:
    """Return non-empty (heading, body) sections from a Markdown document."""
    sections: list[tuple[str, str]] = []
    heading = "General"
    lines: list[str] = []

    for line in markdown.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            body = "\n".join(lines).strip()
            if body:
                sections.append((heading, body))

            heading = match.group(1).strip()
            lines = []
        else:
            lines.append(line)

    body = "\n".join(lines).strip()
    if body:
        sections.append((heading, body))

    return sections


def _make_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    return genai.Client(api_key=api_key)


def _embed_document(client: genai.Client, heading: str, body: str) -> list[float]:
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=f"{heading}\n{body}",
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )

    if not response.embeddings or not response.embeddings[0].values:
        raise RuntimeError("Gemini returned no embedding")

    values = response.embeddings[0].values
    if len(values) != EMBEDDING_DIMENSIONS:
        raise RuntimeError(
            f"Expected {EMBEDDING_DIMENSIONS} embedding values; got {len(values)}"
        )

    return values


def ingest_policy_directory(policy_dir: Path) -> int:
    """Embed all Markdown policies and replace their stored chunks."""
    if not policy_dir.is_dir():
        raise FileNotFoundError(f"Policy directory not found: {policy_dir}")

    client = _make_client()
    records: list[PolicyChunk] = []

    for policy_path in sorted(policy_dir.glob("*.md")):
        markdown = policy_path.read_text(encoding="utf-8")

        for heading, body in split_policy_markdown(markdown):
            embedding = _embed_document(client, heading, body)
            records.append(
                PolicyChunk(
                    source=policy_path.name,
                    heading=heading,
                    content=body,
                    embedding=embedding,
                )
            )

    # Replace each source's old chunks, so rerunning ingestion won't duplicate them.
    sources = {record.source for record in records}
    with SessionLocal() as session:
        for source in sources:
            session.execute(
                delete(PolicyChunk).where(PolicyChunk.source == source)
            )
        session.add_all(records)
        session.commit()

    return len(records)