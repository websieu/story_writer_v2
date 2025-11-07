# System Architecture

## 📐 Tổng quan kiến trúc

Hệ thống được thiết kế theo kiến trúc modular với các thành phần độc lập, dễ maintain và mở rộng.

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Orchestrator                        │
│                       (main.py)                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       │               │               │
       ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│  Core    │    │ Pipeline │    │  Post    │
│ Modules  │    │ Modules  │    │Processing│
└──────────┘    └──────────┘    └──────────┘
```

## 🏗️ Core Modules

### 1. Utils (`src/utils.py`)

**Trách nhiệm:**
- File I/O operations (JSON, text)
- Configuration management
- Logging system
- Cost tracking

**Key Classes:**
- `Logger`: Quản lý logging với multi-handler (file + console)
- `CostTracker`: Theo dõi chi phí API và token usage

**Features:**
- Automatic directory creation
- UTF-8 encoding support
- Structured logging với metadata

### 2. Checkpoint Manager (`src/checkpoint.py`)

**Trách nhiệm:**
- Lưu/load checkpoint state
- Theo dõi bước đã hoàn thành
- Hỗ trợ resume từ gián đoạn

**Data Structure:**
```json
{
  "story_id": "story_001",
  "current_batch": 2,
  "current_chapter": 7,
  "completed_steps": {
    "outline_generation_batch1": {
      "completed_at": "2025-01-07T14:30:22",
      "metadata": {...}
    }
  },
  "metadata": {
    "motif": {...},
    "super_summary": "..."
  }
}
```

**Key Methods:**
- `is_step_completed()`: Kiểm tra bước đã hoàn thành chưa
- `mark_step_completed()`: Đánh dấu bước hoàn thành
- `set_metadata()`: Lưu metadata global

### 3. LLM Client (`src/llm_client.py`)

**Trách nhiệm:**
- Wrapper cho OpenAI API
- Token counting
- Cost calculation
- Task-specific configuration

**Features:**
- Tự động chọn config theo task
- Token counting với tiktoken
- Error handling và retry logic
- Logging đầy đủ prompt/response

**Call Flow:**
```
User Code → LLMClient.call()
    ↓
1. Load task config
2. Count input tokens
3. Call OpenAI API
4. Calculate cost
5. Log everything
6. Return result
```

## 🔄 Pipeline Modules

### 1. Motif Loader (`src/motif_loader.py`)

**Input:** `data/motif.json`

**Output:** Selected motif object

**Features:**
- Random selection
- Genre filtering
- ID-based lookup

### 2. Outline Generator (`src/outline_generator.py`)

**Modes:**
- **Initial**: Tạo outline batch đầu từ motif
- **Continuation**: Tạo outline batch tiếp với context

**Input (Initial):**
- Motif

**Input (Continuation):**
- Super summary
- Recent summaries
- Characters, entities, events
- Unresolved conflicts
- User suggestions

**Output:**
```json
{
  "batch": 1,
  "chapters": [
    {
      "chapter_number": 1,
      "title": "...",
      "summary": "...",
      "key_events": [...],
      "characters": [...],
      "conflicts": [...],
      "settings": [...],
      "foreshadowing": [...]
    }
  ]
}
```

**Prompt Strategy:**
- Detailed requirements trong prompt
- JSON format enforcement
- Examples và constraints

### 3. Entity Manager (`src/entity_manager.py`)

**Entity Categories:**
1. Characters (nhân vật)
2. Locations (địa điểm)
3. Items (vật phẩm)
4. Spiritual Herbs (linh dược)
5. Beasts (yêu thú)
6. Techniques (công pháp)
7. Factions (thế lực)

**Features:**
- Extraction từ outline
- Extraction từ chapter content
- Merge với duplicate detection
- Relevant entity selection

**Algorithm - Get Relevant Entities:**
```python
1. Lấy characters xuất hiện trong chapter
2. Lấy locations trong settings
3. Lấy entities liên kết với characters
4. Sort và limit theo max_entities
```

**Storage:**
```json
{
  "characters": [
    {
      "name": "Lý Thanh Vân",
      "description": "...",
      "cultivation_level": "Kim Đan kỳ",
      "abilities": [...],
      "relationships": [...]
    }
  ],
  "locations": [...],
  ...
}
```

### 4. Chapter Writer (`src/chapter_writer.py`)

**Context Selection Algorithm:**

```python
def prepare_context():
    1. Get chapter outline
    2. Get relevant entities (from outline)
    3. Get related characters (by name)
    4. Get related events (by characters involved)
    5. Get recent summaries (last 2)
    6. Get super summary
    7. Get last 1000 chars of previous chapter
    8. Get motif
    
    return comprehensive_context
```

**Writing Prompt Structure:**
1. **Chapter Outline**: Title, summary, events, characters, conflicts
2. **Context**: Motif, summaries, previous ending
3. **Reference Data**: Characters, events, entities
4. **Requirements**: Length, structure, style
5. **Constraints**: Consistency, character development

**Output:**
- `output/chapters/chapter_XXX.txt`: Nội dung
- `output/chapters/chapter_XXX_meta.json`: Metadata

## 📊 Post-Processing Modules

### Post Processor (`src/post_processor.py`)

**Tasks After Each Chapter:**

1. **Event Extraction**
   - Chỉ events quan trọng (importance: 0-1)
   - Characters involved
   - Consequences

2. **Conflict Extraction**
   - New conflicts
   - Updated conflicts (status changes)
   - Timeline classification

3. **Summary Generation**
   - 150-250 từ
   - Key events
   - Important developments

4. **Super Summary Update**
   - Ultra-condensed (100-200 từ)
   - Entire story so far
   - Incremental update

**Conflict Tracking:**

```python
Conflict Structure:
{
    "id": "conflict_ch3_5",
    "description": "...",
    "type": "external",
    "timeline": "batch",
    "status": "active",  # or "resolved"
    "introduced_chapter": 3,
    "resolution_chapter": null,
    "characters_involved": [...]
}
```

**Timeline Categories:**
- `immediate`: 1 chapter
- `batch`: 5 chapters
- `short_term`: 10 chapters
- `medium_term`: 30 chapters
- `long_term`: 100 chapters
- `epic`: 300 chapters

## 🔀 Data Flow

### Complete Generation Flow

```
START
  ↓
[1] Load Motif
  ↓
[2] Generate Outline (Batch 1)
  ↓
[3] Extract Entities from Outline
  ↓
┌─[4] FOR each chapter:
│   ↓
│   [4a] Prepare Context
│   ↓
│   [4b] Write Chapter Content
│   ↓
│   [4c] Extract New Entities
│   ↓
│   [4d] Extract Events
│   ↓
│   [4e] Extract Conflicts
│   ↓
│   [4f] Generate Summary
│   ↓
│   [4g] Update Super Summary
│   ↓
└── [4h] Save Checkpoint
  ↓
[5] Batch Complete?
  ↓ No
[6] Generate Outline (Next Batch)
  ↓ (with expanded context)
  └─→ Go to [3]
  ↓ Yes
[7] Save Final Summary
  ↓
END
```

### Context Evolution

**Batch 1:**
```
Motif only
```

**Batch 2:**
```
Motif +
Super Summary +
Recent Summaries +
All Entities +
Important Events +
Unresolved Conflicts +
User Suggestions
```

**Batch N:**
```
Same as Batch 2, but:
- More entities accumulated
- More events tracked
- Conflicts resolved/evolved
- Richer super summary
```

## 🗄️ File Organization

### Output Structure

```
output/
├── chapters/
│   ├── chapter_001.txt          # Nội dung chapter
│   ├── chapter_001_meta.json    # Metadata
│   └── ...
├── outlines/
│   ├── batch_1_outline.json     # Outline batch 1
│   └── ...
├── entities/
│   └── entities.json            # Global entity database
├── events/
│   └── events.json              # All events với importance
├── conflicts/
│   └── conflicts.json           # All conflicts với tracking
├── summaries/
│   └── summaries.json           # All chapter summaries
└── cost_summary.json            # Cost tracking
```

### Checkpoint Structure

```
checkpoints/
└── story_001_checkpoint.json    # State của story_001
```

### Logs Structure

```
logs/
└── StoryGenerator_YYYYMMDD_HHMMSS.log
```

## 🔧 Extensibility Points

### 1. Thêm Entity Type Mới

```python
# src/entity_manager.py
def _load_entities():
    return {
        'characters': [],
        'locations': [],
        'new_type': [],  # Thêm type mới
        ...
    }
```

### 2. Thêm LLM Provider Mới

```python
# src/llm_client.py
class LLMClient:
    def __init__(self):
        if provider == 'openai':
            self.client = OpenAI()
        elif provider == 'anthropic':
            self.client = Anthropic()  # Thêm provider
```

### 3. Custom Prompt Templates

```python
# src/outline_generator.py
def _create_outline_prompt():
    # Sửa template prompt
    return custom_prompt
```

### 4. Thêm Post-Processing Task

```python
# src/post_processor.py
def process_chapter():
    # Thêm task mới
    new_data = extract_new_feature()
```

## 🎯 Best Practices

### 1. Error Handling

Mọi LLM call đều có:
- Try-catch
- Logging
- Checkpoint save

### 2. Cost Control

- Token counting trước khi call
- Cost estimate logging
- Configurable model per task

### 3. Resume Logic

```python
if checkpoint.is_step_completed(step):
    return load_from_file()
else:
    result = do_step()
    checkpoint.mark_completed(step)
    return result
```

### 4. Data Validation

- JSON parsing với fallback
- Required field checks
- Type validation

## 🔍 Debugging

### Log Levels

- `DEBUG`: Tất cả chi tiết
- `INFO`: Các bước chính
- `WARNING`: Issues không critical
- `ERROR`: Failures

### Checkpoint Inspection

```python
checkpoint = CheckpointManager('checkpoints', 'story_001')
print(checkpoint.state)
```

### Cost Tracking

```python
summary = cost_tracker.get_summary()
print(f"Total: ${summary['total_cost']}")
```

## 📈 Performance Optimization

### 1. Parallel Processing (Future)

```python
# Có thể parallel nhiều chapters
with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(write_chapter, ch) for ch in chapters]
```

### 2. Caching

- Entity lookup cache
- Summary cache
- Conflict resolution cache

### 3. Batch API Calls

- Combine multiple extractions
- Reduce API call count

## 🔒 Security

- API keys từ environment variables
- No hardcoded credentials
- Safe file operations

---

**Architecture Version:** 1.0
**Last Updated:** 2025-01-07
