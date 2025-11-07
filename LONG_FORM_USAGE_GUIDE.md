# Long-Form Story Optimization - Usage Guide

**Version:** 1.0  
**Date:** 2025-11-07  
**For System Version:** 1.4.0+

## 📖 Overview

This guide explains how to use the new relevance scoring and conflict management features for generating long-form stories (300+ chapters).

## 🎯 What's New

### 1. Relevance Scoring System
Automatically scores entities, events, and conflicts based on:
- **Recency**: How recently was it mentioned?
- **Frequency**: How often does it appear?
- **Context relevance**: Is it mentioned in the chapter outline?
- **Importance**: Base importance score

### 2. Sliding Window Approach
Prioritizes recent content over historical content:
- **Immediate** (last 5 chapters): 100% included
- **Recent** (5-20 chapters ago): 80% included
- **Medium** (20-50 chapters ago): 50% included
- **Historical** (50-100 chapters ago): 20% included
- **Old** (>100 chapters ago): Only if very important

### 3. Conflict Management
- Automatic pruning of stale conflicts
- Priority-based selection
- Timeline-based urgency calculation

### 4. Adaptive Limits
Context limits adjust based on story phase:
- **Introduction** (0-10%): Smaller context
- **Development** (30-70%): Larger context
- **Resolution** (90-100%): Focused context

## 🚀 Getting Started

### Step 1: Update Configuration

The optimizations are **enabled by default** in `config/config.yaml`:

```yaml
story:
  total_planned_chapters: 300  # Set your target
  
  # Context windows (in chapters)
  context_windows:
    immediate: 5      # Adjust as needed
    recent: 20
    medium: 50
    historical: 100
  
  # Feature flags
  use_relevance_scoring: true    # Enable relevance scoring
  use_sliding_window: true       # Enable sliding window
  use_conflict_pruning: true     # Enable conflict pruning
  use_adaptive_limits: true      # Enable adaptive limits
```

### Step 2: Generate Story Normally

No changes needed to your workflow:

```bash
# Generate a long story (60 batches = 300 chapters)
python main.py --project-id long_story_001 --batches 60
```

The system will automatically:
- ✅ Use relevance scoring for entities and events
- ✅ Apply sliding window to focus on recent content
- ✅ Prune stale conflicts automatically
- ✅ Adjust limits based on story progress

### Step 3: Monitor in Logs

Check logs to see the optimizations in action:

```
INFO - Context prepared for chapter 150: 28 entities, 18 events
INFO - Batch 31 context: 8 conflicts, 15 characters, 20 entities
INFO - Pruned 3 stale conflicts at chapter 155
```

## 📊 Configuration Options

### 1. Adjust Context Windows

For a faster-paced story (more recency focus):

```yaml
context_windows:
  immediate: 3      # Tighter focus
  recent: 10
  medium: 30
  historical: 50
```

For a slower-paced story (more historical context):

```yaml
context_windows:
  immediate: 10     # Broader focus
  recent: 40
  medium: 100
  historical: 200
```

### 2. Adjust Total Planned Chapters

If you plan a different length:

```yaml
story:
  total_planned_chapters: 500  # For a 500-chapter story
```

This affects:
- Adaptive limit calculations
- Story phase detection
- Conflict timeline scaling

### 3. Disable Specific Features

If you want to test without certain optimizations:

```yaml
story:
  use_relevance_scoring: false   # Disable scoring
  use_sliding_window: false      # Disable windowing
  use_conflict_pruning: false    # Disable pruning
  use_adaptive_limits: false     # Use fixed limits
```

## 🔍 Understanding the Impact

### Token Usage Comparison

**Without Optimizations:**
```
Chapter 50:   ~8,000 tokens in context
Chapter 100:  ~15,000 tokens in context
Chapter 200:  ~30,000 tokens in context
Chapter 250:  ~40,000+ tokens (may exceed limits!)
```

**With Optimizations:**
```
Chapter 50:   ~4,000 tokens in context
Chapter 100:  ~5,500 tokens in context
Chapter 200:  ~6,000 tokens in context
Chapter 250:  ~6,500 tokens in context
```

**Savings: ~84% at chapter 250**

### Quality Impact

**Before:**
- Context polluted with irrelevant old entities
- Events from 200 chapters ago given same weight as recent
- Conflicts accumulate without resolution
- Fixed limits cause information loss

**After:**
- Context focused on relevant recent content
- Recent events prioritized appropriately
- Stale conflicts automatically pruned
- Adaptive limits match story complexity

## 🎨 Advanced Usage

### 1. Custom Scoring Weights

To modify how relevance is calculated, edit `src/relevance_scorer.py`:

```python
# In calculate_entity_relevance()
score += recency_score * 0.4   # Change from 0.4 to 0.5 for more recency focus
score += frequency_score * 0.2
score += outline_match * 0.3
score += importance * 0.1
```

### 2. Custom Pruning Thresholds

To modify when conflicts get pruned, edit `src/conflict_manager.py`:

```python
self.pruning_thresholds = {
    'immediate': 5,      # Prune after 5 chapters (was 10)
    'batch': 10,         # Prune after 10 chapters (was 10)
    'short_term': 20,    # Prune after 20 chapters (was 30)
    'medium_term': 50,   # Prune after 50 chapters (was 100)
    'long_term': None,
    'epic': None
}
```

### 3. Monitor Scoring in Detail

Add debug logging:

```python
# In main.py, add after getting scored entities:
for entity in related_entities[:5]:
    relevance = self.relevance_scorer.calculate_entity_relevance(
        entity, chapter_num, chapter_outline
    )
    self.logger.debug(f"Entity '{entity['name']}': relevance={relevance:.3f}")
```

## 📈 Best Practices

### 1. Set Realistic Total Chapters

```yaml
# If you're not sure how long the story will be:
total_planned_chapters: 300  # Conservative estimate
```

The system adapts dynamically, so you can go beyond this if needed.

### 2. Monitor Conflict Count

Check logs for conflict pruning:
- If too many conflicts are pruned: Increase pruning thresholds
- If conflicts accumulate: Decrease pruning thresholds

### 3. Review Periodically

After every 50 chapters:
1. Check `output/cost_summary.json` for token usage trends
2. Review chapter quality
3. Adjust configuration if needed

### 4. Use Story Arcs

For very long stories (500+ chapters), consider:
- Breaking into arcs of 100 chapters each
- Using separate project IDs per arc
- Copying key entities/conflicts between arcs

## 🐛 Troubleshooting

### Issue: Too Few Entities in Context

**Symptom:** Chapter feels disconnected, missing important characters

**Solution:**
1. Check if `use_sliding_window: true` is too aggressive
2. Increase window sizes:
   ```yaml
   context_windows:
     recent: 30      # Was 20
     medium: 75      # Was 50
   ```
3. Or disable sliding window for that batch:
   ```yaml
   use_sliding_window: false
   ```

### Issue: Too Many Entities Still

**Symptom:** Context still large, high token usage

**Solution:**
1. Decrease adaptive limits:
   - Edit `src/relevance_scorer.py` 
   - In `get_adaptive_limits()`, reduce values:
     ```python
     'development': {
         'entities': 25,  # Was 35
         'events': 15,    # Was 20
         'conflicts': 10   # Was 12
     }
     ```

### Issue: Important Conflict Was Pruned

**Symptom:** A key conflict disappeared unexpectedly

**Solution:**
1. Check logs for pruning events
2. Increase pruning threshold for that timeline
3. Or mark it as `long_term` or `epic` (never pruned):
   ```python
   # In conflicts.json
   {
     "timeline": "epic",  # Changed from "medium_term"
     ...
   }
   ```

### Issue: Story Feels Rushed

**Symptom:** Too much focus on immediate events, lost big picture

**Solution:**
1. Increase historical window influence:
   ```yaml
   context_windows:
     historical: 150  # Was 100
   ```
2. Or adjust relevance weights to favor frequency over recency

## 📚 Examples

### Example 1: Standard 300-Chapter Story

```yaml
# config/config.yaml
story:
  total_planned_chapters: 300
  context_windows:
    immediate: 5
    recent: 20
    medium: 50
    historical: 100
  use_relevance_scoring: true
  use_sliding_window: true
  use_conflict_pruning: true
  use_adaptive_limits: true
```

```bash
# Generate
python main.py --project-id standard_300 --batches 60
```

### Example 2: Epic 500-Chapter Story

```yaml
# config/config.yaml
story:
  total_planned_chapters: 500
  context_windows:
    immediate: 10      # Broader
    recent: 40
    medium: 100
    historical: 200
  use_relevance_scoring: true
  use_sliding_window: true
  use_conflict_pruning: true
  use_adaptive_limits: true
```

```bash
# Generate
python main.py --project-id epic_500 --batches 100
```

### Example 3: Fast-Paced 200-Chapter Story

```yaml
# config/config.yaml
story:
  total_planned_chapters: 200
  context_windows:
    immediate: 3       # Tighter
    recent: 10
    medium: 30
    historical: 60
  use_relevance_scoring: true
  use_sliding_window: true
  use_conflict_pruning: true
  use_adaptive_limits: true
```

```bash
# Generate
python main.py --project-id fast_200 --batches 40
```

## 🔗 Related Documentation

- **Technical Analysis:** See `LONG_FORM_STORY_ANALYSIS.md` for detailed analysis
- **System Architecture:** See `ARCHITECTURE.md` for overall system design
- **Entity Optimization:** See `ENTITY_FILTERING_OPTIMIZATION.md` for entity filtering details

## 📝 Changelog

### Version 1.0 (2025-11-07)
- Initial release
- Relevance scoring system
- Sliding window approach
- Conflict management with pruning
- Adaptive limits based on story phase

---

**Questions or Issues?**
- Check `LONG_FORM_STORY_ANALYSIS.md` for technical details
- Review logs in `projects/{project_id}/logs/`
- Adjust configuration as needed

**Happy Writing! 📖✨**
