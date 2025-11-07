# Đánh giá Logic Write Chapter cho Truyện Dài 300 Chương

**Ngày:** 2025-11-07  
**Phiên bản hệ thống:** 1.3.1

## 📋 Tổng quan

Tài liệu này đánh giá xem logic lựa chọn entity và event hiện tại có đủ chặt chẽ để viết truyện dài 300 chương hay không, và đề xuất các tối ưu hóa cần thiết.

---

## 🔍 Phân tích hiện trạng

### 1. Entity Selection Logic

#### ✅ Điểm mạnh hiện tại

1. **Chapter-based filtering** (v1.3.1):
   - Đã có `appear_in_chapters` field để track entity xuất hiện ở chương nào
   - Filter entities theo chapter number trong `_filter_entities_by_chapter()`
   - Giảm 40-65% token consumption

2. **Category-based organization**:
   - Phân loại rõ ràng: characters, locations, items, techniques, beasts, factions
   - Dễ quản lý và truy xuất

3. **Merge mechanism**:
   - Tự động merge entities trùng lặp
   - Track descriptions qua nhiều chapters

#### ❌ Vấn đề cho truyện 300 chương

**Vấn đề 1: Không có Recency Weight**

```python
# Hiện tại trong ChapterWriter._get_entities_from_outline()
if chapter_num in entity.get('appear_in_chapters', []):
    full_entities.append(entity)  # Thêm entity mà không có scoring
```

**Tác động:**
- Entity từ chapter 1 và chapter 299 được đối xử như nhau khi viết chapter 300
- Không ưu tiên entities gần đây hơn
- Context bị loãng với thông tin cũ không còn relevant

**Vấn đề 2: Fixed Limits Không Adaptive**

```python
# Trong EntityManager.get_relevant_entities()
return relevant[:max_entities]  # Hard limit 20 entities
```

**Tác động:**
- 20 entities có thể đủ cho batch đầu (chương 1-5)
- Không đủ cho chapter 250 với hàng trăm entities đã xuất hiện
- Không scale theo độ phức tạp của story

**Vấn đề 3: Không có Importance Scoring**

```python
# Entities không có importance field
{
    "name": "Lý Hạo",
    "description": "...",
    "appear_in_chapters": [1, 5, 10, 50, 100]
    # Thiếu: "importance": 0.9
    # Thiếu: "last_mentioned_chapter": 100
    # Thiếu: "mention_frequency": 0.8
}
```

**Tác động:**
- Không phân biệt được nhân vật chính vs nhân vật phụ
- Entity xuất hiện 1 lần = entity xuất hiện 100 lần
- Không thể prioritize khi context đầy

**Vấn đề 4: Không có Sliding Window**

```python
# Lấy tất cả entities trong appear_in_chapters
# Không có focus vào chapters gần đây
```

**Tác động:**
- Khi ở chapter 250, vẫn load entities từ chapter 1-5
- Context window tràn với thông tin cũ
- Chi phí token tăng không cần thiết

---

### 2. Event Selection Logic

#### ✅ Điểm mạnh hiện tại

1. **Importance scoring** (0-1):
   - Events có importance score
   - Được sort theo importance

2. **Characters/entities linking**:
   - Track characters_involved và entities_involved
   - Filter theo nhân vật trong outline

#### ❌ Vấn đề cho truyện 300 chương

**Vấn đề 1: No Recency Consideration**

```python
# Trong main.py._get_relevant_events()
all_events = sorted(
    self.post_processor.events,
    key=lambda x: x.get('importance', 0),  # Chỉ sort theo importance
    reverse=True
)
```

**Tác động:**
- Event importance=0.9 từ chapter 10 được ưu tiên hơn event importance=0.8 từ chapter 298
- Không phù hợp với narrative flow
- Context bị lấn át bởi historical events

**Vấn đề 2: Fixed Limit Without Adaptation**

```python
return relevant[:10]  # Top 10 relevant events - fixed
```

**Tác động:**
- 10 events không đủ thể hiện story arc phức tạp ở chapter 200
- Có thể bỏ sót events quan trọng gần đây

**Vấn đề 3: No Decay Mechanism**

```python
# Events không có decay theo thời gian
# Event từ 200 chapters trước vẫn có importance nguyên bản
```

**Tác động:**
- Old events giữ importance cao mãi mãi
- Không phản ánh sự thay đổi của narrative
- Context pollution

**Vấn đề 4: No Event Relationship Tracking**

```python
# Không track event nào dẫn đến event nào
# Không có causal chain
{
    "description": "Trận chiến X",
    "importance": 0.9,
    "chapter": 150
    # Thiếu: "causes": [event_id_1, event_id_2]
    # Thiếu: "caused_by": [event_id_0]
}
```

**Tác động:**
- Không thể chọn events theo mạch nhân quả
- Mất logic liên kết giữa events

---

### 3. Conflict Management Logic

#### ✅ Điểm mạnh hiện tại

1. **Timeline-based classification**:
   - immediate, batch, short_term, medium_term, long_term, epic
   - Phù hợp cho planning truyện dài

2. **Status tracking**:
   - active/resolved status
   - Resolution chapter tracking

3. **Conflict analysis trong OutlineGenerator**:
   - `_analyze_conflicts_for_batch()` phân tích conflicts nào cần resolve
   - LLM-driven conflict planning

#### ❌ Vấn đề cho truyện 300 chương

**Vấn đề 1: Unbounded Conflict Accumulation**

```python
# Trong PostChapterProcessor.get_unresolved_conflicts()
return [c for c in self.conflicts if c.get('status') == 'active']
```

**Tác động:**
- Ở chapter 250, có thể có 100+ active conflicts
- Không có automatic pruning
- Context overload

**Vấn đề 2: No Priority Scoring**

```python
# Conflicts không có priority field
{
    "id": "conflict_ch5_1",
    "timeline": "long_term",
    "status": "active"
    # Thiếu: "priority": 0.8
    # Thiếu: "stale_since_chapter": 200  # Không tiến triển từ chapter 200
}
```

**Tác động:**
- Không thể prioritize conflicts quan trọng
- Conflicts lặp đi lặp lại không được giải quyết

**Vấn đề 3: Timeline Không Adaptive**

```python
# Timeline definitions cố định
"epic": 300 chapters  # Cố định, không scale
```

**Tác động:**
- Nếu story > 300 chapters thì sao?
- Không flexible với story length

**Vấn đề 4: No Arc-based Grouping**

```python
# Conflicts không được group theo story arc
# Tất cả conflicts treated equally
```

**Tác động:**
- Khó quản lý conflicts trong các arc khác nhau
- Không thể focus vào current arc

---

### 4. Context Preparation Logic

#### ✅ Điểm mạnh hiện tại

1. **Comprehensive context**:
   - Motif, entities, events, summaries, conflicts
   - Previous chapter ending

2. **Super summary**:
   - Condensed overall story summary
   - Updated after each chapter

#### ❌ Vấn đề cho truyện 300 chương

**Vấn đề 1: Context Size Explosion**

```python
# Trong main.py._prepare_chapter_context()
context = {
    'related_entities': related_entities,  # Tất cả entities liên quan
    'related_events': related_events,      # Tất cả events liên quan
    ...
}
```

**Tính toán:**
- Chapter 1-10: ~20 entities, ~10 events = ~3K tokens
- Chapter 100: ~100 entities, ~50 events = ~15K tokens
- Chapter 250: ~200+ entities, ~100+ events = **~30K+ tokens**

**Tác động:**
- Vượt context window của nhiều models
- Chi phí API tăng exponentially
- Response quality giảm do context overload

**Vấn đề 2: No Arc/Phase Awareness**

```python
# Không có concept của story arc hoặc phase
# Context chuẩn bị giống nhau cho tất cả chapters
```

**Tác động:**
- Không thể focus vào current arc
- Information từ arc khác làm nhiễu

**Vấn đề 3: Super Summary Inflation**

```python
# Super summary được update liên tục
# Có thể trở nên quá dài ở chapter 250
```

**Tác động:**
- Super summary không còn "super" condensed
- Mất focus vào main plot

---

## 💡 Đề xuất tối ưu hóa

### Tối ưu 1: Relevance Scoring System

**Mục tiêu:** Đánh giá mức độ relevant của entity/event với chapter hiện tại

#### 1.1. Entity Relevance Score

```python
def calculate_entity_relevance(entity, current_chapter, outline):
    """
    Tính relevance score 0-1 cho entity.
    
    Factors:
    - Recency: Entity xuất hiện gần đây hơn = score cao hơn
    - Frequency: Xuất hiện nhiều lần = quan trọng hơn
    - Outline match: Entity trong outline = score cao
    - Importance: Entity importance (nếu có)
    """
    score = 0.0
    
    # Factor 1: Recency (40%)
    appear_chapters = entity.get('appear_in_chapters', [])
    if appear_chapters:
        last_appearance = max(appear_chapters)
        chapter_distance = current_chapter - last_appearance
        
        # Decay function: gần hơn = score cao hơn
        if chapter_distance == 0:
            recency_score = 1.0
        elif chapter_distance <= 5:
            recency_score = 0.8
        elif chapter_distance <= 10:
            recency_score = 0.6
        elif chapter_distance <= 30:
            recency_score = 0.4
        elif chapter_distance <= 100:
            recency_score = 0.2
        else:
            recency_score = 0.1
        
        score += recency_score * 0.4
    
    # Factor 2: Frequency (20%)
    frequency = len(appear_chapters)
    max_frequency = min(current_chapter, 50)  # Cap at 50
    frequency_score = min(frequency / max_frequency, 1.0)
    score += frequency_score * 0.2
    
    # Factor 3: Outline match (30%)
    entity_name = entity.get('name', '')
    outline_entities = outline.get('entities', [])
    outline_names = [e.get('name', '') for e in outline_entities]
    
    if entity_name in outline_names:
        score += 1.0 * 0.3
    
    # Factor 4: Importance (10%) - if available
    importance = entity.get('importance', 0.5)
    score += importance * 0.1
    
    return min(score, 1.0)
```

#### 1.2. Event Relevance Score

```python
def calculate_event_relevance(event, current_chapter, outline):
    """
    Tính relevance score 0-1 cho event.
    
    Factors:
    - Recency: Event gần hơn = relevant hơn
    - Importance: Event importance score
    - Character overlap: Event involve characters trong outline
    - Causal chain: Event dẫn đến events hiện tại
    """
    score = 0.0
    
    # Factor 1: Recency (40%)
    event_chapter = event.get('chapter', 1)
    chapter_distance = current_chapter - event_chapter
    
    if chapter_distance <= 5:
        recency_score = 1.0
    elif chapter_distance <= 10:
        recency_score = 0.8
    elif chapter_distance <= 30:
        recency_score = 0.6
    elif chapter_distance <= 100:
        recency_score = 0.3
    else:
        recency_score = 0.1
    
    score += recency_score * 0.4
    
    # Factor 2: Importance (30%)
    importance = event.get('importance', 0.5)
    score += importance * 0.3
    
    # Factor 3: Character overlap (30%)
    event_characters = set(event.get('characters_involved', []))
    outline_characters = set([c.get('name') for c in outline.get('characters', [])])
    
    if event_characters and outline_characters:
        overlap = len(event_characters & outline_characters) / len(event_characters)
        score += overlap * 0.3
    
    return min(score, 1.0)
```

#### 1.3. Implementation trong ChapterWriter

```python
# Update _prepare_chapter_context() trong main.py

def _prepare_chapter_context(self, chapter_num: int, chapter_outline: Dict[str, Any],
                             motif: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare context với relevance scoring."""
    
    # Get ALL entities first
    all_entities = []
    for category, entities in self.entity_manager.entities.items():
        for entity in entities:
            all_entities.append({**entity, 'category': category})
    
    # Score and sort entities
    scored_entities = []
    for entity in all_entities:
        relevance = calculate_entity_relevance(entity, chapter_num, chapter_outline)
        if relevance > 0.1:  # Threshold
            scored_entities.append({
                'entity': entity,
                'relevance': relevance
            })
    
    scored_entities.sort(key=lambda x: x['relevance'], reverse=True)
    
    # Adaptive limit based on chapter number
    base_limit = 20
    if chapter_num > 200:
        entity_limit = 30
    elif chapter_num > 100:
        entity_limit = 25
    else:
        entity_limit = base_limit
    
    related_entities = [item['entity'] for item in scored_entities[:entity_limit]]
    
    # Same for events
    all_events = self.post_processor.events
    scored_events = []
    for event in all_events:
        relevance = calculate_event_relevance(event, chapter_num, chapter_outline)
        if relevance > 0.1:
            scored_events.append({
                'event': event,
                'relevance': relevance
            })
    
    scored_events.sort(key=lambda x: x['relevance'], reverse=True)
    
    # Adaptive limit
    if chapter_num > 200:
        event_limit = 20
    elif chapter_num > 100:
        event_limit = 15
    else:
        event_limit = 10
    
    related_events = [item['event'] for item in scored_events[:event_limit]]
    
    # ... rest of context preparation
    return context
```

---

### Tối ưu 2: Sliding Window Approach

**Mục tiêu:** Focus vào chapters gần đây, giảm context pollution

#### 2.1. Chapter Window Definition

```python
# Trong config.yaml
story:
  context_windows:
    immediate: 5      # Last 5 chapters - highest priority
    recent: 20        # Last 20 chapters - medium priority
    medium: 50        # Last 50 chapters - low priority
    historical: 100   # Last 100 chapters - very low priority
```

#### 2.2. Windowed Entity Selection

```python
def get_entities_with_window(current_chapter, all_entities, window_config):
    """
    Lấy entities theo sliding window.
    
    Priority:
    1. Entities trong immediate window (5 chapters) - 100% included
    2. Entities trong recent window (20 chapters) - 80% included
    3. Entities trong medium window (50 chapters) - 50% included
    4. Entities trong historical window (100 chapters) - 20% included
    5. Entities ngoài window - 5% only if very important
    """
    categorized = {
        'immediate': [],
        'recent': [],
        'medium': [],
        'historical': [],
        'old': []
    }
    
    for entity in all_entities:
        appear_chapters = entity.get('appear_in_chapters', [])
        if not appear_chapters:
            continue
        
        last_appearance = max(appear_chapters)
        distance = current_chapter - last_appearance
        
        if distance <= window_config['immediate']:
            categorized['immediate'].append(entity)
        elif distance <= window_config['recent']:
            categorized['recent'].append(entity)
        elif distance <= window_config['medium']:
            categorized['medium'].append(entity)
        elif distance <= window_config['historical']:
            categorized['historical'].append(entity)
        else:
            categorized['old'].append(entity)
    
    # Sample from each category với priority khác nhau
    selected = []
    
    # Immediate: take all
    selected.extend(categorized['immediate'])
    
    # Recent: take 80%
    recent_limit = int(len(categorized['recent']) * 0.8)
    selected.extend(sorted(categorized['recent'], 
                          key=lambda e: calculate_entity_relevance(e, current_chapter),
                          reverse=True)[:recent_limit])
    
    # Medium: take 50%
    medium_limit = int(len(categorized['medium']) * 0.5)
    selected.extend(sorted(categorized['medium'],
                          key=lambda e: calculate_entity_relevance(e, current_chapter),
                          reverse=True)[:medium_limit])
    
    # Historical: take 20%
    historical_limit = int(len(categorized['historical']) * 0.2)
    selected.extend(sorted(categorized['historical'],
                          key=lambda e: calculate_entity_relevance(e, current_chapter),
                          reverse=True)[:historical_limit])
    
    # Old: only if importance > 0.8
    very_important_old = [e for e in categorized['old'] 
                          if e.get('importance', 0) > 0.8]
    selected.extend(very_important_old[:5])
    
    return selected
```

---

### Tối ưu 3: Enhanced Conflict Management

**Mục tiêu:** Better prioritization và pruning cho 300 chapters

#### 3.1. Conflict Priority Scoring

```python
def calculate_conflict_priority(conflict, current_chapter):
    """
    Tính priority score cho conflict.
    
    Factors:
    - Timeline urgency
    - Staleness (bao lâu không tiến triển)
    - Character involvement
    """
    score = 0.0
    
    # Factor 1: Timeline urgency (40%)
    timeline = conflict.get('timeline', 'medium_term')
    introduced = conflict.get('introduced_chapter', 1)
    chapters_elapsed = current_chapter - introduced
    
    timeline_scores = {
        'immediate': (1.0, 1),   # (base_score, expected_duration)
        'batch': (0.9, 5),
        'short_term': (0.7, 10),
        'medium_term': (0.5, 30),
        'long_term': (0.3, 100),
        'epic': (0.2, 300)
    }
    
    base_score, expected_duration = timeline_scores.get(timeline, (0.5, 30))
    
    # Increase urgency if approaching expected resolution
    if chapters_elapsed >= expected_duration * 0.8:
        urgency = 1.0
    elif chapters_elapsed >= expected_duration * 0.5:
        urgency = 0.8
    else:
        urgency = base_score
    
    score += urgency * 0.4
    
    # Factor 2: Staleness penalty (30%)
    last_mentioned = conflict.get('last_mentioned_chapter', introduced)
    stale_duration = current_chapter - last_mentioned
    
    if stale_duration <= 5:
        freshness = 1.0
    elif stale_duration <= 20:
        freshness = 0.7
    elif stale_duration <= 50:
        freshness = 0.4
    else:
        freshness = 0.1  # Very stale
    
    score += freshness * 0.3
    
    # Factor 3: Character importance (30%)
    characters_involved = conflict.get('characters_involved', [])
    # Assume we have character importance scores
    avg_char_importance = 0.5  # Simplified
    score += avg_char_importance * 0.3
    
    return min(score, 1.0)
```

#### 3.2. Conflict Pruning

```python
def prune_stale_conflicts(conflicts, current_chapter, threshold=100):
    """
    Tự động prune conflicts quá cũ không được nhắc đến.
    
    Rules:
    - immediate/batch conflicts: prune nếu > 10 chapters không nhắc
    - short_term: prune nếu > 30 chapters
    - medium_term: prune nếu > 100 chapters
    - long_term/epic: không prune
    """
    pruning_rules = {
        'immediate': 10,
        'batch': 10,
        'short_term': 30,
        'medium_term': 100,
        'long_term': None,  # Never prune
        'epic': None
    }
    
    active_conflicts = []
    pruned_conflicts = []
    
    for conflict in conflicts:
        if conflict.get('status') != 'active':
            continue
        
        timeline = conflict.get('timeline', 'medium_term')
        prune_threshold = pruning_rules.get(timeline)
        
        if prune_threshold is None:
            # Don't prune long_term/epic
            active_conflicts.append(conflict)
            continue
        
        introduced = conflict.get('introduced_chapter', 1)
        last_mentioned = conflict.get('last_mentioned_chapter', introduced)
        stale_duration = current_chapter - last_mentioned
        
        if stale_duration > prune_threshold:
            # Auto-resolve as "abandoned"
            conflict['status'] = 'abandoned'
            conflict['resolution_chapter'] = current_chapter
            conflict['resolution_note'] = f'Auto-pruned due to {stale_duration} chapters of inactivity'
            pruned_conflicts.append(conflict)
        else:
            active_conflicts.append(conflict)
    
    return active_conflicts, pruned_conflicts
```

#### 3.3. Conflict Selection for Batch

```python
def select_conflicts_for_batch(all_conflicts, current_batch, current_chapter):
    """
    Select conflicts for next batch with priority scoring.
    """
    # First prune stale conflicts
    active_conflicts, pruned = prune_stale_conflicts(all_conflicts, current_chapter)
    
    # Score remaining conflicts
    scored_conflicts = []
    for conflict in active_conflicts:
        priority = calculate_conflict_priority(conflict, current_chapter)
        scored_conflicts.append({
            'conflict': conflict,
            'priority': priority
        })
    
    # Sort by priority
    scored_conflicts.sort(key=lambda x: x['priority'], reverse=True)
    
    # Select top N based on batch
    # Early batches: fewer conflicts
    # Later batches: more conflicts
    if current_batch <= 5:
        limit = 5
    elif current_batch <= 20:
        limit = 8
    elif current_batch <= 40:
        limit = 12
    else:
        limit = 15
    
    selected = [item['conflict'] for item in scored_conflicts[:limit]]
    
    return selected, pruned
```

---

### Tối ưu 4: Arc-based Context Management

**Mục tiêu:** Organize story theo arcs, focus context theo arc hiện tại

#### 4.1. Story Arc Definition

```python
# Trong config hoặc checkpoint metadata
story_arcs = [
    {
        "arc_id": "arc_1",
        "name": "Khởi đầu tu luyện",
        "start_chapter": 1,
        "end_chapter": 50,
        "main_conflicts": ["conflict_001", "conflict_002"],
        "main_characters": ["Lý Hạo", "Trần Lực"],
        "themes": ["self-discovery", "power-growth"]
    },
    {
        "arc_id": "arc_2",
        "name": "Tông môn tranh đấu",
        "start_chapter": 51,
        "end_chapter": 120,
        "main_conflicts": ["conflict_010", "conflict_015"],
        "main_characters": ["Lý Hạo", "Lâm Thanh Vân", "Trương Đạo"],
        "themes": ["faction-war", "loyalty"]
    },
    # ... more arcs
]
```

#### 4.2. Arc-aware Context Preparation

```python
def get_current_arc(chapter_num, story_arcs):
    """Xác định arc hiện tại."""
    for arc in story_arcs:
        if arc['start_chapter'] <= chapter_num <= arc['end_chapter']:
            return arc
    return None

def prepare_arc_aware_context(chapter_num, chapter_outline, all_entities, all_events, all_conflicts):
    """
    Chuẩn bị context với arc awareness.
    
    Priority:
    1. Entities/events/conflicts trong current arc - 70%
    2. Entities/events/conflicts từ previous arc - 20%
    3. Global important entities/events - 10%
    """
    current_arc = get_current_arc(chapter_num, story_arcs)
    
    if not current_arc:
        # Fallback to standard context
        return prepare_standard_context(...)
    
    # Get current arc entities
    arc_main_chars = set(current_arc.get('main_characters', []))
    arc_conflicts = set(current_arc.get('main_conflicts', []))
    
    # Filter entities
    arc_entities = []
    other_entities = []
    
    for entity in all_entities:
        if entity.get('name') in arc_main_chars:
            arc_entities.append(entity)
        else:
            other_entities.append(entity)
    
    # Allocate 70% to arc entities, 30% to others
    arc_limit = int(entity_total_limit * 0.7)
    other_limit = entity_total_limit - arc_limit
    
    selected_entities = arc_entities[:arc_limit]
    selected_entities.extend(sorted(other_entities, 
                                   key=lambda e: calculate_entity_relevance(e, chapter_num),
                                   reverse=True)[:other_limit])
    
    # Same for events and conflicts
    # ...
    
    return {
        'arc_info': current_arc,
        'entities': selected_entities,
        'events': selected_events,
        'conflicts': selected_conflicts,
        # ...
    }
```

---

### Tối ưu 5: Adaptive Limits Based on Story Phase

**Mục tiêu:** Điều chỉnh limits theo phase của story

#### 5.1. Phase Definition

```python
def get_story_phase(chapter_num, total_planned_chapters=300):
    """
    Xác định phase của story.
    
    Phases:
    - Introduction (0-10%): Giới thiệu thế giới, nhân vật
    - Rising Action (10-30%): Xây dựng conflicts
    - Development (30-70%): Main story arcs
    - Climax (70-90%): Cao trào
    - Resolution (90-100%): Kết thúc
    """
    progress = chapter_num / total_planned_chapters
    
    if progress <= 0.1:
        return 'introduction'
    elif progress <= 0.3:
        return 'rising_action'
    elif progress <= 0.7:
        return 'development'
    elif progress <= 0.9:
        return 'climax'
    else:
        return 'resolution'
```

#### 5.2. Phase-based Limits

```python
def get_phase_limits(phase):
    """
    Trả về limits cho từng phase.
    
    Introduction: Ít entities/events (focus on world-building)
    Development: Nhiều entities/events (complex story)
    Resolution: Giảm dần (focus on main threads)
    """
    limits = {
        'introduction': {
            'entities': 15,
            'events': 8,
            'conflicts': 5,
            'context_window': 5
        },
        'rising_action': {
            'entities': 25,
            'events': 15,
            'conflicts': 8,
            'context_window': 10
        },
        'development': {
            'entities': 35,
            'events': 20,
            'conflicts': 12,
            'context_window': 20
        },
        'climax': {
            'entities': 30,  # Focus lại
            'events': 25,    # Nhiều events để buildup
            'conflicts': 15,
            'context_window': 30
        },
        'resolution': {
            'entities': 20,  # Focus on main characters
            'events': 15,
            'conflicts': 8,  # Resolve conflicts
            'context_window': 50  # Need full story context
        }
    }
    
    return limits.get(phase, limits['development'])
```

---

### Tối ưu 6: Entity & Event Importance Tracking

**Mục tiêu:** Track importance của entities/events tự động

#### 6.1. Entity Importance Auto-calculation

```python
def calculate_entity_importance(entity, all_events, all_conflicts):
    """
    Tự động tính importance của entity.
    
    Factors:
    - Frequency of appearance
    - Involvement in important events
    - Involvement in conflicts
    - Role (main character > supporting > minor)
    """
    importance = 0.0
    
    # Factor 1: Appearance frequency (30%)
    appearances = len(entity.get('appear_in_chapters', []))
    # Normalize by total chapters seen
    frequency_score = min(appearances / 50, 1.0)
    importance += frequency_score * 0.3
    
    # Factor 2: Event involvement (40%)
    entity_name = entity.get('name', '')
    involved_events = [e for e in all_events 
                       if entity_name in e.get('characters_involved', []) or 
                          entity_name in e.get('entities_involved', [])]
    
    if involved_events:
        # Weighted by event importance
        avg_event_importance = sum(e.get('importance', 0.5) for e in involved_events) / len(involved_events)
        event_count_score = min(len(involved_events) / 20, 1.0)
        event_score = (avg_event_importance + event_count_score) / 2
        importance += event_score * 0.4
    
    # Factor 3: Conflict involvement (30%)
    involved_conflicts = [c for c in all_conflicts
                         if entity_name in c.get('characters_involved', [])]
    
    if involved_conflicts:
        active_conflicts = [c for c in involved_conflicts if c.get('status') == 'active']
        conflict_score = len(active_conflicts) / max(len(involved_conflicts), 1)
        importance += conflict_score * 0.3
    
    return min(importance, 1.0)

def update_all_entity_importance(entity_manager, post_processor):
    """Update importance scores for all entities."""
    all_events = post_processor.events
    all_conflicts = post_processor.conflicts
    
    for category, entities in entity_manager.entities.items():
        for entity in entities:
            importance = calculate_entity_importance(entity, all_events, all_conflicts)
            entity['importance'] = importance
            
            # Also update last_mentioned_chapter
            appear_chapters = entity.get('appear_in_chapters', [])
            if appear_chapters:
                entity['last_mentioned_chapter'] = max(appear_chapters)
    
    entity_manager._save_entities()
```

#### 6.2. Periodic Importance Update

```python
# Trong main.py, sau mỗi batch
def finalize_batch(self, batch_num):
    """Finalize batch và update importance scores."""
    # Update entity importance
    self._update_entity_importance()
    
    # Update event relevance (decay old events)
    self._update_event_relevance()
    
    # Prune stale conflicts
    self._prune_stale_conflicts()
    
def _update_entity_importance(self):
    """Update importance scores every batch."""
    update_all_entity_importance(self.entity_manager, self.post_processor)
    self.logger.info("Updated entity importance scores")
```

---

## 📊 Tác động dự kiến

### 1. Token Usage Reduction

**Hiện tại (Chapter 250):**
- Entities: ~200 entities × ~150 tokens = ~30,000 tokens
- Events: ~100 events × ~100 tokens = ~10,000 tokens
- **Total context:** ~40,000 tokens

**Sau tối ưu (Chapter 250):**
- Entities: ~30 entities (scored + windowed) × ~150 tokens = ~4,500 tokens
- Events: ~20 events (scored + windowed) × ~100 tokens = ~2,000 tokens
- **Total context:** ~6,500 tokens

**Tiết kiệm:** ~84% token usage

### 2. Quality Improvement

- ✅ More relevant context → Better narrative coherence
- ✅ Recency focus → Better continuation from previous chapters
- ✅ Conflict management → Better long-term plot development
- ✅ Arc awareness → Better story structure

### 3. Scalability

- ✅ Can scale to 500+ chapters with same approach
- ✅ Context size stays bounded
- ✅ Adaptive limits prevent overload

---

## 🚀 Implementation Roadmap

### Phase 1: Core Scoring (Priority: High)
- [ ] Implement `calculate_entity_relevance()`
- [ ] Implement `calculate_event_relevance()`
- [ ] Implement `calculate_conflict_priority()`
- [ ] Update `_prepare_chapter_context()` to use scoring

### Phase 2: Windowing (Priority: High)
- [ ] Add window config to `config.yaml`
- [ ] Implement `get_entities_with_window()`
- [ ] Implement `get_events_with_window()`
- [ ] Test with existing stories

### Phase 3: Conflict Management (Priority: Medium)
- [ ] Implement `prune_stale_conflicts()`
- [ ] Update conflict selection logic
- [ ] Add `last_mentioned_chapter` tracking

### Phase 4: Importance Tracking (Priority: Medium)
- [ ] Implement `calculate_entity_importance()`
- [ ] Add periodic importance updates
- [ ] Add importance field to entity schema

### Phase 5: Arc Management (Priority: Low)
- [ ] Design arc data structure
- [ ] Implement arc detection/creation
- [ ] Add arc-aware context preparation

### Phase 6: Testing & Validation (Priority: High)
- [ ] Generate test story with 50 chapters
- [ ] Measure token usage improvement
- [ ] Validate narrative quality
- [ ] Adjust scoring weights

---

## 📝 Kết luận

### Logic hiện tại (v1.3.1)

**Đánh giá:** ⚠️ **Không đủ chặt chẽ cho truyện 300 chương**

**Lý do:**
1. ❌ Không có recency/relevance scoring
2. ❌ Fixed limits không adaptive
3. ❌ Context size không bounded
4. ❌ Conflicts không được pruned
5. ✅ Có chapter-based filtering (good start)
6. ✅ Có timeline-based conflict tracking (good foundation)

### Sau tối ưu hóa

**Đánh giá:** ✅ **Đủ chặt chẽ và scalable cho 300+ chương**

**Cải tiến:**
1. ✅ Relevance scoring system
2. ✅ Sliding window approach
3. ✅ Adaptive limits theo phase
4. ✅ Automatic conflict pruning
5. ✅ Importance tracking
6. ✅ Arc-based organization (optional)

---

**Khuyến nghị:** Implement **Phase 1-3** trước để có impact lớn nhất với effort hợp lý.

**Timeline ước tính:** 
- Phase 1-2: 2-3 ngày
- Phase 3: 1-2 ngày
- Testing: 1-2 ngày
- **Total:** ~1 tuần

---

**Tài liệu này:** `LONG_FORM_STORY_ANALYSIS.md`  
**Ngày tạo:** 2025-11-07  
**Version:** 1.0
