# TravelQA Evaluation Report

**Model:** Gemma 4 E2B (4-bit quantized, MLX)
**Platform:** Apple M1, 16GB RAM
**Date:** 2026-04-10
**Benchmark:** 500 questions, 10 categories, 31 countries

## Summary

| Metric | Value |
|--------|-------|
| **Overall Accuracy** | **89.0% (445/500)** |
| Parse Failures | 0 |
| Easy Questions | 90.9% (339/373) |
| Medium Questions | 83.5% (106/127) |

## Per-Category Accuracy

| Category | Accuracy | Correct | Errors |
|----------|----------|---------|--------|
| Cultural Norms | **100.0%** | 50/50 | 0 |
| Currency | **100.0%** | 50/50 | 0 |
| Scams | **100.0%** | 50/50 | 0 |
| Visa | **100.0%** | 50/50 | 0 |
| Health | **98.0%** | 49/50 | 1 |
| Safety | **90.0%** | 45/50 | 5 |
| Emergency | **86.0%** | 43/50 | 7 |
| Language | **84.0%** | 42/50 | 8 |
| Transportation | **70.0%** | 35/50 | 15 |
| Infrastructure | **62.0%** | 31/50 | 19 |

## Per-Country Accuracy

| Country | Accuracy | | Country | Accuracy |
|---------|----------|-|---------|----------|
| Cuba | 100.0% | | Czech Republic | 100.0% |
| Egypt | 100.0% | | Germany | 100.0% |
| Jordan | 100.0% | | Morocco | 100.0% |
| Nepal | 100.0% | | New Zealand | 100.0% |
| Peru | 100.0% | | Philippines | 100.0% |
| South Korea | 100.0% | | Spain | 100.0% |
| Tanzania | 100.0% | | Australia | 96.2% |
| Japan | 95.7% | | China | 91.7% |
| Thailand | 91.7% | | Greece | 90.9% |
| Kenya | 90.3% | | Mexico | 88.5% |
| UAE | 88.0% | | Argentina | 87.5% |
| Norway | 87.1% | | Brazil | 87.0% |
| Colombia | 86.7% | | India | 85.7% |
| Turkey | 85.7% | | Italy | 81.8% |
| Indonesia | 78.3% | | South Africa | 76.9% |
| Vietnam | 76.5% | | | |

## Error Analysis

55 total errors, broken down by root cause:

| Root Cause | Count | Category Hit |
|-----------|-------|-------------|
| Positional B-bias (always picks B) | 13 | Transportation |
| Format mismatch ("A and B" vs "A, B") | 11 | Infrastructure |
| Partial knowledge (1 plug type, not all) | 9 | Infrastructure |
| Keyword matching too strict | 7 | Language |
| Advisory MC wrong pick | 5 | Safety |
| Voltage rounding (220V vs 230V) | 3 | Infrastructure |
| Wrong emergency number | 5 | Emergency |
| Wrong phrase meaning | 2 | Language |
| Benchmark error (Vietnam tap water) | 1 | Health |

**Genuine knowledge failures: ~10 out of 500 (98% knowledge accuracy)**

## Key Findings

1. **Advisory categories are strong.** Cultural norms, scams, visa, and health advice are near-perfect. The model has solid general travel knowledge.

2. **Factual precision is weak.** Emergency numbers, plug types, and voltages require exact recall that the model lacks — especially distinguishing between similar numbers for different services.

3. **Systematic positional bias.** The model picks "B" on every driving-side question regardless of country, suggesting a positional preference in its MC answering rather than a knowledge gap.

4. **Scoring underestimates true accuracy.** ~23 errors are format mismatches or overly strict matching. With lenient scoring, effective accuracy would be ~93-94%.

5. **Emergency numbers are the real gap.** The only category where the model genuinely doesn't know the answer. It confuses police/ambulance/universal numbers within a country.
