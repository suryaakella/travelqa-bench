"""
TravelQA Evaluation Runner

Runs Gemma 4 E2B against the TravelQA benchmark in two modes:
1. Raw — model answers from its own knowledge
2. RAG — model answers with WikiVoyage context retrieval

Usage:
    python run_eval.py              # Run both modes
    python run_eval.py --raw-only   # Raw mode only
    python run_eval.py --rag-only   # RAG mode only
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix SSL cert path on macOS
if os.path.exists("/etc/ssl/cert.pem"):
    os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")

TRAVELQA_DIR = Path(__file__).parent
GEMMA4_DIR = TRAVELQA_DIR.parent
MODELS_DIR = GEMMA4_DIR / "models"
RESULTS_DIR = TRAVELQA_DIR / "results"
BENCHMARK_FILE = TRAVELQA_DIR / "benchmark.json"

MODEL_PATH = str(MODELS_DIR / "gemma-4-e2b-it-4bit")

# Add parent to path for shared utilities
sys_path = str(GEMMA4_DIR)
if sys_path not in sys.path:
    sys.path.insert(0, sys_path)


def load_model():
    """Load Gemma 4 E2B via mlx-vlm."""
    from mlx_vlm import load
    print(f"Loading model from {MODEL_PATH}...")
    model, processor = load(MODEL_PATH)
    print("Model loaded.")
    return model, processor


def generate(model, processor, prompt: str, max_tokens: int = 128) -> tuple[str, float]:
    """Generate a response. Returns (text, tokens_per_second)."""
    from mlx_vlm import generate as mlx_generate
    from mlx_vlm.prompt_utils import apply_chat_template

    formatted = apply_chat_template(processor, config=model.config, prompt=prompt)
    result = mlx_generate(
        model,
        processor,
        formatted,
        max_tokens=max_tokens,
        verbose=False,
    )
    return result.text.strip(), result.generation_tps


def format_mc_prompt(question: dict, context: str = "") -> str:
    """Format a multiple-choice question as a prompt."""
    q_text = question["question"]
    choices = question.get("choices", [])

    prompt = ""
    if context:
        prompt += f"Use the following reference information to help answer the question:\n\n{context}\n\n---\n\n"

    prompt += f"Question: {q_text}\n\n"
    for i, choice in enumerate(choices):
        letter = chr(65 + i)
        prompt += f"{letter}. {choice}\n"
    prompt += "\nAnswer with ONLY the letter (A, B, C, or D)."

    return prompt


def format_exact_prompt(question: dict, context: str = "") -> str:
    """Format an exact-match question as a prompt."""
    q_text = question["question"]

    prompt = ""
    if context:
        prompt += f"Use the following reference information to help answer the question:\n\n{context}\n\n---\n\n"

    prompt += f"Question: {q_text}\n\nAnswer with ONLY the exact value (number, word, or short phrase). No explanation."

    return prompt


def format_keyword_prompt(question: dict, context: str = "") -> str:
    """Format a keyword-match question as a prompt."""
    q_text = question["question"]

    prompt = ""
    if context:
        prompt += f"Use the following reference information to help answer the question:\n\n{context}\n\n---\n\n"

    prompt += f"Question: {q_text}\n\nAnswer concisely in one sentence."

    return prompt


def extract_mc_answer(response: str) -> str | None:
    """Extract multiple-choice letter from response."""
    # Try to find first A-D letter
    response = response.strip()

    # Pattern 1: Just a letter
    if len(response) == 1 and response.upper() in "ABCD":
        return response.upper()

    # Pattern 2: "A." or "(A)" or "A)" or "Answer: A"
    match = re.search(r'\b([A-D])\b', response)
    if match:
        return match.group(1).upper()

    return None  # parse failure


def run_raw_mode(model, processor, questions: list[dict]) -> list[dict]:
    """Run all questions in raw mode (no RAG context)."""
    print("\n=== Raw Mode ===\n")
    results = []
    total = len(questions)

    for i, q in enumerate(questions):
        answer_type = q.get("answer_type", "multiple_choice")

        if answer_type == "multiple_choice":
            prompt = format_mc_prompt(q)
        elif answer_type == "exact_match":
            prompt = format_exact_prompt(q)
        else:
            prompt = format_keyword_prompt(q)

        response, tps = generate(model, processor, prompt, max_tokens=64)

        result = {
            "id": q["id"],
            "category": q["category"],
            "country": q["country"],
            "answer_type": answer_type,
            "response": response.strip(),
            "tps": round(tps, 1),
        }

        if answer_type == "multiple_choice":
            extracted = extract_mc_answer(response)
            result["extracted_answer"] = extracted
            result["parse_failure"] = extracted is None
        else:
            result["extracted_answer"] = response.strip()
            result["parse_failure"] = False

        results.append(result)

        if (i + 1) % 25 == 0:
            print(f"  Progress: {i + 1}/{total}")

    return results


def run_rag_mode(model, processor, questions: list[dict]) -> list[dict]:
    """Run all questions in RAG mode (with WikiVoyage context)."""
    from rag_pipeline import RAGPipeline

    print("\n=== RAG Mode ===\n")
    rag = RAGPipeline()

    # Ensure index exists
    count = rag.build_index()
    if count == 0:
        print("ERROR: RAG index is empty. Run build_benchmark.py first.")
        return []

    results = []
    total = len(questions)

    for i, q in enumerate(questions):
        answer_type = q.get("answer_type", "multiple_choice")

        # Retrieve context
        chunks = rag.retrieve(
            q["question"],
            top_k=5,
            country_filter=q.get("country"),
        )
        context = rag.format_context(chunks)

        if answer_type == "multiple_choice":
            prompt = format_mc_prompt(q, context=context)
        elif answer_type == "exact_match":
            prompt = format_exact_prompt(q, context=context)
        else:
            prompt = format_keyword_prompt(q, context=context)

        response, tps = generate(model, processor, prompt, max_tokens=64)

        result = {
            "id": q["id"],
            "category": q["category"],
            "country": q["country"],
            "answer_type": answer_type,
            "response": response.strip(),
            "tps": round(tps, 1),
            "rag_chunks_used": len(chunks),
            "rag_avg_distance": round(
                sum(c["distance"] for c in chunks) / len(chunks), 3
            ) if chunks else None,
        }

        if answer_type == "multiple_choice":
            extracted = extract_mc_answer(response)
            result["extracted_answer"] = extracted
            result["parse_failure"] = extracted is None
        else:
            result["extracted_answer"] = response.strip()
            result["parse_failure"] = False

        results.append(result)

        if (i + 1) % 25 == 0:
            print(f"  Progress: {i + 1}/{total}")

    return results


def save_results(results: list[dict], filename: str) -> None:
    """Save results to JSON file."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = RESULTS_DIR / filename
    with open(filepath, "w") as f:
        json.dump({
            "model": "gemma-4-e2b-it-4bit",
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(results),
            "results": results,
        }, f, indent=2)
    print(f"Saved {len(results)} results to {filepath}")


def main():
    raw_only = "--raw-only" in sys.argv
    rag_only = "--rag-only" in sys.argv

    # Load benchmark
    if not BENCHMARK_FILE.exists():
        print(f"Benchmark not found: {BENCHMARK_FILE}")
        print("Run build_benchmark.py first.")
        return

    with open(BENCHMARK_FILE) as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} questions from benchmark")

    # Load model
    model, processor = load_model()

    if not rag_only:
        raw_results = run_raw_mode(model, processor, questions)
        save_results(raw_results, "gemma4_e2b_raw.json")

    if not raw_only:
        rag_results = run_rag_mode(model, processor, questions)
        save_results(rag_results, "gemma4_e2b_rag.json")

    # Free model memory
    del model, processor

    print("\nEvaluation complete. Run score.py to analyze results.")


if __name__ == "__main__":
    main()
