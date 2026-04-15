"""CA DMV Practice Test (40 questions) — Gemma 4 E2B via Cactus engine."""

import json
import os
import re
import sys
import time
from pathlib import Path
from collections import Counter

TRAVELQA_DIR = Path(__file__).parent
CACTUS_DIR = TRAVELQA_DIR.parent / "cactus"
WEIGHTS_DIR = CACTUS_DIR / "weights" / "gemma-4-e2b-it"

# Add cactus python to path
sys.path.insert(0, str(CACTUS_DIR / "python"))

from src.cactus import cactus_init, cactus_complete, cactus_destroy, cactus_reset


def main():
    with open(TRAVELQA_DIR / "dmv_benchmark.json") as f:
        questions = json.load(f)

    print(f"=== California DMV Practice Test ({len(questions)} questions) ===")
    print(f"Engine: Cactus | Model: Gemma 4 E2B INT4\n")

    print("Loading model...", flush=True)
    t0 = time.time()
    model = cactus_init(str(WEIGHTS_DIR), None, False)
    print(f"Model loaded in {time.time()-t0:.1f}s\n", flush=True)

    correct = 0
    results = []
    total_time = 0

    for q in questions:
        # Compact prompt avoids triggering thinking mode
        choices_str = " ".join(f"{chr(65+i)}={c}" for i, c in enumerate(q["choices"]))
        prompt = f"Answer only with a single letter. No thinking. No explanation.\n\nQ: {q['question']} {choices_str}\nA:"

        messages = json.dumps([{"role": "user", "content": prompt}])
        options = json.dumps({"max_tokens": 128, "temperature": 0.0})

        t1 = time.time()
        raw = cactus_complete(model, messages, options, None, None)
        elapsed = time.time() - t1
        total_time += elapsed

        # Cactus returns JSON with "response" field
        try:
            parsed = json.loads(raw)
            response = parsed.get("response", "").strip()
        except json.JSONDecodeError:
            response = raw.strip()

        # Strip thinking tokens if present
        if "<|channel>response" in response:
            response = response.split("<|channel>response")[-1].strip()
        elif "<|channel>thought" in response:
            # All thinking, no answer — try to extract from end
            response = response.split("\n")[-1].strip()

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

        print(f"  [{status}] {q['id']} [{q['category']}] ({elapsed:.1f}s)")
        print(f"         Q: {q['question'][:80]}")
        print(f"         Model: {extracted or '?'} ({model_text[:60]})")
        if not is_correct:
            print(f"         Correct: {q['correct_choice']} ({correct_text[:60]})")
        print()

        results.append({
            "id": q["id"], "category": q["category"], "difficulty": q["difficulty"],
            "correct": is_correct, "extracted": extracted, "expected": q["correct_choice"],
            "response": response, "time_s": round(elapsed, 2)
        })

    cactus_destroy(model)

    total = len(questions)
    avg_time = total_time / total

    print(f"\n{'='*60}")
    print(f"OVERALL: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"Total time: {total_time:.1f}s | Avg per question: {avg_time:.1f}s")
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
        json.dump({
            "engine": "cactus", "model": "gemma-4-e2b-it-int4",
            "total": total, "correct": correct, "pct": round(correct/total*100, 1),
            "total_time_s": round(total_time, 1), "avg_time_s": round(avg_time, 2),
            "results": results
        }, f, indent=2)
    print(f"Saved to {out}")


if __name__ == "__main__":
    main()
