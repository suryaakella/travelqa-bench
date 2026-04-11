# Survival Knowledge Benchmark — Evaluation Report

**Model:** Gemma 4 E2B (2B params, 4-bit quantized, MLX)
**Platform:** Apple M1, 16GB RAM
**Date:** 2026-04-11
**Benchmark:** 50 questions, 9 categories, keyword-match scoring

## Summary

| Metric | Value |
|--------|-------|
| **Overall Accuracy** | **80.0% (40/50)** |
| Easy Questions | 80% (8/10) |
| Medium Questions | 87% (20/23) |
| Hard Questions | 71% (12/17) |

## Per-Category Accuracy

| Category | Accuracy | Correct/Total | Key Gap |
|----------|----------|---------------|---------|
| Shelter | **100%** | 5/5 | — |
| Tools | **100%** | 4/4 | — |
| Water | **86%** | 6/7 | Altitude/boiling point relationship |
| First Aid | **83%** | 5/6 | Spinal injury (scoring artifact) |
| Food | **83%** | 5/6 | Survival time without food |
| Fire | **80%** | 4/5 | Doesn't know "fire lay" terminology |
| Signaling | **80%** | 4/5 | Doesn't know 3-blast distress signal |
| Navigation | **71%** | 5/7 | Watch method, Southern Cross method |
| Hazards | **40%** | 2/5 | River crossing, ice rescue, quicksand |

## Error Analysis

10 total failures, broken down by root cause:

| Root Cause | Count | Questions |
|-----------|-------|-----------|
| **Genuine knowledge gap** (wrong technique) | 5 | SUR-001, SUR-002, SUR-023, SUR-039, SUR-044 |
| **Vague/hedging** (knows concept, avoids specifics) | 3 | SUR-045, SUR-046, SUR-029 |
| **Scoring artifact** (correct info, keyword mismatch) | 2 | SUR-014, SUR-033 |

### Genuine Knowledge Gaps (Critical for Offline Use)

1. **Celestial navigation** — Cannot explain the analog watch method (point hour hand at sun, bisect with 12). Gives nonsensical advice about "magnetic markings" on a watch. Cannot explain Southern Cross extension method.

2. **Fire terminology** — Doesn't know what a "fire lay" is (confuses it with fire investigation reports). This is basic bushcraft vocabulary.

3. **Sound distress signals** — Doesn't know the universal 3-blast rule for sound distress signals.

4. **Hazard-specific procedures** — Gives generic advice for river crossing (misses: face upstream, use pole, diagonal path, unbuckle pack). Gives generic advice for ice rescue (misses: kick horizontal, roll away, spread weight).

### Vague/Hedging Responses

The model hedges on factual questions rather than committing to specific numbers:
- "How long without food?" → "varies drastically" instead of "approximately 3 weeks"
- "Quicksand escape?" → Generic "stay calm" instead of specific technique (lean back, spread weight, float, slow wiggle)

### Scoring Artifacts (Model is Actually Correct)

- SUR-014: Model discussed temperature correctly but didn't mention "altitude" keyword
- SUR-033: Model said "immobilization" but keyword expects "immobilize" (stemming issue)

**Adjusted accuracy (excluding scoring artifacts): 42/50 = 84%**

## Key Findings

1. **Shelter and tools knowledge is solid.** The model correctly explains debris huts, insulation techniques, knife sharpening, and cordage making.

2. **Water and first aid are strong.** Solar stills, SODIS, transpiration bags, tourniquets, chest seals — all correctly described with specific details.

3. **Celestial navigation is a critical gap.** The model cannot explain the two most important compass-free navigation methods (analog watch + Southern Cross). This is dangerous for offline survival use.

4. **Hazard response lacks procedural specificity.** The model gives safe but generic advice for emergencies (river crossing, ice rescue, quicksand). In survival scenarios, generic advice can be lethal — you need the specific procedure.

5. **The model hedges instead of committing.** On factual questions with known answers (3 weeks without food, 3 blasts for distress), it gives qualifiers instead of the standard answer. An offline survival assistant needs to be decisive.

## Recommendations for Deployment

If deploying Gemma 4 E2B as an offline survival assistant:

- **DO trust:** Shelter construction, water purification, fire starting, basic first aid, plant identification
- **DO NOT trust:** Celestial navigation methods, specific hazard procedures (river, ice, quicksand), distress signal protocols
- **Fine-tuning priority:** Navigation and hazards categories would benefit most from targeted training data (military field manuals, wilderness survival guides)

## Comparison to v1 TravelQA

| Benchmark | Questions | Accuracy | Genuine Gaps |
|-----------|-----------|----------|--------------|
| TravelQA v1 (travel knowledge) | 500 | 89% | ~10 (emergency numbers) |
| Survival Benchmark (offline use) | 50 | 80% | ~5 (navigation, hazards) |

The model is weaker on survival-specific procedural knowledge than on general travel advisory knowledge, as expected for a general-purpose 2B model.
