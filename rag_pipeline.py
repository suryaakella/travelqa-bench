"""
RAG Pipeline for TravelQA

Uses TF-IDF (scikit-learn) for retrieval — no model download needed.
Augments LLM queries with relevant WikiVoyage context chunks.

Usage:
    from rag_pipeline import RAGPipeline
    rag = RAGPipeline()
    rag.build_index()  # One-time indexing
    chunks = rag.retrieve("What is the emergency number in Japan?", top_k=5)
"""

import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

TRAVELQA_DIR = Path(__file__).parent
SOURCES_DIR = TRAVELQA_DIR / "sources" / "wikivoyage"
INDEX_FILE = TRAVELQA_DIR / "sources" / "tfidf_index.pkl"

# Chunking parameters
CHUNK_SIZE = 500  # tokens (approx words)
CHUNK_OVERLAP = 50


def chunk_text(text: str, country: str, section: str,
               chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Split text into overlapping chunks at paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_size = 0

    for para in paragraphs:
        para_words = len(para.split())

        if current_size + para_words > chunk_size and current_chunk:
            chunk_text_str = "\n\n".join(current_chunk)
            chunks.append({
                "text": chunk_text_str,
                "country": country,
                "section": section,
                "word_count": current_size,
            })

            # Overlap: keep last paragraph(s) up to overlap words
            overlap_paras = []
            overlap_size = 0
            for p in reversed(current_chunk):
                p_words = len(p.split())
                if overlap_size + p_words > overlap:
                    break
                overlap_paras.insert(0, p)
                overlap_size += p_words

            current_chunk = overlap_paras
            current_size = overlap_size

        current_chunk.append(para)
        current_size += para_words

    # Don't forget last chunk
    if current_chunk:
        chunk_text_str = "\n\n".join(current_chunk)
        chunks.append({
            "text": chunk_text_str,
            "country": country,
            "section": section,
            "word_count": current_size,
        })

    return chunks


def load_all_chunks() -> list[dict]:
    """Load and chunk all cached WikiVoyage data."""
    all_chunks = []

    for cache_file in sorted(SOURCES_DIR.glob("*.json")):
        with open(cache_file) as f:
            data = json.load(f)

        country = data["country"]
        for section_name, section_text in data.get("sections", {}).items():
            if len(section_text.split()) < 20:
                continue
            new_chunks = chunk_text(section_text, country, section_name)
            all_chunks.extend(new_chunks)

    return all_chunks


class RAGPipeline:
    """TF-IDF based retrieval pipeline. No external model downloads needed."""

    def __init__(self):
        self._vectorizer = None
        self._tfidf_matrix = None
        self._chunks = None
        self._loaded = False

    def build_index(self, force: bool = False) -> int:
        """Build TF-IDF index from WikiVoyage chunks. Returns chunk count."""
        # Try loading from cache
        if not force and INDEX_FILE.exists():
            self._load_index()
            if self._chunks:
                print(f"Index loaded from cache: {len(self._chunks)} chunks")
                return len(self._chunks)

        chunks = load_all_chunks()
        if not chunks:
            print("No chunks to index. Run build_benchmark.py --scrape-only first.")
            return 0

        print(f"Building TF-IDF index for {len(chunks)} chunks...")

        self._chunks = chunks
        texts = [c["text"] for c in chunks]

        self._vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self._tfidf_matrix = self._vectorizer.fit_transform(texts)
        self._loaded = True

        # Save index to disk
        self._save_index()

        print(f"Index built: {len(chunks)} chunks, {self._tfidf_matrix.shape[1]} features")
        return len(chunks)

    def _save_index(self):
        """Persist index to disk."""
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(INDEX_FILE, "wb") as f:
            pickle.dump({
                "vectorizer": self._vectorizer,
                "matrix": self._tfidf_matrix,
                "chunks": self._chunks,
            }, f)

    def _load_index(self):
        """Load index from disk."""
        try:
            with open(INDEX_FILE, "rb") as f:
                data = pickle.load(f)
            self._vectorizer = data["vectorizer"]
            self._tfidf_matrix = data["matrix"]
            self._chunks = data["chunks"]
            self._loaded = True
        except Exception as e:
            print(f"Failed to load index: {e}")
            self._loaded = False

    def retrieve(self, query: str, top_k: int = 5,
                 country_filter: str | None = None) -> list[dict]:
        """Retrieve top-k relevant chunks for a query."""
        if not self._loaded:
            self.build_index()

        query_vec = self._vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        # Apply country filter if specified
        if country_filter:
            for i, chunk in enumerate(self._chunks):
                if chunk["country"] != country_filter:
                    similarities[i] = -1

        # Get top-k indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if similarities[idx] <= 0:
                continue
            chunk = self._chunks[idx]
            results.append({
                "text": chunk["text"],
                "country": chunk["country"],
                "section": chunk["section"],
                "distance": 1.0 - float(similarities[idx]),  # Convert similarity to distance
            })

        return results

    def format_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks as context string for LLM prompt."""
        if not chunks:
            return ""

        parts = []
        for chunk in chunks:
            parts.append(
                f"[{chunk['country']} - {chunk['section']}]\n{chunk['text']}"
            )
        return "\n\n---\n\n".join(parts)


def main():
    """Build the RAG index from cached WikiVoyage data."""
    print("=== Building RAG Index ===\n")
    rag = RAGPipeline()
    count = rag.build_index(force=True)

    if count > 0:
        # Test retrieval
        print("\n=== Testing Retrieval ===\n")
        test_queries = [
            "What is the emergency number in Japan?",
            "Is tap water safe to drink in India?",
            "What scams should I watch out for in Thailand?",
            "What voltage and plug type is used in Germany?",
            "What are cultural norms for visiting temples in Indonesia?",
        ]
        for query in test_queries:
            chunks = rag.retrieve(query, top_k=3)
            print(f"Q: {query}")
            for c in chunks:
                print(f"  -> [{c['country']} / {c['section']}] (dist={c['distance']:.3f})")
                print(f"     {c['text'][:100]}...")
            print()


if __name__ == "__main__":
    main()
