"""
Smoke test for TravelQA v2 — 20 questions targeting v1 knowledge gaps.

Tests:
1. Emergency numbers (specific service disambiguation)
2. Infrastructure (exact plug/voltage combos)
3. Transportation (driving side with randomized positions)
4. Language (harder phrase questions)
5. Improved scoring (fuzzy matching for format variants)
"""

import json
import os
import re
import time
from pathlib import Path

# Fix SSL
if os.path.exists("/etc/ssl/cert.pem"):
    os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/cert.pem")

SMOKE_QUESTIONS = [
    # --- Emergency: disambiguate police vs ambulance vs fire ---
    {
        "id": "V2-SMOKE-01",
        "category": "emergency",
        "country": "Japan",
        "question": "In Japan, you witness a crime. Which number do you call — 110 or 119?",
        "answer_type": "exact_match",
        "answer": "110",
        "difficulty": "medium",
    },
    {
        "id": "V2-SMOKE-02",
        "category": "emergency",
        "country": "Japan",
        "question": "In Japan, someone collapses and needs an ambulance. Which number do you call — 110 or 119?",
        "answer_type": "exact_match",
        "answer": "119",
        "difficulty": "medium",
    },
    {
        "id": "V2-SMOKE-03",
        "category": "emergency",
        "country": "Brazil",
        "question": "What is the difference between 190, 192, and 193 in Brazil's emergency system?",
        "answer_type": "keyword_match",
        "keywords": ["police", "ambulance", "fire"],
        "difficulty": "hard",
    },
    {
        "id": "V2-SMOKE-04",
        "category": "emergency",
        "country": "South Africa",
        "question": "Which South African emergency number reaches the ambulance service: 10111 or 10177?",
        "answer_type": "exact_match",
        "answer": "10177",
        "difficulty": "hard",
    },
    # --- Infrastructure: combined voltage + plug questions ---
    {
        "id": "V2-SMOKE-05",
        "category": "infrastructure",
        "country": "Japan",
        "question": "Japan uses a unique electrical voltage compared to most of Asia. What voltage does Japan use?",
        "answer_type": "exact_match",
        "answer": "100",
        "difficulty": "medium",
    },
    {
        "id": "V2-SMOKE-06",
        "category": "infrastructure",
        "country": "United Kingdom",
        "question": "What type of electrical plug is standard in the United Kingdom?",
        "answer_type": "exact_match",
        "answer": "G",
        "difficulty": "easy",
    },
    {
        "id": "V2-SMOKE-07",
        "category": "infrastructure",
        "country": "Brazil",
        "question": "Brazil has a unique plug type found almost nowhere else. What type is it?",
        "answer_type": "exact_match",
        "answer": "N",
        "difficulty": "hard",
    },
    {
        "id": "V2-SMOKE-08",
        "category": "infrastructure",
        "country": "India",
        "question": "A traveler from the US (Type A/B plugs) is going to India. Will their plugs fit without an adapter?",
        "answer_type": "multiple_choice",
        "choices": [
            "No, India uses Type C, D, and M plugs",
            "Yes, US plugs work in India",
            "Only in 5-star hotels",
            "Only if you use a voltage converter"
        ],
        "correct_choice": "A",
        "difficulty": "medium",
    },
    # --- Transportation: driving side with randomized positions ---
    {
        "id": "V2-SMOKE-09",
        "category": "transportation",
        "country": "Japan",
        "question": "You're renting a car in Japan. Which side of the road will you drive on?",
        "answer_type": "multiple_choice",
        "choices": [
            "Right side, like the US",
            "Left side, like the UK",
            "Depends on the prefecture",
            "Japan does not allow tourist car rentals"
        ],
        "correct_choice": "B",
        "difficulty": "easy",
    },
    {
        "id": "V2-SMOKE-10",
        "category": "transportation",
        "country": "Thailand",
        "question": "Which side of the road do vehicles drive on in Thailand?",
        "answer_type": "multiple_choice",
        "choices": [
            "Right side",
            "It varies by region",
            "Left side",
            "Center lane only"
        ],
        "correct_choice": "C",
        "difficulty": "easy",
    },
    {
        "id": "V2-SMOKE-11",
        "category": "transportation",
        "country": "Germany",
        "question": "A British tourist renting a car in Germany should be aware that Germany drives on the _____ side.",
        "answer_type": "exact_match",
        "answer": "right",
        "difficulty": "easy",
    },
    {
        "id": "V2-SMOKE-12",
        "category": "transportation",
        "country": "Indonesia",
        "question": "Indonesia, a former Dutch colony, drives on which side of the road?",
        "answer_type": "multiple_choice",
        "choices": [
            "Right side, following Dutch tradition",
            "Alternates by island",
            "No standardized driving side",
            "Left side"
        ],
        "correct_choice": "D",
        "difficulty": "medium",
    },
    # --- Language: harder phrase/meaning questions ---
    {
        "id": "V2-SMOKE-13",
        "category": "language",
        "country": "Japan",
        "question": "What does 'sumimasen' mean in Japanese?",
        "answer_type": "keyword_match",
        "keywords": ["excuse", "sorry", "pardon"],
        "difficulty": "medium",
    },
    {
        "id": "V2-SMOKE-14",
        "category": "language",
        "country": "Thailand",
        "question": "In Thai, what word do men add to the end of sentences for politeness — 'krap' or 'ka'?",
        "answer_type": "exact_match",
        "answer": "krap",
        "difficulty": "medium",
    },
    {
        "id": "V2-SMOKE-15",
        "category": "language",
        "country": "Morocco",
        "question": "Most Moroccans speak Arabic and which European language?",
        "answer_type": "exact_match",
        "answer": "French",
        "difficulty": "easy",
    },
    {
        "id": "V2-SMOKE-16",
        "category": "language",
        "country": "Turkey",
        "question": "How do you say 'thank you' in Turkish?",
        "answer_type": "keyword_match",
        "keywords": ["tesekkur", "teşekkür", "teshekkur", "tesekkürler"],
        "difficulty": "medium",
    },
    # --- Mixed hard questions ---
    {
        "id": "V2-SMOKE-17",
        "category": "emergency",
        "country": "Australia",
        "question": "What single number do you call for all emergencies in Australia?",
        "answer_type": "exact_match",
        "answer": "000",
        "difficulty": "easy",
    },
    {
        "id": "V2-SMOKE-18",
        "category": "emergency",
        "country": "European Union",
        "question": "What is the universal emergency number that works across all EU countries?",
        "answer_type": "exact_match",
        "answer": "112",
        "difficulty": "easy",
    },
    {
        "id": "V2-SMOKE-19",
        "category": "infrastructure",
        "country": "Mexico",
        "question": "Mexico uses the same voltage and plug type as which nearby country?",
        "answer_type": "keyword_match",
        "keywords": ["united states", "us", "usa", "america"],
        "difficulty": "medium",
    },
    {
        "id": "V2-SMOKE-20",
        "category": "transportation",
        "country": "India",
        "question": "India was a British colony. Like the UK, does India drive on the left or right side of the road?",
        "answer_type": "exact_match",
        "answer": "left",
        "difficulty": "easy",
    },
]


def improved_score_exact(response: str, expected: str) -> bool:
    """Improved exact match scoring with fuzzy handling."""
    resp = response.strip().lower()
    exp = expected.strip().lower()

    # Direct containment
    if exp in resp or resp in exp:
        return True

    # Numeric match
    resp_nums = re.findall(r'\d+', resp)
    exp_nums = re.findall(r'\d+', exp)
    if exp_nums and any(n in resp_nums for n in exp_nums):
        return True

    # Handle "Type X and Y" vs "Type X, Y" for plug types
    resp_clean = resp.replace(" and ", ", ").replace("type ", "").replace("types ", "")
    exp_clean = exp.replace(" and ", ", ").replace("type ", "").replace("types ", "")
    if set(resp_clean.split(", ")) == set(exp_clean.split(", ")):
        return True

    return False


def improved_score_keyword(response: str, keywords: list[str]) -> bool:
    """Improved keyword scoring with fuzzy matching."""
    resp = response.strip().lower()
    found = 0
    for kw in keywords:
        kw_lower = kw.lower()
        # Direct match
        if kw_lower in resp:
            found += 1
            continue
        # Remove diacritics approximation
        kw_ascii = kw_lower.replace("ş", "s").replace("ü", "u").replace("ö", "o").replace("ç", "c").replace("ğ", "g").replace("ı", "i")
        if kw_ascii in resp:
            found += 1
            continue
    return found > 0  # At least one keyword match


def main():
    MODEL_PATH = str(Path(__file__).parent.parent / "models" / "gemma-4-e2b-it-4bit")

    print("=== TravelQA v2 Smoke Test (20 questions) ===\n")

    # Load model
    print("Loading model...", flush=True)
    from mlx_vlm import load, generate as mlx_generate
    from mlx_vlm.prompt_utils import apply_chat_template
    model, processor = load(MODEL_PATH)
    print("Model loaded.\n", flush=True)

    correct = 0
    total = len(SMOKE_QUESTIONS)
    results = []

    for q in SMOKE_QUESTIONS:
        at = q["answer_type"]

        if at == "multiple_choice":
            prompt = f"Question: {q['question']}\n\n"
            for i, c in enumerate(q["choices"]):
                prompt += f"{chr(65+i)}. {c}\n"
            prompt += "\nAnswer with ONLY the letter (A, B, C, or D)."
        elif at == "exact_match":
            prompt = f"Question: {q['question']}\n\nAnswer with ONLY the exact value. No explanation."
        else:
            prompt = f"Question: {q['question']}\n\nAnswer concisely in one sentence."

        formatted = apply_chat_template(processor, config=model.config, prompt=prompt)
        result = mlx_generate(model, processor, formatted, max_tokens=64, verbose=False)
        response = result.text.strip()

        # Score
        is_correct = False
        if at == "multiple_choice":
            extracted = None
            if len(response) == 1 and response.upper() in "ABCD":
                extracted = response.upper()
            else:
                m = re.search(r'\b([A-D])\b', response)
                if m:
                    extracted = m.group(1).upper()
            is_correct = extracted == q.get("correct_choice", "")
            answer_display = f"Model: {extracted or '?'} | Correct: {q['correct_choice']}"
        elif at == "exact_match":
            is_correct = improved_score_exact(response, q["answer"])
            answer_display = f"Model: \"{response}\" | Expected: \"{q['answer']}\""
        else:
            is_correct = improved_score_keyword(response, q["keywords"])
            answer_display = f"Model: \"{response[:60]}\" | Keywords: {q['keywords']}"

        if is_correct:
            correct += 1
        status = "PASS" if is_correct else "FAIL"

        print(f"  [{status}] {q['id']} [{q['category']}] [{q['country']}]")
        print(f"         Q: {q['question'][:70]}")
        print(f"         {answer_display}")
        print()

        results.append({"id": q["id"], "correct": is_correct, "response": response})

    print(f"\n=== Results: {correct}/{total} ({correct/total*100:.0f}%) ===")

    # Category breakdown
    from collections import Counter
    cat_correct = Counter()
    cat_total = Counter()
    for q, r in zip(SMOKE_QUESTIONS, results):
        cat_total[q["category"]] += 1
        if r["correct"]:
            cat_correct[q["category"]] += 1

    print("\nPer category:")
    for cat in sorted(cat_total):
        c, t = cat_correct[cat], cat_total[cat]
        print(f"  {cat:20s}: {c}/{t} ({c/t*100:.0f}%)")


if __name__ == "__main__":
    main()
