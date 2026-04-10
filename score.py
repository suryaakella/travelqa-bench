"""
TravelQA Scoring

Scores evaluation results and generates a comprehensive report.

Scoring methods:
- Multiple choice: exact letter match
- Exact match: case-insensitive string match (with normalization)
- Keyword match: fraction of expected keywords found in response

Usage:
    python score.py                     # Score all results, generate report
    python score.py --results-file X    # Score a specific results file
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

TRAVELQA_DIR = Path(__file__).parent
RESULTS_DIR = TRAVELQA_DIR / "results"
BENCHMARK_FILE = TRAVELQA_DIR / "benchmark.json"


def load_benchmark() -> dict[str, dict]:
    """Load benchmark questions indexed by ID."""
    with open(BENCHMARK_FILE) as f:
        questions = json.load(f)
    return {q["id"]: q for q in questions}


def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    text = text.strip().lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    return text


def score_mc(result: dict, question: dict) -> bool:
    """Score a multiple-choice answer."""
    if result.get("parse_failure"):
        return False
    extracted = result.get("extracted_answer", "")
    correct = question.get("correct_choice", "")
    return extracted.upper() == correct.upper()


def score_exact(result: dict, question: dict) -> bool:
    """Score an exact-match answer."""
    response = normalize_text(result.get("extracted_answer", ""))
    expected = normalize_text(question.get("answer", ""))

    # Direct match
    if expected in response or response in expected:
        return True

    # For numeric answers, extract numbers and compare
    resp_nums = re.findall(r'\d+', response)
    exp_nums = re.findall(r'\d+', expected)
    if exp_nums and any(n in resp_nums for n in exp_nums):
        return True

    return False


def score_keyword(result: dict, question: dict) -> float:
    """Score a keyword-match answer. Returns fraction of keywords found."""
    response = normalize_text(result.get("extracted_answer", ""))
    keywords = question.get("keywords", [])

    if not keywords:
        return 0.0

    found = sum(1 for kw in keywords if kw.lower() in response)
    return found / len(keywords)


def score_results(results_data: dict, benchmark: dict[str, dict]) -> dict:
    """Score all results against the benchmark."""
    results = results_data.get("results", [])
    scores = {
        "total": 0,
        "correct": 0,
        "parse_failures": 0,
        "by_category": defaultdict(lambda: {"total": 0, "correct": 0, "parse_failures": 0}),
        "by_country": defaultdict(lambda: {"total": 0, "correct": 0}),
        "by_difficulty": defaultdict(lambda: {"total": 0, "correct": 0}),
        "details": [],
    }

    for result in results:
        qid = result["id"]
        question = benchmark.get(qid)
        if not question:
            continue

        answer_type = question.get("answer_type", "multiple_choice")
        category = question.get("category", "unknown")
        country = question.get("country", "unknown")
        difficulty = question.get("difficulty", "unknown")

        is_correct = False
        keyword_score = 0.0

        if answer_type == "multiple_choice":
            is_correct = score_mc(result, question)
        elif answer_type == "exact_match":
            is_correct = score_exact(result, question)
        elif answer_type == "keyword_match":
            keyword_score = score_keyword(result, question)
            is_correct = keyword_score >= 0.5  # At least half keywords

        scores["total"] += 1
        if is_correct:
            scores["correct"] += 1
        if result.get("parse_failure"):
            scores["parse_failures"] += 1

        cat_scores = scores["by_category"][category]
        cat_scores["total"] += 1
        if is_correct:
            cat_scores["correct"] += 1
        if result.get("parse_failure"):
            cat_scores["parse_failures"] += 1

        country_scores = scores["by_country"][country]
        country_scores["total"] += 1
        if is_correct:
            country_scores["correct"] += 1

        diff_scores = scores["by_difficulty"][difficulty]
        diff_scores["total"] += 1
        if is_correct:
            diff_scores["correct"] += 1

        scores["details"].append({
            "id": qid,
            "category": category,
            "country": country,
            "correct": is_correct,
            "keyword_score": keyword_score if answer_type == "keyword_match" else None,
            "parse_failure": result.get("parse_failure", False),
        })

    return scores


def generate_report(raw_scores: dict | None, rag_scores: dict | None) -> str:
    """Generate markdown report."""
    lines = [
        "# TravelQA Evaluation Report",
        f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Model: Gemma 4 E2B (4-bit quantized, MLX)",
        f"Platform: Apple M1, 16GB RAM",
        "",
    ]

    # Summary
    lines.append("## Summary\n")
    lines.append("| Metric | Raw | RAG | Delta |")
    lines.append("|--------|-----|-----|-------|")

    raw_acc = (raw_scores["correct"] / raw_scores["total"] * 100) if raw_scores else 0
    rag_acc = (rag_scores["correct"] / rag_scores["total"] * 100) if rag_scores else 0
    delta = rag_acc - raw_acc

    raw_pf = raw_scores["parse_failures"] if raw_scores else 0
    rag_pf = rag_scores["parse_failures"] if rag_scores else 0

    raw_str = f"{raw_acc:.1f}%" if raw_scores else "—"
    rag_str = f"{rag_acc:.1f}%" if rag_scores else "—"
    delta_str = f"+{delta:.1f}%" if delta >= 0 else f"{delta:.1f}%"

    lines.append(f"| Overall Accuracy | {raw_str} | {rag_str} | {delta_str} |")
    lines.append(f"| Total Questions | {raw_scores['total'] if raw_scores else '—'} | {rag_scores['total'] if rag_scores else '—'} | |")
    lines.append(f"| Parse Failures | {raw_pf} | {rag_pf} | |")

    # Per-category breakdown
    lines.append("\n## Per-Category Accuracy\n")
    lines.append("| Category | Raw | RAG | Delta |")
    lines.append("|----------|-----|-----|-------|")

    categories = sorted(set(
        list(raw_scores["by_category"].keys() if raw_scores else []) +
        list(rag_scores["by_category"].keys() if rag_scores else [])
    ))

    for cat in categories:
        raw_cat = raw_scores["by_category"].get(cat, {"total": 0, "correct": 0}) if raw_scores else {"total": 0, "correct": 0}
        rag_cat = rag_scores["by_category"].get(cat, {"total": 0, "correct": 0}) if rag_scores else {"total": 0, "correct": 0}

        raw_cat_acc = (raw_cat["correct"] / raw_cat["total"] * 100) if raw_cat["total"] > 0 else 0
        rag_cat_acc = (rag_cat["correct"] / rag_cat["total"] * 100) if rag_cat["total"] > 0 else 0
        cat_delta = rag_cat_acc - raw_cat_acc

        raw_cat_str = f"{raw_cat_acc:.1f}% ({raw_cat['correct']}/{raw_cat['total']})" if raw_cat["total"] > 0 else "—"
        rag_cat_str = f"{rag_cat_acc:.1f}% ({rag_cat['correct']}/{rag_cat['total']})" if rag_cat["total"] > 0 else "—"
        delta_cat_str = f"+{cat_delta:.1f}%" if cat_delta >= 0 else f"{cat_delta:.1f}%"

        lines.append(f"| {cat} | {raw_cat_str} | {rag_cat_str} | {delta_cat_str} |")

    # Per-country breakdown
    lines.append("\n## Per-Country Accuracy\n")
    lines.append("| Country | Raw | RAG | Delta |")
    lines.append("|---------|-----|-----|-------|")

    countries = sorted(set(
        list(raw_scores["by_country"].keys() if raw_scores else []) +
        list(rag_scores["by_country"].keys() if rag_scores else [])
    ))

    for country in countries:
        raw_c = raw_scores["by_country"].get(country, {"total": 0, "correct": 0}) if raw_scores else {"total": 0, "correct": 0}
        rag_c = rag_scores["by_country"].get(country, {"total": 0, "correct": 0}) if rag_scores else {"total": 0, "correct": 0}

        raw_c_acc = (raw_c["correct"] / raw_c["total"] * 100) if raw_c["total"] > 0 else 0
        rag_c_acc = (rag_c["correct"] / rag_c["total"] * 100) if rag_c["total"] > 0 else 0
        c_delta = rag_c_acc - raw_c_acc

        raw_c_str = f"{raw_c_acc:.1f}%" if raw_c["total"] > 0 else "—"
        rag_c_str = f"{rag_c_acc:.1f}%" if rag_c["total"] > 0 else "—"
        delta_c_str = f"+{c_delta:.1f}%" if c_delta >= 0 else f"{c_delta:.1f}%"

        lines.append(f"| {country} | {raw_c_str} | {rag_c_str} | {delta_c_str} |")

    # Difficulty breakdown
    lines.append("\n## By Difficulty\n")
    lines.append("| Difficulty | Raw | RAG | Delta |")
    lines.append("|-----------|-----|-----|-------|")

    for diff in ["easy", "medium", "hard"]:
        raw_d = raw_scores["by_difficulty"].get(diff, {"total": 0, "correct": 0}) if raw_scores else {"total": 0, "correct": 0}
        rag_d = rag_scores["by_difficulty"].get(diff, {"total": 0, "correct": 0}) if rag_scores else {"total": 0, "correct": 0}

        raw_d_acc = (raw_d["correct"] / raw_d["total"] * 100) if raw_d["total"] > 0 else 0
        rag_d_acc = (rag_d["correct"] / rag_d["total"] * 100) if rag_d["total"] > 0 else 0
        d_delta = rag_d_acc - raw_d_acc

        raw_d_str = f"{raw_d_acc:.1f}% ({raw_d['correct']}/{raw_d['total']})" if raw_d["total"] > 0 else "—"
        rag_d_str = f"{rag_d_acc:.1f}% ({rag_d['correct']}/{rag_d['total']})" if rag_d["total"] > 0 else "—"
        delta_d_str = f"+{d_delta:.1f}%" if d_delta >= 0 else f"{d_delta:.1f}%"

        lines.append(f"| {diff} | {raw_d_str} | {rag_d_str} | {delta_d_str} |")

    # Error analysis
    lines.append("\n## Error Analysis\n")

    if raw_scores:
        lines.append("### Raw Mode Errors\n")
        raw_errors = [d for d in raw_scores["details"] if not d["correct"]]
        error_by_cat = defaultdict(int)
        for e in raw_errors:
            error_by_cat[e["category"]] += 1

        lines.append("Category failure counts:")
        for cat, count in sorted(error_by_cat.items(), key=lambda x: -x[1]):
            lines.append(f"- {cat}: {count} errors")

    if rag_scores:
        lines.append("\n### RAG Mode Errors\n")
        rag_errors = [d for d in rag_scores["details"] if not d["correct"]]
        error_by_cat = defaultdict(int)
        for e in rag_errors:
            error_by_cat[e["category"]] += 1

        lines.append("Category failure counts:")
        for cat, count in sorted(error_by_cat.items(), key=lambda x: -x[1]):
            lines.append(f"- {cat}: {count} errors")

    # Key findings
    lines.append("\n## Key Findings\n")

    if raw_scores and rag_scores:
        # Find categories with biggest RAG improvement
        improvements = []
        for cat in categories:
            raw_cat = raw_scores["by_category"].get(cat, {"total": 0, "correct": 0})
            rag_cat = rag_scores["by_category"].get(cat, {"total": 0, "correct": 0})
            if raw_cat["total"] > 0 and rag_cat["total"] > 0:
                raw_pct = raw_cat["correct"] / raw_cat["total"] * 100
                rag_pct = rag_cat["correct"] / rag_cat["total"] * 100
                improvements.append((cat, rag_pct - raw_pct))

        improvements.sort(key=lambda x: -x[1])

        if improvements:
            best = improvements[0]
            worst = improvements[-1]
            lines.append(f"- **Biggest RAG improvement:** {best[0]} (+{best[1]:.1f}%)")
            lines.append(f"- **Smallest RAG improvement:** {worst[0]} ({worst[1]:+.1f}%)")
            lines.append(f"- **Overall RAG delta:** {delta:+.1f}%")
            lines.append(f"- **Parse failure rate (raw):** {raw_pf / raw_scores['total'] * 100:.1f}%")
            lines.append(f"- **Parse failure rate (RAG):** {rag_pf / rag_scores['total'] * 100:.1f}%")

    return "\n".join(lines)


def main():
    benchmark = load_benchmark()
    print(f"Loaded {len(benchmark)} benchmark questions")

    raw_scores = None
    rag_scores = None

    # Load raw results
    raw_file = RESULTS_DIR / "gemma4_e2b_raw.json"
    if raw_file.exists():
        with open(raw_file) as f:
            raw_data = json.load(f)
        raw_scores = score_results(raw_data, benchmark)
        print(f"Raw: {raw_scores['correct']}/{raw_scores['total']} correct "
              f"({raw_scores['correct']/raw_scores['total']*100:.1f}%)")

    # Load RAG results
    rag_file = RESULTS_DIR / "gemma4_e2b_rag.json"
    if rag_file.exists():
        with open(rag_file) as f:
            rag_data = json.load(f)
        rag_scores = score_results(rag_data, benchmark)
        print(f"RAG: {rag_scores['correct']}/{rag_scores['total']} correct "
              f"({rag_scores['correct']/rag_scores['total']*100:.1f}%)")

    if not raw_scores and not rag_scores:
        print("No results found. Run run_eval.py first.")
        return

    # Generate report
    report = generate_report(raw_scores, rag_scores)
    report_file = RESULTS_DIR / "report.md"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_file, "w") as f:
        f.write(report)
    print(f"\nReport saved to {report_file}")
    print("\n" + report)


if __name__ == "__main__":
    main()
