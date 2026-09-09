from pathlib import Path

from rag_engine import LocalVectorStore, build_chunks, ensure_sample_documents, serialize_results

root = Path(__file__).resolve().parent
user_docs = root / "documents"
samples = root / "sample_documents"
ensure_sample_documents(user_docs, samples)
chunks = build_chunks(user_docs)
assert chunks, "sample documents should produce chunks"
assert {chunk.document_name for chunk in chunks} >= {"careshield_life_overview.md", "eldershield_and_support.md"}
store = LocalVectorStore(chunks)
results = store.search("What is ElderShield and where can I check coverage?", top_k=3)
assert results, "retrieval should return results"
assert any("ElderShield" in item["text"] for item in results)
assert all("document_name" in item and "source_excerpt" in item for item in results)
assert "document_name" in serialize_results(results)
print("CarePath RAG smoke tests passed.")
