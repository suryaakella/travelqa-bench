"""Evaluate California DMV practice test (40 questions) against Gemma 4 E2B."""

import json
import os
import re
from pathlib import Path
from collections import Counter

if os.path.exists("/etc/ssl/cert.pem"):
    os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")

TRAVELQA_DIR = Path(__file__).parent
MODEL_PATH = str(TRAVELQA_DIR.parent / "models" / "gemma-4-e2b-it-4bit")


def main():
    with open(TRAVELQA_DIR / "dmv_benchmark.json") as f:
        questions = json.load(f)

    print(f"=== California DMV Practice Test ({len(questions)} questions) ===\n")
    print("Loading model...", flush=True)
    from mlx_vlm import load, generate as mlx_generate
    from mlx_vlm.prompt_utils import apply_chat_template
    model, processor = load(MODEL_PATH)
    print("Model loaded.\n", flush=True)

    correct = 0
    results = []

    for q in questions:
        # Build MC prompt with 3 choices
        prompt = f"California DMV written test question:\n\n{q['question']}\n\n"
        for i, c in enumerate(q["choices"]):
            prompt += f"{chr(65+i)}. {c}\n"
        prompt += "\nAnswer with ONLY the letter (A, B, or C)."

        formatted = apply_chat_template(processor, config=model.config, prompt=prompt)
        result = mlx_generate(model, processor, formatted, max_tokens=32, verbose=False)
        response = result.text.strip()

        # Extract letter
        extracted = None
        if len(response) == 1 and response.upper() in "ABC":
            extracted = response.upper()
        else:
            m = re.search(r'\b([A-C])\b', response)
            if m:
                extracted = m.group(1).upper()

        is_correct = extracted == q["correct_choice"]
        if is_correct:
            correct += 1

        status = "PASS" if is_correct else "FAIL"
        correct_text = q["choices"][ord(q["correct_choice"]) - 65]
        model_text = q["choices"][ord(extracted) - 65] if extracted and extracted in "ABC" else "?"

        print(f"  [{status}] {q['id']} [{q['category']}]")
        print(f"         Q: {q['question'][:80]}")
        print(f"         Model: {extracted or '?'} ({model_text[:60]})")
        if not is_correct:
            print(f"         Correct: {q['correct_choice']} ({correct_text[:60]})")
        print()

        results.append({
            "id": q["id"], "category": q["category"], "difficulty": q["difficulty"],
            "correct": is_correct, "extracted": extracted, "expected": q["correct_choice"],
            "response": response
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
    for cat in sorted(cat_total, key=lambda c: cat_correct[c]/cat_total[c]):
        c, t = cat_correct[cat], cat_total[cat]
        print(f"  {cat:<20s} {c}/{t} ({c/t*100:.0f}%)")

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

    # Failures
    failures = [r for r in results if not r["correct"]]
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for r in failures:
            q_obj = next(q for q in questions if q["id"] == r["id"])
            print(f"  {r['id']}: picked {r['extracted']}, correct {r['expected']}")
            print(f"    Q: {q_obj['question'][:70]}")
            print()

    # Save
    out = TRAVELQA_DIR / "results" / "dmv_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump({"total": total, "correct": correct, "pct": round(correct/total*100, 1), "results": results}, f, indent=2)
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
