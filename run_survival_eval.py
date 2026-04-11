"""Evaluate survival benchmark (50 questions) against Gemma 4 E2B."""

import json
import os
import time
from pathlib import Path
from collections import Counter

if os.path.exists("/etc/ssl/cert.pem"):
    os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")

TRAVELQA_DIR = Path(__file__).parent
MODEL_PATH = str(TRAVELQA_DIR.parent / "models" / "gemma-4-e2b-it-4bit")


def main():
    with open(TRAVELQA_DIR / "survival_benchmark.json") as f:
        questions = json.load(f)

    print(f"=== Survival Knowledge Benchmark ({len(questions)} questions) ===\n")
    print("Loading model...", flush=True)
    from mlx_vlm import load, generate as mlx_generate
    from mlx_vlm.prompt_utils import apply_chat_template
    model, processor = load(MODEL_PATH)
    print("Model loaded.\n", flush=True)

    correct = 0
    results = []

    for q in questions:
        prompt = f"Question: {q['question']}\n\nAnswer concisely in one or two sentences with specific details."
        formatted = apply_chat_template(processor, config=model.config, prompt=prompt)
        result = mlx_generate(model, processor, formatted, max_tokens=150, verbose=False)
        response = result.text.strip()

        resp_lower = response.lower()
        keywords = q["keywords"]
        matched = [kw for kw in keywords if kw.lower() in resp_lower]
        is_correct = len(matched) > 0

        if is_correct:
            correct += 1

        status = "PASS" if is_correct else "FAIL"
        print(f"  [{status}] {q['id']} [{q['category']}] [{q['difficulty']}]")
        print(f"         Q: {q['question'][:80]}")
        print(f"         A: {response[:120]}")
        if not is_correct:
            print(f"         >> Expected keywords: {keywords}")
        print()

        results.append({
            "id": q["id"], "category": q["category"], "difficulty": q["difficulty"],
            "correct": is_correct, "response": response, "matched": matched,
            "keywords": keywords
        })

    total = len(questions)
    print(f"\n{'='*60}")
    print(f"OVERALL: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"{'='*60}")

    # Per category
    cat_correct = Counter()
    cat_total = Counter()
    for r in results:
        cat_total[r["category"]] += 1
        if r["correct"]:
            cat_correct[r["category"]] += 1

    print("\nPer Category:")
    print(f"  {'Category':<15s} {'Score':>10s}")
    print(f"  {'-'*15} {'-'*10}")
    for cat in sorted(cat_total, key=lambda c: cat_correct[c]/cat_total[c]):
        c, t = cat_correct[cat], cat_total[cat]
        print(f"  {cat:<15s} {c}/{t} ({c/t*100:.0f}%)")

    # Per difficulty
    print("\nPer Difficulty:")
    diff_correct = Counter()
    diff_total = Counter()
    for r in results:
        diff_total[r["difficulty"]] += 1
        if r["correct"]:
            diff_correct[r["difficulty"]] += 1
    for d in ["easy", "medium", "hard"]:
        if d in diff_total:
            c, t = diff_correct[d], diff_total[d]
            print(f"  {d:<10s}: {c}/{t} ({c/t*100:.0f}%)")

    # Failures detail
    failures = [r for r in results if not r["correct"]]
    print(f"\n{'='*60}")
    print(f"FAILURES ({len(failures)}):")
    print(f"{'='*60}")
    for r in failures:
        print(f"  {r['id']} [{r['category']}] [{r['difficulty']}]")
        print(f"    Response: {r['response'][:100]}")
        print(f"    Expected: {r['keywords']}")
        print()

    # Save
    out = TRAVELQA_DIR / "results" / "survival_benchmark_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump({"total": total, "correct": correct, "pct": round(correct/total*100, 1), "results": results}, f, indent=2)
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
