# TODO - Story Writer v2 Improvement Plan

Đây là phân tích chi tiết và đề xuất giải pháp cho các vấn đề trong hệ thống Story Writer v2.

---

## 1. Sửa lỗi lấy thông tin entity và event từ batch 2 trở đi ✅ CRITICAL

### Vấn đề hiện tại:
- Phương thức `_entity_appears_in_chapter()` chỉ trả về True nếu entity có field `appear_in_chapters` và chapter_num nằm trong đó
- Entities được trích xuất từ outline của batch 1 có `appear_in_chapters` = [1,2,3,4,5]
- Khi viết batch 2 (chapters 6-10), các entities này bị lọc ra vì 6-10 không nằm trong [1,2,3,4,5]
- Điều này dẫn đến **mất thông tin về nhân vật, địa điểm, items** đã xuất hiện ở batch trước

### Nguyên nhân:
- **File:** `src/entity_manager.py`, line 370-384
- Hàm `_entity_appears_in_chapter()` quá strict, không cho phép entities tái sử dụng qua các batch
- **File:** `main.py`, line 224-242
- `_prepare_batch_context()` không lấy đầy đủ entities từ batch trước

### Giải pháp đề xuất:

#### 1.1. Cập nhật logic appear_in_chapters tự động
Sau khi trích xuất entities từ chapter, tự động cập nhật `appear_in_chapters` cho các entities đã có:

```python
# Trong EntityManager
def _update_entity_appearances(self, chapter_content: str, chapter_num: int):
    """Tự động cập nhật appear_in_chapters dựa trên chapter content"""
    content_lower = chapter_content.lower()
    
    for category, entities in self.entities.items():
        for entity in entities:
            name = entity.get('name', '')
            if name and name.lower() in content_lower:
                appear_in = entity.get('appear_in_chapters', [])
                if chapter_num not in appear_in:
                    appear_in.append(chapter_num)
                    appear_in.sort()
                    entity['appear_in_chapters'] = appear_in
```

#### 1.2. Cải thiện get_relevant_entities
Mở rộng logic lấy entities để bao gồm:
- Entities xuất hiện trong 2-3 chapters gần nhất
- Main characters (xuất hiện >= 5 chapters)
- Entities được đề cập trong outline

```python
def get_relevant_entities(self, chapter_outline: Dict[str, Any], max_entities: int = 20):
    relevant = []
    chapter_num = chapter_outline.get('chapter_number', 0)
    
    # 1. Entities trong chapter hiện tại
    # 2. Entities trong 2-3 chapters gần nhất
    recent_chapters = [chapter_num, chapter_num-1, chapter_num-2]
    for ch in recent_chapters:
        if ch > 0:
            relevant.extend(self._get_entities_by_chapter(ch))
    
    # 3. Main characters/entities (frequent appearances)
    frequent = self.get_frequently_used_entities(min_chapters=3)
    relevant.extend(frequent)
    
    # 4. Deduplicate và limit
    return self._deduplicate_entities(relevant)[:max_entities]
```

#### 1.3. Thêm phương thức get_frequently_used_entities
```python
def get_frequently_used_entities(self, min_chapters: int = 3) -> List[Dict[str, Any]]:
    """Lấy entities xuất hiện thường xuyên (main characters, important items)"""
    result = []
    for category, entities in self.entities.items():
        for entity in entities:
            appear_in = entity.get('appear_in_chapters', [])
            if len(appear_in) >= min_chapters:
                result.append({**entity, 'category': category})
    return result
```

#### 1.4. Cải thiện _prepare_batch_context
```python
def _prepare_batch_context(self, batch_num: int, user_suggestions: Optional[str] = None):
    # ... existing code ...
    
    # Thêm: Main entities (xuất hiện >= 3 chapters)
    frequent_entities = self.entity_manager.get_frequently_used_entities(min_chapters=3)
    
    # Thêm: Entities từ 5 chapters gần nhất  
    prev_batch = batch_num - 1
    start_ch = max(1, (prev_batch - 1) * 5 + 1)
    end_ch = prev_batch * 5
    recent_entities = []
    for ch in range(start_ch, end_ch + 1):
        recent_entities.extend(self.entity_manager.get_entities_by_chapter(ch))
    
    return {
        # ... existing ...
        'frequent_entities': frequent_entities,
        'recent_entities': recent_entities
    }
```

---

## 2. Tối ưu cách lấy entity và event liên quan đến chapter ⚡

### Vấn đề hiện tại:
- Việc lọc entities quá hạn chế, thiếu context
- Events không được lọc theo độ quan trọng và thời gian
- Entities/events quan trọng có thể bị bỏ qua

### Giải pháp đề xuất:

#### 2.1. Thêm scoring system cho entities
```python
def score_entity_relevance(self, entity: Dict[str, Any], chapter_num: int, 
                          character_names: List[str]) -> float:
    """Tính điểm liên quan của entity với chapter hiện tại"""
    score = 0.0
    
    # Entity xuất hiện trong chapter này: +10
    if self._entity_appears_in_chapter(entity, chapter_num):
        score += 10.0
    
    # Entity xuất hiện trong 1-2 chapters gần: +5
    recent = [chapter_num - 1, chapter_num - 2]
    if any(self._entity_appears_in_chapter(entity, ch) for ch in recent if ch > 0):
        score += 5.0
    
    # Entity liên quan đến nhân vật chính: +3
    associated = entity.get('associated_characters', [])
    if any(char in associated for char in character_names):
        score += 3.0
    
    # Main character (xuất hiện >= 5 chapters): +8
    if len(entity.get('appear_in_chapters', [])) >= 5:
        score += 8.0
    
    # Important items/techniques: +2
    if entity.get('importance', 0) > 0.7:
        score += 2.0
    
    return score
```

#### 2.2. Events với time decay
```python
def get_events_by_entities(self, entity_names: List[str], current_chapter: int,
                           max_events: int = 10) -> List[Dict[str, Any]]:
    """Lấy events với time decay - events gần đây quan trọng hơn"""
    related_events = []
    
    for event in self.events:
        # Check involvement
        involved = self._is_entity_involved(event, entity_names)
        
        if involved:
            importance = event.get('importance', 0.5)
            event_chapter = event.get('chapter', 1)
            
            # Time decay: events càng gần càng quan trọng
            chapters_ago = current_chapter - event_chapter
            time_decay = 1.0 / (1.0 + chapters_ago * 0.1)
            
            relevance_score = importance * time_decay
            event['relevance_score'] = relevance_score
            related_events.append(event)
    
    related_events.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    return related_events[:max_events]
```

#### 2.3. Cache để giảm tính toán
```python
class EntityManager:
    def __init__(self, ...):
        self._entity_cache = {}  # chapter_num -> relevant_entities
        self._cache_ttl = 5
    
    def get_relevant_entities_cached(self, chapter_outline, max_entities=20):
        chapter_num = chapter_outline.get('chapter_number', 0)
        
        if chapter_num in self._entity_cache:
            return self._entity_cache[chapter_num]
        
        relevant = self.get_relevant_entities(chapter_outline, max_entities)
        self._entity_cache[chapter_num] = relevant
        
        # Clean old cache
        old = [k for k in self._entity_cache if k < chapter_num - self._cache_ttl]
        for k in old:
            del self._entity_cache[k]
        
        return relevant
```

---

## 3. Đánh giá và điều chỉnh logic cho truyện 300 chương 📚

### Vấn đề hiện tại:
- Hệ thống thiết kế cho truyện ngắn (5-50 chương)
- Conflict timeline không phù hợp với 300 chương
- Super summary sẽ quá dài
- Entity list phình to (hàng trăm entities)

### Giải pháp đề xuất:

#### 3.1. Điều chỉnh conflict timeline
```python
CONFLICT_TIMELINES_300_CHAPTERS = {
    'immediate': 1,      # 1 chapter
    'batch': 5,          # 5 chapters (1 batch)
    'arc': 20,           # 20 chapters (1 arc, ~4 batches)
    'volume': 50,        # 50 chapters (1 volume)
    'saga': 150,         # 150 chapters (nửa truyện)
    'epic': 300          # Toàn bộ truyện
}
```

#### 3.2. Hierarchical summary system
```python
# Thay vì 1 super_summary cho 300 chapters:
summaries = {
    'current_arc_summary': "20 chapters gần nhất (400-500 từ)",
    'current_volume_summary': "Volume hiện tại (600-800 từ)",
    'story_overview': "Toàn bộ truyện (800-1000 từ)",
    'recent_chapters': ["5 chapters gần nhất"]
}
```

#### 3.3. Entity importance decay
```python
def calculate_entity_importance(self, entity: Dict, current_chapter: int) -> float:
    """Importance giảm dần theo thời gian không xuất hiện"""
    appear_in = entity.get('appear_in_chapters', [])
    if not appear_in:
        return 0.0
    
    last_chapter = max(appear_in)
    chapters_since = current_chapter - last_chapter
    
    frequency = len(appear_in)
    base_importance = min(1.0, frequency / 10.0)
    
    # Decay nếu không xuất hiện >20 chapters
    if chapters_since > 20:
        decay = 0.5 ** (chapters_since / 20)
        return base_importance * decay
    
    return base_importance
```

#### 3.4. Arc-based structure
```python
class ArcManager:
    """Quản lý story arcs cho truyện dài"""
    
    def __init__(self, chapters_per_arc=20):
        self.chapters_per_arc = chapters_per_arc
        self.arcs = []
    
    def create_arc(self, arc_num: int, theme: str, main_conflict: str):
        arc = {
            'arc_number': arc_num,
            'start_chapter': (arc_num - 1) * self.chapters_per_arc + 1,
            'end_chapter': arc_num * self.chapters_per_arc,
            'theme': theme,
            'main_conflict': main_conflict,
            'status': 'planning'
        }
        self.arcs.append(arc)
        return arc
```

---

## 4. Điều phối nhịp truyện và phong cách viết 🎭

### Vấn đề hiện tại:
- Không có cơ chế điều chỉnh pacing và tone
- Tất cả chapters có cùng style
- Không có variation, gây nhàm chán

### Giải pháp đề xuất:

#### 4.1. Pacing và Tone configuration
```yaml
# Trong config.yaml
story_pacing:
  pacing_cycle:
    - {batch: 1, pace: "slow", tone: "mysterious", focus: "world_building"}
    - {batch: 2, pace: "medium", tone: "adventurous", focus: "character_development"}
    - {batch: 3, pace: "fast", tone: "intense", focus: "action"}
    - {batch: 4, pace: "slow", tone: "emotional", focus: "resolution"}
    - {batch: 5, pace: "medium", tone: "suspenseful", focus: "plot_twist"}
  
  pace_definitions:
    slow: "Mô tả chi tiết, nội tâm nhân vật, xây dựng không khí"
    medium: "Cân bằng hành động và mô tả, tiết tấu đều"
    fast: "Nhiều hành động, đối thoại nhanh, ít mô tả"
  
  tone_definitions:
    mysterious: "Bí ẩn, hồi hộp, nhiều foreshadowing"
    adventurous: "Khám phá, gặp nhân vật mới"
    intense: "Căng thẳng, xung đột gay gắt"
    emotional: "Tập trung cảm xúc, mối quan hệ"
    humorous: "Hài hước, nhẹ nhàng"
    dark: "Bi kịch, tàn khốc"
```

#### 4.2. PacingManager
```python
class PacingManager:
    """Quản lý pacing và tone"""
    
    def get_batch_style(self, batch_num: int) -> Dict[str, str]:
        """Lấy style cho batch dựa trên cycle"""
        idx = (batch_num - 1) % len(self.pacing_cycle)
        return self.pacing_cycle[idx]
    
    def generate_style_prompt(self, batch_num: int) -> str:
        """Tạo prompt điều chỉnh style"""
        style = self.get_batch_style(batch_num)
        
        prompt = f"""
**PHONG CÁCH VIẾT CHO BATCH {batch_num}:**
- Nhịp độ: {style['pace'].upper()}
- Tone: {style['tone'].upper()}
- Trọng tâm: {style['focus']}
"""
        
        if style['pace'] == 'fast':
            prompt += "- Nhiều hành động, ít mô tả dài\n"
        elif style['pace'] == 'slow':
            prompt += "- Mô tả chi tiết, phát triển từ từ\n"
        
        return prompt
```

#### 4.3. VillainManager
```python
class VillainManager:
    """Quản lý tiến trình tiêu diệt tiểu nhân"""
    
    def plan_villain_defeat(self, current_chapter: int) -> List[str]:
        """Villains xuất hiện lâu (>20 chapters) nên được defeat"""
        to_defeat = []
        for villain in self.villains:
            if villain['status'] == 'active':
                chapters_active = current_chapter - villain['introduction_chapter']
                if chapters_active > 20:
                    to_defeat.append(villain['name'])
        return to_defeat
```

---

## 5. Kiểm tra và quản lý character status 👥

### Vấn đề hiện tại:
- Không có tracking số lượng characters
- Không biết character nào active/inactive
- Dễ bị character bloat

### Giải pháp đề xuất:

#### 5.1. CharacterManager
```python
class CharacterManager:
    """Quản lý characters"""
    
    def get_character_stats(self, current_chapter: int) -> Dict[str, Any]:
        """Thống kê characters"""
        characters = self.entity_manager.entities.get('characters', [])
        
        stats = {
            'total': len(characters),
            'main': [],           # Xuất hiện >= 10 chapters
            'supporting': [],     # 3-9 chapters
            'minor': [],          # 1-2 chapters
            'inactive': [],       # Không xuất hiện >20 chapters
            'recent': []          # Xuất hiện trong 5 chapters gần
        }
        
        for char in characters:
            appear_in = char.get('appear_in_chapters', [])
            name = char.get('name', 'Unknown')
            frequency = len(appear_in)
            
            if frequency >= 10:
                stats['main'].append(name)
            elif frequency >= 3:
                stats['supporting'].append(name)
            else:
                stats['minor'].append(name)
            
            if appear_in:
                last = max(appear_in)
                if current_chapter - last > 20:
                    stats['inactive'].append(name)
                elif last > current_chapter - 5:
                    stats['recent'].append(name)
        
        return stats
    
    def should_introduce_new_character(self, current_chapter: int) -> bool:
        """Quyết định có nên giới thiệu character mới"""
        stats = self.get_character_stats(current_chapter)
        
        # Không nếu quá nhiều active (>15)
        active = len(stats['main']) + len(stats['supporting'])
        if active > 15:
            return False
        
        # Không nếu vừa giới thiệu nhiều trong 3 chapters
        if len(stats['recent']) > 3:
            return False
        
        return True
```

#### 5.2. Character guidelines trong prompt
```python
def add_character_guidelines(self, chapter_num: int, prompt: str) -> str:
    stats = self.char_mgr.get_character_stats(chapter_num)
    
    guidelines = f"""
**QUẢN LÝ NHÂN VẬT:**
- Tổng: {stats['total']}
- Chính: {len(stats['main'])}
- Phụ: {len(stats['supporting'])}
- Không hoạt động: {len(stats['inactive'])}

**Hướng dẫn:**
"""
    
    if not self.char_mgr.should_introduce_new_character(chapter_num):
        guidelines += "- KHÔNG giới thiệu nhân vật mới (đã đủ)\n"
    
    reintroduce = self.char_mgr.suggest_character_reintroduction(chapter_num)
    if reintroduce:
        guidelines += f"- Đưa trở lại: {', '.join(reintroduce)}\n"
    
    return prompt + guidelines
```

---

## 6. Xác định điểm kết truyện (open ending) 🎬

### Vấn đề hiện tại:
- Không có planning cho ending
- Không biết khi nào hướng tới kết thúc

### Giải pháp đề xuất:

#### 6.1. Ending configuration
```yaml
# config.yaml
story_structure:
  total_chapters: 300
  
  acts:
    act1_setup:
      chapters: [1, 60]
      description: "Giới thiệu thế giới, nhân vật"
    act2_rising:
      chapters: [61, 180]
      description: "Phát triển conflicts, MC mạnh hơn"
    act3_climax:
      chapters: [181, 270]
      description: "Đối đầu big boss"
    act4_resolution:
      chapters: [271, 300]
      description: "Giải quyết subplots, ending"
  
  ending_type: "open"  # "closed", "open", "cliffhanger"
```

#### 6.2. EndingManager
```python
class EndingManager:
    """Quản lý progression tới ending"""
    
    def get_current_act(self, chapter_num: int) -> str:
        for act_name, act_info in self.acts.items():
            start, end = act_info['chapters']
            if start <= chapter_num <= end:
                return act_name
        return 'unknown'
    
    def get_ending_guidance(self, chapter_num: int) -> str:
        progress = chapter_num / self.total_chapters
        
        if progress < 0.6:
            return "Giai đoạn phát triển, thoải mái mở subplots mới"
        elif progress < 0.9:
            return "Hướng tới giải quyết main conflicts, tránh mở subplots phức tạp"
        else:
            guidance = "GIAI ĐOẠN ENDING!\n"
            guidance += "- Ưu tiên giải quyết conflicts\n"
            guidance += "- KHÔNG mở subplots mới\n"
            if self.ending_type == 'open':
                guidance += "- Giải quyết main conflict, để ngỏ possibilities\n"
            return guidance
```

---

## 7. Kiểm tra và sửa lỗi tên entity chung chung 🔍

### Vấn đề hiện tại:
- Entities có tên chung chung: "Thanh gươm", "Động"
- Khó phân biệt và track

### Giải pháp đề xuất:

#### 7.1. EntityNameValidator
```python
class EntityNameValidator:
    """Validate entity names"""
    
    GENERIC_NAMES = {
        'items': ['thanh gươm', 'kiếm', 'áo', 'bùa'],
        'locations': ['động', 'thung lũng', 'núi', 'rừng'],
        'techniques': ['chiêu', 'thức', 'công pháp']
    }
    
    def is_name_too_generic(self, name: str, category: str) -> bool:
        name_lower = name.lower().strip()
        
        # Too short
        if len(name_lower) < 3:
            return True
        
        # In generic list
        generic_list = self.GENERIC_NAMES.get(category, [])
        if name_lower in generic_list:
            return True
        
        return False
    
    def suggest_improvement(self, name: str, category: str) -> str:
        if category == 'items':
            return "Thêm tính từ: 'Băng Hỏa Kiếm', 'Huyền Thiên Bảo Giáp'"
        elif category == 'locations':
            return "Thêm tên riêng: 'Thanh Vân Động', 'Thiên Trượng Thung'"
        return "Thêm tính từ hoặc tên riêng"
```

#### 7.2. Thêm vào extraction prompt
```python
prompt += """
**QUY TẮC ĐẶT TÊN ENTITY:**

❌ SAI: "Thanh gươm", "Động", "Chiêu thức"
✅ ĐÚNG: "Băng Hỏa Thần Kiếm", "Thanh Vân Động", "Cửu Thiên Huyền Nữ Công"

**Items:** Thêm tính từ đặc biệt (Băng, Hỏa, Thiên...)
**Locations:** Tên địa danh cụ thể
**Techniques:** Tên công pháp đầy đủ
**Characters:** Full name Hán Việt (2-3 chữ)

Nếu không có tên riêng rõ ràng, KHÔNG trích xuất.
"""
```

#### 7.3. Post-processing validation
```python
def _validate_and_filter_entities(self, entities: Dict, validator) -> Dict:
    """Lọc entities có tên chung chung"""
    filtered = {}
    
    for category, entity_list in entities.items():
        filtered[category] = []
        
        for entity in entity_list:
            name = entity.get('name', '')
            
            if validator.is_name_too_generic(name, category):
                self.logger.warning(
                    f"Rejected generic: '{name}' ({category}). "
                    f"Suggestion: {validator.suggest_improvement(name, category)}"
                )
                continue
            
            filtered[category].append(entity)
    
    return filtered
```

---

## 8. Kiểm tra và cải thiện logic conflict checking ⚔️

### Vấn đề hiện tại:
- Conflict resolution không track chặt chẽ
- Không kiểm tra conflict có thực sự resolved
- Timeline không được enforce

### Giải pháp đề xuất:

#### 8.1. ConflictValidator
```python
class ConflictValidator:
    """Validate conflicts và track resolution"""
    
    def validate_timeline(self, conflict: Dict, current_chapter: int) -> Dict:
        """Kiểm tra conflict có vi phạm timeline không"""
        introduced = conflict.get('introduced_in_chapter', 1)
        timeline = conflict.get('timeline', 'batch')
        status = conflict.get('status', 'active')
        
        chapters_elapsed = current_chapter - introduced
        
        timeline_limits = {
            'immediate': 1, 'batch': 5, 'short_term': 10,
            'medium_term': 30, 'long_term': 100, 'epic': 300
        }
        
        limit = timeline_limits.get(timeline, 10)
        
        validation = {
            'conflict_id': conflict.get('id', ''),
            'is_overdue': status == 'active' and chapters_elapsed > limit,
            'warning': None
        }
        
        if validation['is_overdue']:
            validation['warning'] = (
                f"Conflict overdue: '{conflict.get('description', '')}' "
                f"(ch.{introduced}, timeline: {timeline}={limit}ch, now: ch.{current_chapter})"
            )
        
        return validation
```

#### 8.2. Conflict resolution verification
```python
def verify_resolution(self, content: str, conflict_id: str, desc: str) -> bool:
    """Verify conflict thực sự resolved trong chapter"""
    keywords = ['giải quyết', 'kết thúc', 'chiến thắng', 'đánh bại']
    
    content_lower = content.lower()
    
    if desc.lower() not in content_lower:
        return False
    
    return any(kw in content_lower for kw in keywords)

def extract_conflicts(self, chapter_content: str, chapter_num: int):
    # ... existing ...
    
    # Verify expected resolutions
    outline = self._get_chapter_outline(chapter_num)
    if outline:
        expected = outline.get('expected_conflict_updates', {})
        
        for conf_id, expected_status in expected.items():
            if expected_status == 'resolved':
                conflict = self._find_conflict(conf_id)
                if conflict:
                    verified = self.verify_resolution(
                        chapter_content, conf_id, conflict.get('description', '')
                    )
                    
                    if not verified:
                        self.logger.warning(
                            f"Ch{chapter_num}: Conflict {conf_id} expected resolved "
                            f"but couldn't verify"
                        )
```

#### 8.3. Conflict dependency tracking
```python
class ConflictDependencyTracker:
    """Track dependencies giữa conflicts"""
    
    def __init__(self):
        self.dependencies = {}  # parent -> [children]
    
    def can_resolve(self, conflict_id: str, resolved: List[str]) -> bool:
        """Kiểm tra conflict có thể resolve (dependencies đã resolve?)"""
        parents = [p for p, children in self.dependencies.items() 
                  if conflict_id in children]
        return all(p in resolved for p in parents)
```

---

## 9. Tổng kết và roadmap triển khai 🚀

### Thứ tự ưu tiên:

**Phase 1 - Critical Fixes (1-2 tuần):**
1. ✅ Item 1: Sửa lỗi batch 2+ không lấy entities/events
2. ✅ Item 2: Entity/event relevance scoring
3. ✅ Item 7: Entity name validation

**Phase 2 - Core Improvements (2-3 tuần):**
4. Item 5: CharacterManager và tracking
5. Item 8: ConflictValidator
6. Item 3: Điều chỉnh cho 300 chapters

**Phase 3 - Advanced Features (3-4 tuần):**
7. Item 4: PacingManager và style control
8. Item 6: EndingManager
9. Arc-based structure
10. Conflict dependencies

### Testing checklist:
- [ ] Batch 1 generation (baseline)
- [ ] Batch 2 lấy được entities từ batch 1
- [ ] Batch 3-4 với entity persistence
- [ ] Character bloat prevention
- [ ] Conflict timeline enforcement
- [ ] Ending guidance ở chapter 270+
- [ ] Pacing variation

### Monitoring:
- Entity retrieval success rate
- Character count over time
- Conflict resolution rate
- Super summary length growth

---

## Implementation Notes

### Backward Compatibility
- Tất cả thay đổi phải backward compatible
- Thêm feature flags để enable/disable features
- Existing data structures không bị break

### Code Quality
- Document kỹ trong code
- Viết unit tests cho validators
- Type hints cho tất cả methods mới

### Configuration
- Thêm vào config.yaml với defaults hợp lý
- Cho phép override qua command line args
- Validate config khi load

### Performance
- Cache kết quả tính toán entities/events
- Lazy load data khi cần
- Profile để tìm bottlenecks

---

**Tài liệu này sẽ được cập nhật khi implement từng phase.**
