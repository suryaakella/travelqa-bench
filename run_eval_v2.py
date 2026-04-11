"""Quick evaluation of benchmark_v2.json (60 offline-use-case questions) against Gemma 4 E2B."""

import json
import os
import re
import time
from pathlib import Path
from collections import Counter

# Fix SSL
if os.path.exists("/etc/ssl/cert.pem"):
    os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")

TRAVELQA_DIR = Path(__file__).parent
MODEL_PATH = str(TRAVELQA_DIR.parent / "models" / "gemma-4-e2b-it-4bit")
BENCHMARK_FILE = TRAVELQA_DIR / "benchmark_v2.json"


def main():
    print("=== Benchmark V2: Offline Use Cases (60 questions) ===\n")

    # Load benchmark
    with open(BENCHMARK_FILE) as f:
        questions = json.load(f)
    print(f"Loaded {len(questions)} questions\n")

    # Load model
    print("Loading model...", flush=True)
    t0 = time.time()
    from mlx_vlm import load, generate as mlx_generate
    from mlx_vlm.prompt_utils import apply_chat_template
    model, processor = load(MODEL_PATH)
    print(f"Model loaded in {time.time()-t0:.1f}s\n", flush=True)

    correct = 0
    total = len(questions)
    results = []

    for i, q in enumerate(questions):
        qid = q["id"]
        cat = q["category"]
        diff = q["difficulty"]
        at = q["answer_type"]

        # Build prompt
        if at == "keyword_match":
            prompt = f"Question: {q['question']}\n\nAnswer concisely in one or two sentences."
        elif at == "exact_match":
            prompt = f"Question: {q['question']}\n\nAnswer with ONLY the exact value. No explanation."
        elif at == "multiple_choice":
            prompt = f"Question: {q['question']}\n\n"
            for j, c in enumerate(q.get("choices", [])):
                prompt += f"{chr(65+j)}. {c}\n"
            prompt += "\nAnswer with ONLY the letter (A, B, C, or D)."
        else:
            prompt = f"Question: {q['question']}\n\nAnswer concisely."

        # Generate
        formatted = apply_chat_template(processor, config=model.config, prompt=prompt)
        result = mlx_generate(model, processor, formatted, max_tokens=128, verbose=False)
        response = result.text.strip()

        # Score
        is_correct = False
        if at == "keyword_match":
            resp_lower = response.lower()
            keywords = q.get("keywords", [])
            matched = [kw for kw in keywords if kw.lower() in resp_lower]
            # Need at least 1 keyword match
            is_correct = len(matched) > 0
            detail = f"Matched {len(matched)}/{len(keywords)}: {matched}"
        elif at == "exact_match":
            expected = q.get("answer", "").lower()
            is_correct = expected in response.lower()
            detail = f"Expected: {expected}"
        elif at == "multiple_choice":
            extracted = None
            if len(response) == 1 and response.upper() in "ABCD":
                extracted = response.upper()
            else:
                m = re.search(r'\b([A-D])\b', response)
                if m:
                    extracted = m.group(1).upper()
            is_correct = extracted == q.get("correct_choice", "")
            detail = f"Extracted: {extracted}, Correct: {q.get('correct_choice')}"

        status = "PASS" if is_correct else "FAIL"
        if is_correct:
            correct += 1

        print(f"  [{status}] {qid} [{cat}] [{diff}]")
        print(f"         Q: {q['question'][:80]}")
        print(f"         A: {response[:100]}")
        if not is_correct:
            print(f"         >> {detail}")
        print()

        results.append({
            "id": qid, "category": cat, "difficulty": diff,
            "correct": is_correct, "response": response
        })

    # Summary
    print(f"\n{'='*60}")
    print(f"OVERALL: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"{'='*60}")

    # Per category
    cat_correct = Counter()
    cat_total = Counter()
    for q, r in zip(questions, results):
        cat_total[q["category"]] += 1
        if r["correct"]:
            cat_correct[q["category"]] += 1

    print("\nPer Category:")
    print(f"  {'Category':<25s} {'Score':>10s}")
    print(f"  {'-'*25} {'-'*10}")
    for cat in sorted(cat_total, key=lambda c: cat_correct[c]/cat_total[c]):
        c, t = cat_correct[cat], cat_total[cat]
        pct = c/t*100
        print(f"  {cat:<25s} {c}/{t} ({pct:.0f}%)")

    # Per difficulty
    diff_correct = Counter()
    diff_total = Counter()
    for q, r in zip(questions, results):
        diff_total[q["difficulty"]] += 1
        if r["correct"]:
            diff_correct[q["difficulty"]] += 1

    print("\nPer Difficulty:")
    for d in ["easy", "medium", "hard"]:
        if d in diff_total:
            c, t = diff_correct[d], diff_total[d]
            print(f"  {d:<10s}: {c}/{t} ({c/t*100:.0f}%)")

    # Save results
    results_file = TRAVELQA_DIR / "results" / "benchmark_v2_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(results_file, "w") as f:
        json.dump({"total": total, "correct": correct, "results": results}, f, indent=2)
    print(f"\nResults saved to {results_file}")


if __name__ == "__main__":
    main()
