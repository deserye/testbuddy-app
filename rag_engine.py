from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    import faiss  # type: ignore
except ImportError:  # pragma: no cover
    faiss = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}
EMBEDDING_DIMENSION = 384


@dataclass
class Chunk:
    chunk_id: str
    document_name: str
    page: int | None
    section: str
    text: str
    source_excerpt: str


class LocalVectorStore:
    """Small in-memory vector store for a Streamlit prototype.

    It uses deterministic hashed word/phrase embeddings so the guided RAG flow can
    run without a second paid API. If faiss-cpu is installed, retrieval uses a
    FAISS inner-product index; otherwise it uses the same cosine scores with NumPy.
    """

    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.vectors = np.vstack([hashed_embedding(chunk.text) for chunk in chunks]).astype("float32") if chunks else np.empty((0, EMBEDDING_DIMENSION), dtype="float32")
        self.index = None
        if chunks and faiss is not None:
            self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
            self.index.add(self.vectors)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.chunks:
            return []
        query_vector = hashed_embedding(query).reshape(1, -1).astype("float32")
        limit = min(top_k, len(self.chunks))
        if self.index is not None:
            scores, indices = self.index.search(query_vector, limit)
            ranked = [(int(index), float(score)) for score, index in zip(scores[0], indices[0]) if index >= 0]
        else:
            scores = (self.vectors @ query_vector[0]).tolist()
            ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)[:limit]
        return [{**asdict(self.chunks[index]), "score": round(score, 4)} for index, score in ranked]


def hashed_embedding(text: str) -> np.ndarray:
    vector = np.zeros(EMBEDDING_DIMENSION, dtype="float32")
    tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}", text.lower())
    tokens += [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        position = int.from_bytes(digest[:4], "little") % EMBEDDING_DIMENSION
        sign = 1.0 if digest[4] % 2 else -1.0
        vector[position] += sign
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm else vector


def extract_file(path: Path) -> list[tuple[int | None, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        if PdfReader is None:
            raise RuntimeError("PDF support requires pypdf. Install the requirements.txt dependencies.")
        reader = PdfReader(str(path))
        return [(page_number + 1, page.extract_text() or "") for page_number, page in enumerate(reader.pages)]
    return [(None, path.read_text(encoding="utf-8", errors="ignore"))]


def split_text(text: str, words_per_chunk: int = 180, overlap: int = 35) -> list[str]:
    words = re.findall(r"\S+", text.strip())
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + words_per_chunk)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + 1, end - overlap)
    return chunks


def build_chunks(directory: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    directory.mkdir(parents=True, exist_ok=True)
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        for page, text in extract_file(path):
            for number, chunk_text in enumerate(split_text(text), start=1):
                chunk_id = hashlib.sha1(f"{path.name}:{page}:{number}:{chunk_text}".encode("utf-8")).hexdigest()[:12]
                chunks.append(Chunk(chunk_id, path.name, page, f"Chunk {number}", chunk_text, chunk_text[:320]))
    return chunks


def save_uploaded_file(uploaded_file: Any, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    destination = directory / safe_name
    destination.write_bytes(uploaded_file.getbuffer())
    return destination


def ensure_sample_documents(directory: Path, sample_directory: Path) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    sample_directory.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source in sample_directory.iterdir():
        if source.suffix.lower() in SUPPORTED_EXTENSIONS:
            destination = directory / source.name
            if not destination.exists():
                destination.write_bytes(source.read_bytes())
                copied += 1
    return copied


def serialize_results(results: list[dict[str, Any]]) -> str:
    return json.dumps(results, ensure_ascii=False, indent=2)
