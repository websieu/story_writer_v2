# System Architecture Diagram - Long-Form Story Optimization

## Before Optimization (v1.3.1)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Chapter Writing Flow                         │
│                        (Chapter 250)                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌─────────┐      ┌─────────┐     ┌──────────┐
   │ Get ALL │      │ Get ALL │     │ Get ALL  │
   │Entities │      │ Events  │     │Conflicts │
   │  (200+) │      │  (100+) │     │  (50+)   │
   └────┬────┘      └────┬────┘     └─────┬────┘
        │                │                 │
        │                │                 │
        ▼                ▼                 ▼
   ┌─────────────────────────────────────────┐
   │   Simple filtering by character name    │
   │   - No recency consideration            │
   │   - No importance scoring               │
   │   - Fixed limit (20 entities)           │
   └─────────────┬───────────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │ Context Size:  │
        │  40,000+ tokens│  ← PROBLEM!
        │                │
        │ Issues:        │
        │ • Too large    │
        │ • Old info     │
        │ • Not relevant │
        └────────────────┘
```

## After Optimization (v1.4.0)

```
┌─────────────────────────────────────────────────────────────────┐
│              Chapter Writing Flow (Chapter 250)                  │
│              With Relevance Scoring & Sliding Window             │
└────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬────────────────┐
        │                │                │                │
        ▼                ▼                ▼                ▼
   ┌─────────┐      ┌─────────┐     ┌──────────┐    ┌─────────┐
   │ Get ALL │      │ Get ALL │     │ Get ALL  │    │Get Story│
   │Entities │      │ Events  │     │Conflicts │    │  Phase  │
   │  (200+) │      │  (100+) │     │  (50+)   │    │         │
   └────┬────┘      └────┬────┘     └─────┬────┘    └────┬────┘
        │                │                 │              │
        │                │                 │              │
        ▼                ▼                 ▼              ▼
   ┌─────────────────────────────────────────────────────────┐
   │            RELEVANCE SCORER                              │
   │  ┌─────────────────────────────────────────────────┐   │
   │  │ Entity Scoring (0-1):                            │   │
   │  │  • Recency (40%): Last appearance distance      │   │
   │  │  • Frequency (20%): Appearance count            │   │
   │  │  • Outline match (30%): In current outline?     │   │
   │  │  • Importance (10%): Base importance            │   │
   │  └─────────────────────────────────────────────────┘   │
   │  ┌─────────────────────────────────────────────────┐   │
   │  │ Event Scoring (0-1):                             │   │
   │  │  • Recency (40%)                                 │   │
   │  │  • Importance (30%)                              │   │
   │  │  • Character overlap (20%)                       │   │
   │  │  • Entity overlap (10%)                          │   │
   │  └─────────────────────────────────────────────────┘   │
   │  ┌─────────────────────────────────────────────────┐   │
   │  │ Conflict Priority (0-1):                         │   │
   │  │  • Timeline urgency (40%)                        │   │
   │  │  • Freshness (30%)                               │   │
   │  │  • Character involvement (30%)                   │   │
   │  └─────────────────────────────────────────────────┘   │
   └───────────────────────┬─────────────────────────────────┘
                           │
                           ▼
   ┌──────────────────────────────────────────────────────────┐
   │           SLIDING WINDOW FILTER                           │
   │                                                            │
   │  Immediate (ch 245-250): ████████████ 100% included       │
   │  Recent    (ch 230-244): ██████████   80% included        │
   │  Medium    (ch 200-229): ██████       50% included        │
   │  Historical(ch 150-199): ███          20% included        │
   │  Old       (ch < 150):   █             5% if important    │
   └───────────────────────┬──────────────────────────────────┘
                           │
                           ▼
   ┌──────────────────────────────────────────────────────────┐
   │           ADAPTIVE LIMITS (Story Phase)                   │
   │                                                            │
   │  Phase: Development (66.7% progress)                      │
   │    • Entities: 35 (was 20)                                │
   │    • Events: 20 (was 10)                                  │
   │    • Conflicts: 12 (was unlimited)                        │
   └───────────────────────┬──────────────────────────────────┘
                           │
                           ▼
   ┌──────────────────────────────────────────────────────────┐
   │           CONFLICT PRUNING                                │
   │                                                            │
   │  Before: 50 active conflicts                              │
   │  Pruned: 3 stale conflicts (>100 ch inactive)             │
   │  After: 8 prioritized conflicts                           │
   └───────────────────────┬──────────────────────────────────┘
                           │
                           ▼
        ┌───────────────────────────┐
        │ Optimized Context:        │
        │   6,500 tokens            │  ← SOLVED!
        │                           │
        │ Benefits:                 │
        │ • 84% smaller             │
        │ • Highly relevant         │
        │ • Recent focus            │
        │ • Phase-appropriate       │
        └───────────────────────────┘
```

## Scoring Example: Entity at Chapter 250

```
Entity: "Lý Hạo" (Main Character)
─────────────────────────────────

Appear in chapters: [1, 5, 10, 15, 20, 50, 100, 150, 200, 245, 250]

Factor 1: Recency (40%)
├─ Last appearance: chapter 250
├─ Distance: 0 chapters
└─ Score: 1.0 × 0.4 = 0.40  ✓

Factor 2: Frequency (20%)
├─ Total appearances: 11
├─ Normalized: 11/50 = 0.22
└─ Score: 0.22 × 0.2 = 0.04  ✓

Factor 3: Outline Match (30%)
├─ In chapter 250 outline? YES
└─ Score: 1.0 × 0.3 = 0.30  ✓

Factor 4: Importance (10%)
├─ Base importance: 0.9
└─ Score: 0.9 × 0.1 = 0.09  ✓

TOTAL RELEVANCE: 0.83  → HIGH PRIORITY ✓
```

## Scoring Example: Old Entity at Chapter 250

```
Entity: "Vương Lão Đầu" (Minor Character from early chapters)
──────────────────────────────────────────────────────────────

Appear in chapters: [3, 4, 5]

Factor 1: Recency (40%)
├─ Last appearance: chapter 5
├─ Distance: 245 chapters
└─ Score: 0.05 × 0.4 = 0.02  ✗ (very old)

Factor 2: Frequency (20%)
├─ Total appearances: 3
├─ Normalized: 3/50 = 0.06
└─ Score: 0.06 × 0.2 = 0.01  ✗ (rare)

Factor 3: Outline Match (30%)
├─ In chapter 250 outline? NO
└─ Score: 0.0 × 0.3 = 0.00  ✗ (not mentioned)

Factor 4: Importance (10%)
├─ Base importance: 0.3
└─ Score: 0.3 × 0.1 = 0.03  ✗ (minor)

TOTAL RELEVANCE: 0.06  → FILTERED OUT ✗
```

## Conflict Pruning Flow

```
At Chapter 250:
───────────────

Active Conflicts (before pruning): 50
│
├─ Immediate conflicts (timeline: 1 ch)
│  ├─ Introduced: ch 250
│  ├─ Last mentioned: ch 250
│  └─ Status: ACTIVE ✓ (not stale)
│
├─ Batch conflicts (timeline: 5 ch)
│  ├─ Introduced: ch 245
│  ├─ Last mentioned: ch 248
│  └─ Status: ACTIVE ✓ (only 2 ch inactive, threshold is 10)
│
├─ Short-term conflicts (timeline: 10 ch)
│  ├─ Introduced: ch 200
│  ├─ Last mentioned: ch 210
│  └─ Status: PRUNED ✗ (40 ch inactive > 30 threshold)
│
├─ Medium-term conflicts (timeline: 30 ch)
│  ├─ Introduced: ch 100
│  ├─ Last mentioned: ch 120
│  └─ Status: PRUNED ✗ (130 ch inactive > 100 threshold)
│
└─ Long-term conflicts (timeline: 100 ch)
   ├─ Introduced: ch 50
   ├─ Last mentioned: ch 50
   └─ Status: ACTIVE ✓ (never pruned)

Result:
───────
Active: 8 conflicts (prioritized by scoring)
Pruned: 3 conflicts (auto-resolved as "abandoned")
```

## Adaptive Limits by Phase

```
Story Progress Chart (300 chapters total):
───────────────────────────────────────────

Chapter Range │ Phase         │ Entities │ Events │ Conflicts
──────────────┼───────────────┼──────────┼────────┼──────────
1 - 30        │ Introduction  │    15    │   8    │    5
31 - 90       │ Rising Action │    25    │   15   │    8
91 - 210      │ Development   │    35    │   20   │   12     ← Peak
211 - 270     │ Climax        │    30    │   25   │   15
271 - 300     │ Resolution    │    20    │   15   │    8

Reasoning:
──────────
• Introduction: Small cast, establish world
• Rising Action: Build complexity
• Development: Peak complexity, multiple arcs
• Climax: Focus on resolution, high event density
• Resolution: Narrow to main threads
```

## Token Savings Over Story Length

```
Token Usage Comparison (Context Size):
──────────────────────────────────────

50K │                                           
    │                                         • Without optimization
40K │                                       •
    │                                     •
30K │                                   •
    │                                 •
20K │                               •
    │                             •
10K │                           •
    │  • • • • • • • • • • • • • • • • • • •  With optimization
 0  └─────────────────────────────────────────→
    1   50  100  150  200  250  300 (chapters)

Savings at Chapter 250: 84%
Average savings (ch 100-300): 75%
```

---

**Legend:**
- ✓ = Included
- ✗ = Filtered out
- • = Data point
- █ = Percentage bar

**Version:** 1.0  
**Date:** 2025-11-07
