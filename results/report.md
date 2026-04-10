# TravelQA Evaluation Report

Generated: 2026-04-10 03:12
Model: Gemma 4 E2B (4-bit quantized, MLX)
Platform: Apple M1, 16GB RAM

## Summary

| Metric | Raw | RAG | Delta |
|--------|-----|-----|-------|
| Overall Accuracy | 89.0% | — | -89.0% |
| Total Questions | 500 | — | |
| Parse Failures | 0 | 0 | |

## Per-Category Accuracy

| Category | Raw | RAG | Delta |
|----------|-----|-----|-------|
| cultural_norms | 100.0% (50/50) | — | -100.0% |
| currency | 100.0% (50/50) | — | -100.0% |
| emergency | 86.0% (43/50) | — | -86.0% |
| health | 98.0% (49/50) | — | -98.0% |
| infrastructure | 62.0% (31/50) | — | -62.0% |
| language | 84.0% (42/50) | — | -84.0% |
| safety | 90.0% (45/50) | — | -90.0% |
| scams | 100.0% (50/50) | — | -100.0% |
| transportation | 70.0% (35/50) | — | -70.0% |
| visa | 100.0% (50/50) | — | -100.0% |

## Per-Country Accuracy

| Country | Raw | RAG | Delta |
|---------|-----|-----|-------|
| Argentina | 87.5% | — | -87.5% |
| Australia | 96.2% | — | -96.2% |
| Brazil | 87.0% | — | -87.0% |
| China | 91.7% | — | -91.7% |
| Colombia | 86.7% | — | -86.7% |
| Cuba | 100.0% | — | -100.0% |
| Czech Republic | 100.0% | — | -100.0% |
| Egypt | 100.0% | — | -100.0% |
| Germany | 100.0% | — | -100.0% |
| Greece | 90.9% | — | -90.9% |
| India | 85.7% | — | -85.7% |
| Indonesia | 78.3% | — | -78.3% |
| Italy | 81.8% | — | -81.8% |
| Japan | 95.7% | — | -95.7% |
| Jordan | 100.0% | — | -100.0% |
| Kenya | 90.3% | — | -90.3% |
| Mexico | 88.5% | — | -88.5% |
| Morocco | 100.0% | — | -100.0% |
| Nepal | 100.0% | — | -100.0% |
| New Zealand | 100.0% | — | -100.0% |
| Norway | 87.1% | — | -87.1% |
| Peru | 100.0% | — | -100.0% |
| Philippines | 100.0% | — | -100.0% |
| South Africa | 76.9% | — | -76.9% |
| South Korea | 100.0% | — | -100.0% |
| Spain | 100.0% | — | -100.0% |
| Tanzania | 100.0% | — | -100.0% |
| Thailand | 91.7% | — | -91.7% |
| Turkey | 85.7% | — | -85.7% |
| United Arab Emirates | 88.0% | — | -88.0% |
| Vietnam | 76.5% | — | -76.5% |

## By Difficulty

| Difficulty | Raw | RAG | Delta |
|-----------|-----|-----|-------|
| easy | 90.9% (339/373) | — | -90.9% |
| medium | 83.5% (106/127) | — | -83.5% |
| hard | — | — | +0.0% |

## Error Analysis

### Raw Mode Errors

Category failure counts:
- infrastructure: 19 errors
- transportation: 15 errors
- language: 8 errors
- emergency: 7 errors
- safety: 5 errors
- health: 1 errors

## Key Findings
