# Future Enhancements for Long-Form Story Optimization

**Date:** 2025-11-07  
**Status:** TODO  
**Priority:** Medium

## Overview

Based on code review feedback, these enhancements would make the relevance scoring system more flexible and configurable.

## 1. Extract Hard-coded Scoring Weights

**Current:** Weights are hard-coded in `src/relevance_scorer.py`

```python
# Entity relevance (line 48)
score += recency_score * 0.4    # Recency weight
score += frequency_score * 0.2  # Frequency weight
score += outline_match * 0.3    # Outline match weight
score += importance * 0.1       # Importance weight
```

**Proposed:** Add to `config/config.yaml`

```yaml
relevance_scoring:
  entity_weights:
    recency: 0.4
    frequency: 0.2
    outline_match: 0.3
    importance: 0.1
  
  event_weights:
    recency: 0.4
    importance: 0.3
    character_overlap: 0.2
    entity_overlap: 0.1
  
  conflict_weights:
    urgency: 0.4
    freshness: 0.3
    character_involvement: 0.3
```

**Benefits:**
- Users can experiment with different weights
- Easy A/B testing
- Story-type specific tuning

**Implementation:**
- Add config section
- Load in `RelevanceScorer.__init__()`
- Use variables instead of constants

## 2. Configurable Recency Decay Values

**Current:** Decay values hard-coded (lines 128-137)

```python
if chapter_distance <= self.window_immediate:
    recency_score = 1.0
elif chapter_distance <= self.window_recent:
    recency_score = 0.8
# ... etc
```

**Proposed:**

```yaml
relevance_scoring:
  recency_decay:
    immediate: 1.0
    recent: 0.8
    medium: 0.5
    historical: 0.2
    old: 0.05
```

**Benefits:**
- Fine-tune decay curve
- Different for fast vs slow-paced stories

## 3. Configurable Thresholds

**Current:** Various thresholds hard-coded

```python
# Line 72: frequency normalization
max_frequency = min(current_chapter, 50)

# Line 336: importance threshold for old entities
if item['relevance'] > 0.8

# main.py lines 205-206: fallback limits
entity_limit = 20
event_limit = 10
```

**Proposed:**

```yaml
relevance_scoring:
  thresholds:
    max_frequency_cap: 50
    old_entity_importance: 0.8
    min_relevance: 0.05
  
  default_limits:
    entities: 20
    events: 10
    conflicts: 8
```

## 4. Configurable Conflict Batch Limits

**Current:** (lines 127-134 in `conflict_manager.py`)

```python
if current_batch <= 5:
    limit = 5
elif current_batch <= 20:
    limit = 8
# ... etc
```

**Proposed:**

```yaml
conflict_management:
  batch_limits:
    early: {max_batch: 5, limit: 5}
    mid_early: {max_batch: 20, limit: 8}
    mid_late: {max_batch: 40, limit: 12}
    late: {limit: 15}
```

## Implementation Plan

### Phase 1: Config Structure
1. Add new config sections to `config.yaml`
2. Update config schema documentation
3. Add validation

### Phase 2: Code Updates
1. Update `RelevanceScorer.__init__()` to load configs
2. Update `ConflictManager.__init__()` to load configs
3. Replace hard-coded values with config variables
4. Add default fallbacks

### Phase 3: Testing
1. Test with default values (should be same as current)
2. Test with different configurations
3. Validate backward compatibility

### Phase 4: Documentation
1. Update `LONG_FORM_USAGE_GUIDE.md` with new configs
2. Add examples for different story types
3. Document weight tuning guidelines

## Example Configurations

### Fast-Paced Action Story

```yaml
relevance_scoring:
  entity_weights:
    recency: 0.5      # Higher recency focus
    frequency: 0.15
    outline_match: 0.3
    importance: 0.05
  
  recency_decay:
    immediate: 1.0
    recent: 0.7       # Steeper decay
    medium: 0.3
    historical: 0.1
    old: 0.01
```

### Epic Saga with Long Arcs

```yaml
relevance_scoring:
  entity_weights:
    recency: 0.3      # Lower recency focus
    frequency: 0.3    # Higher frequency importance
    outline_match: 0.3
    importance: 0.1
  
  recency_decay:
    immediate: 1.0
    recent: 0.85      # Gentler decay
    medium: 0.6
    historical: 0.3
    old: 0.1
```

### Character-Driven Drama

```yaml
relevance_scoring:
  entity_weights:
    recency: 0.35
    frequency: 0.25
    outline_match: 0.25
    importance: 0.15  # Higher importance weight
  
  event_weights:
    recency: 0.3
    importance: 0.3
    character_overlap: 0.3  # Higher character focus
    entity_overlap: 0.1
```

## Priority

**Medium** - Current implementation works well, but these enhancements would:
- Make system more flexible
- Enable experimentation
- Support different story types better

## Estimated Effort

- Phase 1: 2 hours
- Phase 2: 4 hours
- Phase 3: 2 hours
- Phase 4: 2 hours
- **Total: 1-2 days**

## Notes

- All current functionality should remain as defaults
- Backward compatibility is critical
- Changes should be non-breaking
- Document weight tuning best practices

---

**Status:** Open for future implementation
**Created:** 2025-11-07
**Type:** Enhancement
