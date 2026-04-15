# Offline LLM Knowledge Benchmarks

Can a 2B parameter model running locally (no internet) give you correct answers when it matters? We tested.

## Model Under Test

**Gemma 4 E2B** — 2B params, 4-bit quantized, running on Apple M1. No RAG, no retrieval, no internet. Pure parametric knowledge. Tested with both MLX and [Cactus](https://github.com/cactus-compute/cactus) inference engines.

## Experiments

### 1. Travel Knowledge (500 questions)

Practical travel info across 31 countries: emergency numbers, plug types, driving sides, cultural norms, scams, visa rules.

```
Overall: 89% (445/500)

100%: Currency, Cultural Norms, Scams, Visa
84-98%: Health, Safety, Emergency, Language
<84%: Transportation (70%), Infrastructure (62%)
```

**Takeaway:** Advisory knowledge (what to do) is near-perfect. Factual recall (exact numbers, plug types) is the weak point. Only ~10 genuine knowledge failures out of 500 — most "errors" are format mismatches or positional bias in MC questions.

### 2. Offline Use Cases (60 questions)

Medical, military, aviation, industrial, agriculture, disaster, maritime, outdoor, education, legal, comms.

```
Overall: 80% (48/60)

100%: Industrial, Rural Health, Outdoor, Legal, Comms
80-88%: Medical, Agriculture, Education
50-60%: Maritime, Military/Survival, Aviation, Disaster
```

**Takeaway:** General knowledge (first aid, plant science, law) is solid. Domain-specific protocols (squawk codes, VHF channels, buoyage systems) are not in the model.

### 3. Survival Knowledge (50 questions)

Deep-dive into the weakest area. Navigation, water, shelter, fire, food, first aid, signaling, hazards, tools.

```
Overall: 80% (40/50)

100%: Shelter, Tools
80-86%: Water, First Aid, Food, Fire, Signaling
71%: Navigation
40%: Hazards
```

**Takeaway:** The model knows *concepts* but not *procedures*. It can explain what a solar still is, but can't tell you how to use an analog watch as a compass. For hazards (river crossing, ice rescue, quicksand), it gives generic "stay calm" advice instead of the specific steps that keep you alive.

### 4. California DMV Written Test (40 questions)

Can it pass a driving test? 40 questions from CA DMV Class C practice exams. Evaluated with Cactus engine (12s model load vs 140s with MLX).

```
Overall: 37.5% (15/40) — FAIL (passing is 83%)

80%: Parking
67%: Right of Way
38-43%: Rules of Road, Safe Driving
0%: Laws/Penalties, Admin/DMV
```

**Takeaway:** The model cannot pass a state driving test. It knows basic concepts (red curb, right turn lane, parallel parking) but fails on CA-specific vehicle code: legal penalties, minor driving hours, headset laws, SR-1 filing rules. State-specific regulatory knowledge is absent from a 2B general-purpose model.

## Key Findings

1. **Advisory vs. factual split.** The model excels at "what should I generally do" (98%+) but fails at "what is the exact number/code/procedure" (~70%).

2. **Hedging kills usefulness.** On survival questions, the model qualifies everything ("it varies", "depends on factors") instead of giving the standard answer. An offline assistant needs to be decisive.

3. **Domain protocols are absent.** Aviation (squawk 7700), maritime (VHF Ch 16, IALA buoyage), and military procedures are not in a 2B general-purpose model. Expected, but confirmed.

4. **Scoring inflates failure rate.** Across all experiments, ~30% of "failures" are scoring artifacts (format mismatch, keyword stemming, LaTeX output). True knowledge accuracy is higher than raw numbers suggest.

5. **2B is surprisingly capable for offline use** — if you stay within advisory/educational domains and away from protocol-specific recall.

6. **State-specific legal knowledge is a hard zero.** The model scores 0% on CA vehicle code penalties and DMV admin rules. This isn't partial knowledge — it's complete absence.

## Quick Start

```bash
git clone https://github.com/suryaakella/travelqa-bench.git
cd travelqa-bench

pip install mlx-vlm pandas tqdm
huggingface-cli download google/gemma-4-e2b-it-4bit --local-dir models/gemma-4-e2b-it-4bit

# Run any benchmark
python run_eval.py --raw-only          # Travel (500q)
python run_eval_v2.py                  # Offline use cases (60q)
python run_survival_eval.py            # Survival deep-dive (50q)
```

## File Structure

```
├── benchmark.json              # 500 travel questions
├── benchmark_v2.json           # 60 offline use case questions
├── survival_benchmark.json     # 50 survival questions
├── run_eval.py                 # Travel eval (MLX)
├── run_eval_v2.py              # Offline use case eval (MLX)
├── run_survival_eval.py        # Survival eval (MLX)
├── run_dmv_cactus.py           # DMV eval (Cactus engine)
├── score.py                    # Scoring + report gen
├── build_benchmark.py          # WikiVoyage scraper
├── results/
│   ├── report.md               # Travel results
│   ├── survival_report.md      # Survival results
│   └── dmv_report.md           # DMV results
└── sources/                    # Cached scraped data (gitignored)
```

## License

Benchmark data from [WikiVoyage](https://en.wikivoyage.org/) (CC BY-SA 3.0). Factual data from public sources (ITU, IEC, ISO 4217).
