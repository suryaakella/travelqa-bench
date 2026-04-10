# TravelQA Bench

**The first benchmark for practical travel knowledge in LLMs.**

Every existing travel benchmark (TravelBench, TripTailor, TravelPlanner) tests *planning* — itinerary generation, booking optimization, scheduling. None of them test whether the model actually *knows* anything about traveling to a country: Is the tap water safe? What's the emergency number? Which side of the road do they drive on? Will I get scammed?

TravelQA fills that gap. 500 questions. 10 knowledge categories. 31 countries. 6 continents.

## Results at a Glance

**Gemma 4 E2B (2B params, 4-bit quantized)** on Apple M1:

```
Overall: 89.0% (445/500)

Perfect (100%):  Currency | Cultural Norms | Scams | Visa
Strong  (84-98%): Health (98%) | Safety (90%) | Emergency (86%) | Language (84%)
Weak    (<84%):   Transportation (70%) | Infrastructure (62%)
```

The model knows travel advice cold. It struggles with specific factual details — plug types, driving sides, and distinguishing police vs ambulance numbers.

### Error Breakdown

Of the 55 raw errors, only **~10 are genuine knowledge failures**. The rest:

| Error Type | Count | Example |
|-----------|-------|---------|
| Positional B-bias (driving side) | 13 | Always picks option B regardless of country |
| Format mismatch | 11 | "Type A and B" vs expected "Type A, B" |
| Partial knowledge | 9 | Knows one plug type, not all variants |
| Keyword matching too strict | 7 | "tesekkur" doesn't match "tesekkur" |
| Voltage rounding | 3 | 220V vs 230V (both defensible) |
| Benchmark error | 1 | Vietnam tap water marked safe (it's not) |
| **Genuine knowledge gaps** | **~10** | Wrong emergency number, wrong phrase meaning |

### Real Knowledge Gaps

The only category with genuine failures is **emergency numbers** — the model confuses which number maps to which service (police vs ambulance vs universal). Everything else is either known or partially known.

## What's in the Benchmark

### 10 Categories (50 questions each)

| Category | Type | What It Tests |
|----------|------|--------------|
| Safety | Multiple choice | Crime awareness, natural hazards, night safety |
| Health | Multiple choice | Tap water, diseases, vaccinations, medical access |
| Cultural Norms | Multiple choice | Dress codes, tipping, photography, religious sites |
| Emergency | Exact match | Police, ambulance, fire, universal emergency numbers |
| Currency | Mixed | Currency names, ISO codes, cash vs card usage |
| Infrastructure | Exact match | Voltage, plug types, internet access |
| Language | Keyword match | Official languages, greetings, common phrases |
| Transportation | Multiple choice | Driving side, trains, buses, taxis, domestic flights |
| Visa & Entry | Multiple choice | Visa requirements, passport validity, customs |
| Scams | Multiple choice | Tourist scams, pricing tricks, taxi fraud |

### 31 Countries Across 6 Continents

**Asia:** Japan, Thailand, Vietnam, India, Indonesia, China, South Korea, Nepal, Philippines, Malaysia
**Europe:** Italy, Czech Republic, Norway, Greece, Turkey, Spain, Germany, France
**Americas:** Mexico, Brazil, Argentina, Cuba, Colombia, Peru
**Africa:** Morocco, Kenya, South Africa, Egypt, Tanzania
**Oceania:** Australia, New Zealand
**Middle East:** UAE, Jordan

### Data Sources

- **WikiVoyage** — scraped via MediaWiki API for Stay Safe, Stay Healthy, Respect, Buy, Connect, Talk, Get Around, Get In sections
- **Factual databases** — emergency numbers (ITU), voltages (IEC), currencies (ISO 4217), driving sides

## Per-Category Results (Gemma 4 E2B)

| Category | Accuracy | Notes |
|----------|----------|-------|
| Cultural Norms | **100%** (50/50) | Perfect |
| Currency | **100%** (50/50) | Perfect |
| Scams | **100%** (50/50) | Perfect |
| Visa | **100%** (50/50) | Perfect |
| Health | **98%** (49/50) | 1 error (Vietnam tap water — benchmark bug) |
| Safety | **90%** (45/50) | 5 errors on advisory questions |
| Emergency | **86%** (43/50) | Confuses police/ambulance/universal numbers |
| Language | **84%** (42/50) | Fails on less common greetings |
| Transportation | **70%** (35/50) | Systematic B-positional bias on driving side |
| Infrastructure | **62%** (31/50) | Partial plug types, voltage rounding |

## Per-Country Results (Gemma 4 E2B)

| Country | Accuracy | | Country | Accuracy |
|---------|----------|-|---------|----------|
| Cuba | 100% | | Czech Republic | 100% |
| Egypt | 100% | | Germany | 100% |
| Jordan | 100% | | Morocco | 100% |
| Nepal | 100% | | New Zealand | 100% |
| Peru | 100% | | Philippines | 100% |
| South Korea | 100% | | Spain | 100% |
| Tanzania | 100% | | Australia | 96.2% |
| Japan | 95.7% | | China | 91.7% |
| Thailand | 91.7% | | Greece | 90.9% |
| Kenya | 90.3% | | Mexico | 88.5% |
| UAE | 88.0% | | Argentina | 87.5% |
| Norway | 87.1% | | Brazil | 87.0% |
| Colombia | 86.7% | | India | 85.7% |
| Turkey | 85.7% | | Italy | 81.8% |
| Indonesia | 78.3% | | South Africa | 76.9% |
| Vietnam | 76.5% | | | |

## Quick Start

### Run the benchmark on your model

```bash
# Clone
git clone https://github.com/suryaakella/travelqa-bench.git
cd travelqa-bench

# The benchmark is just a JSON file — use it with any model
cat benchmark.json | python -c "import json,sys; qs=json.load(sys.stdin); print(f'{len(qs)} questions loaded')"
```

### Evaluate Gemma 4 E2B locally (Apple Silicon)

```bash
# Install dependencies
pip install mlx-vlm pandas tqdm

# Download model (one-time)
huggingface-cli download google/gemma-4-e2b-it-4bit --local-dir models/gemma-4-e2b-it-4bit

# Run evaluation
python run_eval.py --raw-only

# Score and generate report
python score.py
# -> results/report.md
```

### Rebuild the benchmark from scratch

```bash
# Scrape WikiVoyage (caches to sources/wikivoyage/)
python build_benchmark.py --scrape-only

# Generate QA pairs from cached data
python build_benchmark.py --generate-only

# Or do both in one step
python build_benchmark.py
```

## Question Format

Each question in `benchmark.json` follows this schema:

```json
{
  "id": "TQA-0001",
  "category": "safety",
  "country": "Japan",
  "city": null,
  "question": "What is a common safety concern for tourists in Japan?",
  "answer_type": "multiple_choice",
  "choices": ["Pickpocketing and petty theft", "Volcanic eruptions", "Extreme cold weather", "Radioactive contamination"],
  "correct_choice": "A",
  "difficulty": "easy",
  "source": "wikivoyage"
}
```

Three answer types:
- **multiple_choice** — 4 options, answer is a letter (A/B/C/D)
- **exact_match** — short factual answer (number, currency code, voltage)
- **keyword_match** — open-ended response scored by keyword overlap

## File Structure

```
travelqa-bench/
├── README.md              # This file
├── benchmark.json         # 500 QA pairs (the deliverable)
├── build_benchmark.py     # WikiVoyage scraper + QA generator
├── run_eval.py            # Gemma 4 E2B evaluation runner (MLX)
├── score.py               # Scoring + report generation
├── rag_pipeline.py        # Optional: TF-IDF RAG retrieval
├── results/
│   └── report.md          # Gemma 4 E2B results
└── sources/               # Cached WikiVoyage data (gitignored)
```

## Contributing

To evaluate a new model:
1. Write an adapter that loads your model and calls `generate(prompt) -> str`
2. Feed each question through the appropriate prompt template (see `run_eval.py`)
3. Run `score.py` to generate comparable results
4. Open a PR with your results file

## License

Benchmark data derived from [WikiVoyage](https://en.wikivoyage.org/) (CC BY-SA 3.0). Factual data (emergency numbers, voltages, currencies) from public sources.
