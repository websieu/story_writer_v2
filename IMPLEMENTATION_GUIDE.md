# Quick Reference: TODO Items Implementation Guide

Hướng dẫn nhanh cho developers implement các TODO items.

## 🚨 START HERE - Phase 1 (CRITICAL)

### Item 1: Fix Batch 2+ Entity/Event Retrieval

**Files to modify:**
- `src/entity_manager.py`
- `main.py`

**Changes needed:**

1. Add method in `EntityManager`:
```python
def _update_entity_appearances(self, chapter_content: str, chapter_num: int):
    """Auto-update appear_in_chapters"""
    # Implementation in TODO.MD line 60-75
```

2. Modify `get_relevant_entities()`:
```python
# Add logic to include:
# - Entities from last 2-3 chapters
# - Main characters (appear >= 5 chapters)
# See TODO.MD line 92-115
```

3. Add in `EntityManager`:
```python
def get_frequently_used_entities(self, min_chapters: int = 3):
    # See TODO.MD line 117-128
```

4. Update `main.py._prepare_batch_context()`:
```python
# Add frequent_entities and recent_entities
# See TODO.MD line 130-154
```

**Test:**
```bash
python main.py --story-id test_batch2 --batches 2
# Verify batch 2 has entities from batch 1
```

---

### Item 2: Entity/Event Relevance Scoring

**Files to modify:**
- `src/entity_manager.py`
- `src/post_processor.py`

**Add method:**
```python
def score_entity_relevance(self, entity, chapter_num, character_names):
    # See TODO.MD line 198-222
```

**Add time decay for events:**
```python
def get_events_by_entities(self, entity_names, current_chapter, max_events):
    # See TODO.MD line 227-250
```

**Test:**
```bash
# Check entities are ranked by relevance
# Check recent events weighted higher
```

---

### Item 7: Entity Name Validation

**New file:** `src/validators/entity_name_validator.py`

**Add class:**
```python
class EntityNameValidator:
    # See TODO.MD line 495-522
```

**Modify:** `src/entity_manager.py`
```python
def _validate_and_filter_entities(self, entities, validator):
    # See TODO.MD line 555-576
```

**Update extraction prompt:**
```python
# Add naming rules to prompt
# See TODO.MD line 527-552
```

**Test:**
```bash
# Try to extract entity with generic name
# Should be rejected with warning
```

---

## 📊 Phase 2 (Core Improvements)

### Item 5: CharacterManager

**New file:** `src/character_manager.py`

**Add class:**
```python
class CharacterManager:
    def get_character_stats(self, current_chapter):
        # See TODO.MD line 313-353
    
    def should_introduce_new_character(self, current_chapter):
        # See TODO.MD line 355-369
```

**Test:**
```bash
# Generate 30 chapters
# Verify character count stays under 15 active
```

---

### Item 8: ConflictValidator

**New file:** `src/validators/conflict_validator.py`

**Add class:**
```python
class ConflictValidator:
    def validate_timeline(self, conflict, current_chapter):
        # See TODO.MD line 603-633
    
    def verify_resolution(self, content, conflict_id, desc):
        # See TODO.MD line 638-660
```

**Test:**
```bash
# Check overdue conflicts are flagged
# Verify resolution verification works
```

---

### Item 3: 300-Chapter Adjustments

**Modify:** `config/config.yaml`
```yaml
conflict_timelines:
  immediate: 1
  batch: 5
  arc: 20
  volume: 50
  saga: 150
  epic: 300
```

**New file:** `src/arc_manager.py`
```python
class ArcManager:
    # See TODO.MD line 295-317
```

**Modify:** `src/post_processor.py`
```python
# Implement hierarchical summaries
# See TODO.MD line 273-282
```

---

## 🎨 Phase 3 (Advanced Features)

### Item 4: PacingManager

**New file:** `src/pacing_manager.py`

**Update:** `config/config.yaml`
```yaml
story_pacing:
  # See TODO.MD line 347-368
```

**Add class:**
```python
class PacingManager:
    def get_batch_style(self, batch_num):
        # See TODO.MD line 373-398
```

---

### Item 6: EndingManager

**New file:** `src/ending_manager.py`

**Update:** `config/config.yaml`
```yaml
story_structure:
  # See TODO.MD line 428-452
```

**Add class:**
```python
class EndingManager:
    def get_ending_guidance(self, chapter_num):
        # See TODO.MD line 457-482
```

---

## 🔧 Utilities

### Create Validators Directory
```bash
mkdir -p src/validators
touch src/validators/__init__.py
```

### Run Tests
```bash
# After each phase
python -m pytest tests/
python main.py --story-id test_project --batches 3
```

### Check Metrics
```python
from src.utils import Logger
logger = Logger("Test")
# Check logs for entity retrieval rates
# Check character counts
# Check conflict resolution
```

---

## 📝 Checklist Before PR

- [ ] All Phase 1 items implemented
- [ ] Tests passing
- [ ] No breaking changes to existing projects
- [ ] Documentation updated
- [ ] Config has sensible defaults
- [ ] Feature flags added
- [ ] Performance profiled

---

## 🐛 Common Issues

**Issue:** Batch 2 still missing entities
**Fix:** Check `_update_entity_appearances()` is called after chapter extraction

**Issue:** Too many entities returned
**Fix:** Adjust `max_entities` parameter or scoring thresholds

**Issue:** Generic entity names still passing
**Fix:** Add more patterns to `GENERIC_NAMES` dict

**Issue:** Conflicts marked overdue incorrectly
**Fix:** Check timeline calculation in `validate_timeline()`

---

## 📚 Further Reading

- [TODO.MD](TODO.MD) - Complete analysis and solutions
- [TODO_ANALYSIS_SUMMARY.md](TODO_ANALYSIS_SUMMARY.md) - Executive summary
- [README.md](README.md) - System overview

---

**Questions?** Check TODO.MD for detailed explanations and code examples.
