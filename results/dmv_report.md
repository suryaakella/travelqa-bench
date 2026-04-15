# California DMV Written Test — Evaluation Report

**Model:** Gemma 4 E2B (2B params, INT4 quantized)
**Engine:** Cactus (low-latency inference)
**Platform:** Apple M1, 16GB RAM
**Date:** 2026-04-14
**Benchmark:** 40 questions from CA DMV Class C practice tests 1-4

## Summary

| Metric | Value |
|--------|-------|
| **Overall Accuracy** | **37.5% (15/40)** |
| Easy Questions | 44% (11/25) |
| Medium Questions | 31% (4/13) |
| Hard Questions | 0% (0/2) |
| **CA DMV Passing Score** | **83% (30/36)** |
| **Verdict** | **FAIL — would not pass DMV test** |

## Per-Category Accuracy

| Category | Accuracy | Correct/Total |
|----------|----------|---------------|
| Parking | **80%** | 4/5 |
| Right of Way | **67%** | 2/3 |
| Safe Driving | **43%** | 3/7 |
| Rules of Road | **38%** | 6/16 |
| Admin/DMV | **0%** | 0/3 |
| Laws/Penalties | **0%** | 0/6 |

## Performance

| Metric | Cactus | MLX-VLM (previous) |
|--------|--------|---------------------|
| Model load time | 12s | 140s |
| Avg per question | ~1-10s | ~8s |

## Error Analysis

25 failures broken down:

| Error Type | Count | Examples |
|-----------|-------|---------|
| **Wrong answer** (picked wrong choice) | 18 | School bus, tailgater, truck blind spots |
| **Parse failure** (no letter extracted) | 7 | Thinking mode consumed all tokens |

### Genuine Knowledge Gaps

1. **Laws & Penalties (0%)** — Cannot recall specific CA legal penalties (prison time for evading police), driving hours for minors, headset laws, open container rules, cell phone laws, or crossing guard rules.

2. **Admin/DMV (0%)** — Gets all DMV notification rules wrong (SR-1 filing, vehicle transfer).

3. **Specific numbers** — Wrong on railroad crossing speed (said 10mph, correct is 15mph), headlight distance (500 feet), minor driving hours (5am-11pm).

4. **Common driving knowledge** — Gets truck blind spots wrong twice, school bus yellow lights (should slow down, not stop), tailgater response (should change lanes, not tap brakes).

### What It Gets Right

- Parallel parking procedure
- Red curb = no stopping
- Right turn ending lane
- Basic speed law
- Crosshatched areas = no parking
- Green light blocked intersection = don't enter
- Railroad track crossing = wait until clear
- One-way left turn = far-left lane

## Key Takeaway

A 2B model **cannot pass the California DMV written test**. It scores 37.5% against a required 83%. The model knows basic driving concepts but lacks recall of specific CA vehicle code rules, legal penalties, and exact regulatory numbers. This is a domain (state-specific legal knowledge) where small models fundamentally lack training data coverage.
