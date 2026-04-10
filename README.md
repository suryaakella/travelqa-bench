# TravelQA: Practical Travel Knowledge Benchmark

A 500-question benchmark testing LLMs on real-world travel knowledge across 10 categories, sourced from WikiVoyage + factual databases.

## Categories (50 questions each)

| # | Category | Question Type |
|---|----------|---------------|
| 1 | Safety | Advisory (MC) |
| 2 | Health | Advisory (MC) |
| 3 | Cultural Norms | Advisory (MC) |
| 4 | Emergency | Factual (exact match) |
| 5 | Currency & Money | Mixed (MC + factual) |
| 6 | Infrastructure | Factual (exact match) |
| 7 | Language/Phrases | Open-ended (keyword) |
| 8 | Transportation | Advisory (MC) |
| 9 | Entry & Visa | Factual (MC) |
| 10 | Scams & Pitfalls | Advisory (MC) |

## Countries (30+, 6 continents)

Asia, Europe, Americas, Africa, Oceania, Middle East coverage.

## Usage

```bash
# 1. Scrape WikiVoyage data
python build_benchmark.py

# 2. Run evaluation (raw + RAG)
python run_eval.py

# 3. Score results
python score.py

# Results written to results/report.md
```

## Dependencies

```bash
pip install chromadb sentence-transformers
# Existing: mlx-vlm, datasets, pandas, tqdm
```
