# Story Generation System - Architecture Documentation

**Version:** 1.3.1  
**Last Updated:** 2024-11-07  
**Author:** AI Story Generation Team

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Data Flow](#data-flow)
4. [Core Components](#core-components)
5. [Module Details](#module-details)
6. [File Structure](#file-structure)
7. [Input/Output Specifications](#inputoutput-specifications)
8. [API Integration](#api-integration)
9. [Checkpoint & Recovery](#checkpoint--recovery)
10. [Cost Tracking](#cost-tracking)

---

## System Overview

Hệ thống tự động sinh truyện tu tiên/kiếm hiệp bằng AI, sử dụng Google Gemini API. Hệ thống hoạt động theo mô hình pipeline với khả năng checkpoint và resume.

### Key Features

- ✅ **Project-based structure**: Mỗi project có folder riêng biệt
- ✅ **Multi-batch generation**: Sinh truyện theo batch (mỗi batch = 5 chapters)
- ✅ **Entity tracking**: Theo dõi nhân vật, địa điểm, bảo vật, công pháp
- ✅ **Event & conflict management**: Quản lý sự kiện và mâu thuẫn
- ✅ **Checkpoint system**: Có thể dừng và tiếp tục bất kỳ lúc nào
- ✅ **Cost tracking**: Theo dõi chi phí API calls
- ✅ **Detailed logging**: Log tất cả LLM requests/responses

### Technology Stack

- **Language**: Python 3.8+
- **LLM Provider**: Google Gemini (gemini-2.5-flash, gemini-2.5-pro)
- **Config**: YAML
- **Data Format**: JSON
- **Storage**: File-based (JSON, TXT)

---

## Architecture Diagram

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Story Generator                           │
│                         (Orchestrator)                           │
└────────────────┬────────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬──────────────┬──────────────┐
    │            │            │              │              │
    ▼            ▼            ▼              ▼              ▼
┌────────┐  ┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Motif  │  │Outline │  │  Entity  │  │ Chapter  │  │   Post   │
│ Loader │  │  Gen   │  │ Manager  │  │  Writer  │  │Processor │
└────────┘  └────────┘  └──────────┘  └──────────┘  └──────────┘
     │           │            │              │              │
     └───────────┴────────────┴──────────────┴──────────────┘
                              │
                 ┌────────────┼────────────┐
                 │            │            │
                 ▼            ▼            ▼
            ┌─────────┐  ┌─────────┐  ┌─────────┐
            │   LLM   │  │Checkpoint│  │  Cost   │
            │ Client  │  │ Manager  │  │ Tracker │
            └─────────┘  └─────────┘  └─────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Gemini API     │
        │  (Pool of Keys) │
        └─────────────────┘
```

### Component Interaction Flow

```
User Input (CLI)
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│                     Main Orchestrator                         │
│  - Initialize components                                      │
│  - Manage batch generation loop                               │
│  - Coordinate module interactions                             │
└─────────────┬────────────────────────────────────────────────┘
              │
   ┌──────────┴──────────┬──────────────────┬───────────────┐
   │                     │                  │               │
   ▼                     ▼                  ▼               ▼
Step 1:              Step 2:           Step 3-4:        Step 5:
Load Motif        Gen Outline      Extract Entities   Write Chapter
   │                     │                  │               │
   │                     │                  │               │
   │                     │                  │               │
   └─────────────────────┴──────────────────┴───────────────┘
                              │
                              ▼
                         Step 6-8:
                      Post-Processing
                    (Events/Conflicts/Summary)
                              │
                              ▼
                         Save & Track
                    (Files, Checkpoint, Cost)
```

---

## Data Flow

### Complete Pipeline Data Flow

```
┌─────────────┐
│ data/       │
│ motif.json  │ ──┐
└─────────────┘   │
                  │
                  ▼
         ┌────────────────┐
         │ 1. Motif Loader│
         │ ─────────────  │
         │ Input:  motif  │
         │ Output: motif  │
         └───────┬────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │ 2. Outline Generator │
      │ ──────────────────── │
      │ Input:  motif/context│
      │ Output: 5 outlines   │
      └──────────┬───────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │ 3. Entity Manager    │
      │ ──────────────────── │
      │ Input:  outlines     │
      │ Output: entities{}   │
      └──────────┬───────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │ 4. Chapter Writer    │  ◄─── Context (entities, events, summaries)
      │ ──────────────────── │
      │ Input:  outline +    │
      │         context      │
      │ Output: chapter text │
      └──────────┬───────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │ 5. Post Processor    │
      │ ──────────────────── │
      │ Input:  chapter text │
      │ Output: events[]     │
      │         conflicts[]  │
      │         summary      │
      └──────────┬───────────┘
                 │
                 ▼
         ┌───────────────┐
         │ projects/     │
         │ {project_id}/ │
         │   outputs/    │
         │   logs/       │
         │   checkpoints/│
         └───────────────┘
```

### Detailed Data Flow per Chapter

```
Chapter N Generation Flow:
═══════════════════════════

Input Stage:
───────────
┌─ Chapter Outline (from Step 2)
│  • chapter_number
│  • title
│  • summary
│  • key_events[]
│  • characters[]
│  • settings[]
│  • conflicts[]
│  • foreshadowing[]
│
├─ Context (from previous chapters)
│  ├─ Entities
│  │  ├─ characters[]
│  │  ├─ locations[]
│  │  ├─ items[]
│  │  ├─ techniques[]
│  │  └─ factions[]
│  │
│  ├─ Events (recent important events)
│  │  └─ [{description, importance, consequences}]
│  │
│  ├─ Conflicts (unresolved)
│  │  └─ [{type, timeline, status}]
│  │
│  ├─ Summaries
│  │  ├─ super_summary (overall story)
│  │  └─ recent_summaries (last 2 chapters)
│  │
│  └─ Previous Chapter End (last 1000 chars)
│
└────────────────────────────────────────────────

Processing Stage:
────────────────
┌─ LLM Call (Gemini API)
│  Input:  Combined prompt from above
│  Model:  gemini-2.5-pro (chapter writing)
│  Temp:   0.85
│  Output: Chapter text (5000+ words)
│
├─ Save to File
│  Path: projects/{id}/outputs/chapters/chapter_{N}.txt
│
└─ Checkpoint
   Mark: chapter_writing_{N} = completed
────────────────────────────────────────────────

Post-Processing Stage:
─────────────────────
┌─ Extract Events
│  Input:  chapter text
│  Output: events[] with importance scores
│  Save:   projects/{id}/outputs/events/events.json
│
├─ Extract Conflicts
│  Input:  chapter text + existing conflicts
│  Output: new_conflicts[], updated_conflicts[]
│  Save:   projects/{id}/outputs/conflicts/conflicts.json
│
├─ Generate Summary
│  Input:  chapter text
│  Output: chapter summary (200-300 words)
│  Save:   projects/{id}/outputs/summaries/summaries.json
│
├─ Extract New Entities
│  Input:  chapter text + existing entities
│  Output: new entities (characters, locations, etc.)
│  Update: projects/{id}/outputs/entities/entities.json
│
└─ Update Super Summary
   Input:  all chapter summaries
   Output: overall story summary
   Save:   in checkpoint metadata
────────────────────────────────────────────────

Output Stage:
────────────
✓ Chapter file: .../chapters/chapter_{N}.txt
✓ Updated entities.json
✓ Updated events.json
✓ Updated conflicts.json
✓ Updated summaries.json
✓ Checkpoint updated
✓ Cost tracked
✓ LLM requests logged
```

---

## Core Components

### 1. Main Orchestrator (`main.py`)

**Class**: `StoryGenerator`

**Responsibilities**:
- Initialize all components
- Manage batch generation loop
- Coordinate between modules
- Handle checkpointing
- Track costs

**Key Methods**:
```python
__init__(config_path, project_id)
generate_story(num_batches, motif_id, genre)
generate_batch(batch_num, motif, user_suggestions)
_generate_chapter(chapter_num, outline, motif)
_prepare_chapter_context(chapter_num, outline, motif)
_prepare_batch_context(batch_num, user_suggestions)
```

**Initialization Flow**:
```
1. Load config from YAML
2. Create project directories
3. Initialize Logger
4. Initialize CostTracker
5. Initialize CheckpointManager
6. Initialize LLMClient
7. Initialize all processing modules
   - MotifLoader
   - OutlineGenerator
   - EntityManager
   - ChapterWriter
   - PostChapterProcessor
```

### 2. Configuration System (`config/config.yaml`)

**Structure**:
```yaml
default_llm:          # Default LLM settings
  provider: gemini
  model: gemini-2.5-flash
  temperature: 0.7
  max_tokens: 4000

task_configs:         # Task-specific overrides
  outline_generation: {...}
  entity_extraction: {...}
  chapter_writing: {...}
  event_extraction: {...}

story:                # Story parameters
  chapters_per_batch: 5
  target_words_per_chapter: 5000

paths:                # File paths
  projects_base_dir: "projects"
  motif_file: "data/motif.json"
  project_subdirs: {...}

logging:              # Logging config
  level: INFO
  log_prompts: true

cost_tracking:        # Pricing info
  pricing:
    gemini-2.5-pro: {input: 1.25, output: 5.00}
    gemini-2.5-flash: {input: 0.075, output: 0.30}
```

### 3. LLM Client (`src/llm_client.py`)

**Class**: `LLMClient`

**Responsibilities**:
- Wrap Gemini API calls
- Handle task-specific configurations
- Estimate tokens
- Calculate costs
- Log requests/responses

**Method Signature**:
```python
call(
    prompt: str,
    task_name: str = "default",
    system_message: Optional[str] = None,
    return_json: bool = False,
    batch_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]
```

**Returns**:
```python
{
    'response': str,          # LLM response text
    'tokens': {
        'input': int,
        'output': int,
        'total': int
    },
    'cost': float,           # USD
    'duration': float,       # seconds
    'model': str            # Model used
}
```

**Logging**:
- Main log: Via Logger.log_llm_call()
- Detailed log: Via Logger.log_llm_request() → separate file
- Error log: Via Logger.log_llm_error() → separate file

### 4. Checkpoint Manager (`src/checkpoint.py`)

**Class**: `CheckpointManager`

**Responsibilities**:
- Track completed steps
- Save/load checkpoint state
- Enable resume functionality
- Store metadata

**Checkpoint File Structure**:
```json
{
  "story_id": "story_001",
  "created_at": "2024-11-07T10:00:00",
  "last_updated": "2024-11-07T12:30:00",
  "current_batch": 2,
  "current_chapter": 7,
  "completed_steps": {
    "outline_generation_batch1": {
      "completed_at": "...",
      "metadata": {"num_chapters": 5}
    },
    "entity_extraction_batch_1": {...},
    "chapter_writing_1": {...},
    ...
  },
  "metadata": {
    "motif": {...},
    "super_summary": "...",
    ...
  }
}
```

**Key Methods**:
```python
is_step_completed(step_name, batch, chapter) -> bool
mark_step_completed(step_name, batch, chapter, metadata)
set_metadata(key, value)
get_metadata(key, default)
update_progress(batch, chapter)
```

---

## Module Details

### Module 1: Motif Loader

**File**: `src/motif_loader.py`

**Input**:
- `data/motif.json` - Collection of story templates

**Output**:
```python
{
    "id": "motif_001",
    "title": "Tên motif",
    "genre": "tu_tien",
    "protagonist": {...},
    "setting": {...},
    "conflict": {...},
    "theme": "..."
}
```

**Methods**:
```python
get_motif_by_id(motif_id) -> Dict
get_random_motif(genre=None) -> Dict
get_all_motifs() -> List[Dict]
```

### Module 2: Outline Generator

**File**: `src/outline_generator.py`

**Input for Initial Outline**:
- Motif object
- Batch number

**Input for Continuation Outline**:
```python
{
    'super_summary': str,        # Overall story summary
    'recent_summary': str,       # Last chapter summary
    'characters': List[Dict],    # Top characters
    'entities': List[Dict],      # Relevant entities
    'events': List[Dict],        # Important events
    'unresolved_conflicts': List[Dict],
    'user_suggestions': str      # Optional user input
}
```

**Output**: List of 5 chapter outlines
```python
[
    {
        "chapter_number": 1,
        "title": "Chương 1: Khởi đầu",
        "summary": "Tóm tắt ngắn gọn",
        "key_events": [
            {
                "description": "Sự kiện",
                "order": 1,
                "purpose": "Setup/Plot/Character development"
            }
        ],
        "characters": [
            {
                "name": "Trần Phàm",
                "role": "main",
                "development": "Giới thiệu nhân vật"
            }
        ],
        "settings": ["Lạc Diệp Trấn", "Phế Tích Cổ"],
        "conflicts": [
            {
                "type": "internal/external",
                "description": "...",
                "timeline": "immediate/batch/long_term"
            }
        ],
        "foreshadowing": ["Gợi ý tương lai 1", "..."]
    },
    ...
]
```

**LLM Task**: `outline_generation`
- Model: gemini-2.5-flash
- Temperature: 0.8
- Max tokens: 4000

### Module 3: Entity Manager

**File**: `src/entity_manager.py`

**Input for Batch Extraction**:
- List of 5 chapter outlines
- Batch number

**Input for Chapter Extraction**:
- Chapter content text
- Chapter number
- Existing entities (for deduplication)

**Output**: Categorized entities
```python
{
    "characters": [
        {
            "name": "Trần Phàm",
            "type": "character",
            "description": "giới tính: nam; ...; tiến trình: (c1)... → (c5)...",
            "appear_in_chapters": [1, 2, 3, 4, 5]
        }
    ],
    "locations": [...],
    "items": [...],          # artifacts
    "spiritual_herbs": [...], # elixirs
    "beasts": [...],
    "techniques": [...],
    "factions": [...],
    "other": [...]
}
```

**Type Mapping** (Gemini response → Storage):
```python
{
    'character': 'characters',
    'beast': 'beasts',
    'faction': 'factions',
    'artifact': 'items',
    'location': 'locations',
    'technique': 'techniques',
    'elixir': 'spiritual_herbs',
    'other': 'other'
}
```

**Key Methods**:
```python
extract_entities_from_outlines(outlines, batch_num) -> Dict
extract_entities_from_chapter(chapter_content, chapter_num) -> Dict
get_relevant_entities(chapter_outline, max_entities=20) -> List[Dict]
get_entity_by_name(name) -> Optional[Dict]
```

**LLM Task**: `entity_extraction`
- Model: gemini-2.5-flash
- Temperature: 0.3 (low for consistency)
- Max tokens: 3000

**JSON Parsing**:
- Uses `parse_json_from_response()` utility
- Handles markdown code blocks: ` ```json\n[...]\n``` `
- Supports both arrays and objects

### Module 4: Chapter Writer

**File**: `src/chapter_writer.py`

**Input**:
```python
chapter_outline = {
    "chapter_number": 5,
    "title": "...",
    "summary": "...",
    "key_events": [...],
    "characters": [...],
    "settings": [...],
    "conflicts": [...]
}

context = {
    'motif': {...},
    'related_entities': [...],
    'related_characters': [...],
    'related_events': [...],
    'recent_summaries': ["summary1", "summary2"],
    'super_summary': "Overall story summary",
    'previous_chapter_end': "Last 1000 chars of previous chapter"
}
```

**Output**:
- Chapter content text (5000+ words in Vietnamese)
- Saved to: `projects/{id}/outputs/chapters/chapter_{N}.txt`

**Prompt Structure**:
```
OUTLINE CHƯƠNG {N}: {title}
├─ Tóm tắt
├─ Sự kiện chính
├─ Nhân vật
├─ Địa điểm
└─ Mâu thuẫn

NGỮ CẢNH TRUYỆN:
├─ Motif gốc
├─ Tóm tắt tổng thể
├─ Tóm tắt chương gần đây
├─ Kết chương trước
├─ Nhân vật liên quan
├─ Sự kiện quan trọng
└─ Entity liên quan

YÊU CẦU VIẾT:
- Độ dài: ~5000 từ
- Phong cách: Tu tiên/kiếm hiệp
- Miêu tả chi tiết
- Đối thoại tự nhiên
- Liên kết mạch truyện
```

**LLM Task**: `chapter_writing`
- Model: gemini-2.5-pro (high quality)
- Temperature: 0.85 (creative)
- Max tokens: 8000 (long output)

**Key Methods**:
```python
write_chapter(chapter_outline, context) -> str
get_chapter_end(chapter_num, last_chars=1000) -> str
_create_writing_prompt(outline, context) -> str
```

### Module 5: Post-Processor

**File**: `src/post_processor.py`

**Responsibilities**:
1. Extract events from chapter
2. Extract/update conflicts
3. Generate chapter summary
4. Update super summary

**5.1 Event Extraction**

**Input**: Chapter content + chapter number

**Output**: List of events
```python
[
    {
        "chapter": 5,
        "description": "Trần Phàm đột phá Luyện Khí tầng 3",
        "importance": 0.9,  # 0-1 scale
        "characters_involved": ["Trần Phàm", "Linh Hồn Sư Phụ"],
        "location": "Phế Tích Cổ",
        "consequences": "Tăng sức mạnh, thu hút sự chú ý"
    },
    ...
]
```

**LLM Task**: `event_extraction`
- Model: gemini-2.5-flash
- Temperature: 0.3
- Max tokens: 2000

**5.2 Conflict Extraction**

**Input**: Chapter content + existing conflicts

**Output**:
```python
{
    "new_conflicts": [
        {
            "id": "conflict_ch5_1",
            "type": "external",
            "description": "...",
            "introduced_chapter": 5,
            "timeline": "short_term",  # immediate/batch/short/medium/long/epic
            "status": "active"
        }
    ],
    "updated_conflicts": [
        {
            "id": "conflict_ch3_2",
            "status": "resolved",
            "resolution_chapter": 5
        }
    ]
}
```

**Conflict Timeline Categories**:
```python
{
    "immediate": 1 chapter,
    "batch": 5 chapters,
    "short_term": 10 chapters,
    "medium_term": 30 chapters,
    "long_term": 100 chapters,
    "epic": 300 chapters
}
```

**5.3 Summary Generation**

**Input**: Chapter content

**Output**:
```python
{
    "chapter": 5,
    "summary": "200-300 word summary in Vietnamese",
    "key_points": ["Point 1", "Point 2", "Point 3"]
}
```

**5.4 Super Summary**

Periodically updated overall story summary based on all chapter summaries.

**Key Methods**:
```python
process_chapter(chapter_content, chapter_num) -> Dict
extract_events(chapter_content, chapter_num) -> List[Dict]
extract_conflicts(chapter_content, chapter_num) -> Tuple[List, List]
generate_summary(chapter_content, chapter_num) -> str
update_super_summary(chapter_num) -> str
get_unresolved_conflicts() -> List[Dict]
get_recent_summaries(count=2) -> List[str]
```

---

## File Structure

### Project Directory Layout

```
projects/
└── {project_id}/           # e.g., story_001
    ├── outputs/            # All generated content
    │   ├── chapters/
    │   │   ├── chapter_1.txt
    │   │   ├── chapter_2.txt
    │   │   └── ...
    │   ├── outlines/
    │   │   ├── batch_1_outline.json
    │   │   ├── batch_2_outline.json
    │   │   └── ...
    │   ├── entities/
    │   │   └── entities.json      # All entities, categorized
    │   ├── events/
    │   │   └── events.json        # All events with importance
    │   ├── conflicts/
    │   │   └── conflicts.json     # All conflicts with status
    │   ├── summaries/
    │   │   └── summaries.json     # Per-chapter summaries
    │   └── cost_summary.json      # Final cost report
    │
    ├── checkpoints/
    │   └── {project_id}_checkpoint.json
    │
    └── logs/
        ├── StoryGenerator_YYYYMMDD_HHMMSS.log  # Main log
        └── llm_requests/   # Detailed LLM request logs
            ├── outline_generation_batch001_20241107_120000_123456.txt
            ├── entity_extraction_batch001_20241107_120530_234567.txt
            ├── chapter_writing_chapter001_20241107_121000_345678.txt
            ├── event_extraction_chapter001_20241107_122000_456789.txt
            └── ...
```

### LLM Request Log Format

**Filename Pattern**:
```
{task_name}_{context}_{timestamp}_{random}.txt
```

Examples:
- `outline_generation_batch001_20241107_120000_123456.txt`
- `entity_extraction_batch002_20241107_140000_234567.txt`
- `chapter_writing_chapter005_20241107_160000_345678.txt`

**Content Format**:
```
========================================
LLM Request Log
========================================
Timestamp: 2024-11-07 12:00:00.123456
Task: outline_generation
Batch: 1
Chapter: None
Model: gemini-2.5-flash

========================================
System Prompt:
========================================
{system_prompt}

========================================
User Prompt:
========================================
{user_prompt}

========================================
Response:
========================================
{response}

========================================
Metrics:
========================================
Input Tokens: 3745
Output Tokens: 2269
Total Tokens: 6014
Cost: $0.0010
Duration: 34.73s
========================================
```

---

## Input/Output Specifications

### CLI Input

```bash
python main.py \
  --project-id story_001 \
  --batches 3 \
  --motif-id motif_cultivation_001 \
  --genre tu_tien \
  --config config/config.yaml
```

**Parameters**:
- `--project-id`: Unique identifier (default: `story_001`)
- `--batches`: Number of 5-chapter batches (default: `1`)
- `--motif-id`: Specific motif to use (optional)
- `--genre`: Filter motifs by genre (optional)
- `--config`: Config file path (default: `config/config.yaml`)

### Input Files

**1. Motif File** (`data/motif.json`)
```json
[
    {
        "id": "motif_001",
        "title": "Từ phế tài đến đỉnh cao tu luyện",
        "genre": "tu_tien",
        "protagonist": {
            "background": "Thiếu niên bị coi là phế tài",
            "starting_power": "weak",
            "unique_trait": "Có bảo vật ẩn giấu"
        },
        "setting": {
            "world": "Tu tiên giới",
            "initial_location": "Làng nhỏ hẻo lánh"
        },
        "conflict": {
            "internal": "Vượt qua giới hạn bản thân",
            "external": "Đối đầu kẻ địch mạnh mẽ"
        },
        "theme": "Nghị lực, phát triển bản thân"
    }
]
```

**2. Config File** (`config/config.yaml`)
```yaml
default_llm:
  provider: "gemini"
  model: "gemini-2.5-flash"
  temperature: 0.7
  max_tokens: 4000
  keys_file: "auth_files/keys.txt"

task_configs:
  chapter_writing:
    model: "gemini-2.5-pro"
    temperature: 0.85
    max_tokens: 8000
  
story:
  chapters_per_batch: 5
  target_words_per_chapter: 5000

paths:
  projects_base_dir: "projects"
  motif_file: "data/motif.json"
```

**3. API Keys File** (`auth_files/keys.txt`)
```
API_KEY_1
API_KEY_2
API_KEY_3
```
One key per line. System will randomly rotate through keys.

### Output Files

**1. Chapter Files**
- Path: `projects/{id}/outputs/chapters/chapter_{N}.txt`
- Format: Plain text, UTF-8
- Content: 5000+ words of Vietnamese story text

**2. Outline Files**
- Path: `projects/{id}/outputs/outlines/batch_{N}_outline.json`
- Format: JSON with 5 chapter outlines

**3. Entities File**
- Path: `projects/{id}/outputs/entities/entities.json`
- Format: Categorized entity dictionary
```json
{
  "characters": [{...}],
  "locations": [{...}],
  "items": [{...}],
  "techniques": [{...}],
  ...
}
```

**4. Events File**
- Path: `projects/{id}/outputs/events/events.json`
- Format: Array of event objects with importance scores

**5. Conflicts File**
- Path: `projects/{id}/outputs/conflicts/conflicts.json`
- Format: Array of conflict objects with status tracking

**6. Summaries File**
- Path: `projects/{id}/outputs/summaries/summaries.json`
- Format: Array of per-chapter summaries

**7. Checkpoint File**
- Path: `projects/{id}/checkpoints/{id}_checkpoint.json`
- Format: State object with completed steps

**8. Cost Summary**
- Path: `projects/{id}/outputs/cost_summary.json`
- Format: Breakdown of API costs
```json
{
  "total_cost": 12.45,
  "total_tokens": {
    "input": 150000,
    "output": 80000,
    "total": 230000
  },
  "total_calls": 45,
  "by_model": {...},
  "by_step": {...}
}
```

**9. Log Files**
- Main: `projects/{id}/logs/StoryGenerator_YYYYMMDD_HHMMSS.log`
- LLM Requests: `projects/{id}/logs/llm_requests/*.txt`

---

## API Integration

### Gemini API Integration

**Provider**: Google Gemini via `gemini_client_pool.py`

**Models Used**:
1. **gemini-2.5-flash** (default)
   - Use case: Outline, entity extraction, event extraction
   - Pricing: $0.075/1M input tokens, $0.30/1M output tokens
   - Speed: Fast
   - Quality: Good for structured tasks

2. **gemini-2.5-pro**
   - Use case: Chapter writing
   - Pricing: $1.25/1M input tokens, $5.00/1M output tokens
   - Speed: Slower
   - Quality: Excellent for creative writing

**API Call Flow**:
```
LLMClient.call()
    ↓
Get task config (model, temperature, max_tokens)
    ↓
gemini_call_text_free() or gemini_call_json_free()
    ↓
Load random API key from pool
    ↓
Construct Gemini API request
    ↓
POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent
    ↓
Parse response
    ↓
Extract JSON from markdown if needed (```json\n...\n```)
    ↓
Return to LLMClient
    ↓
Log request/response
Calculate cost
Update cost tracker
    ↓
Return result to caller
```

**Request Format**:
```json
{
  "contents": [{
    "parts": [{
      "text": "{system_prompt}\n\n{user_prompt}"
    }]
  }],
  "generationConfig": {
    "temperature": 0.7,
    "maxOutputTokens": 4000
  }
}
```

**Response Format**:
```json
{
  "candidates": [{
    "content": {
      "parts": [{
        "text": "Response text (may be wrapped in ```json\n...\n```)"
      }]
    }
  }],
  "usageMetadata": {
    "promptTokenCount": 1000,
    "candidatesTokenCount": 500,
    "totalTokenCount": 1500
  }
}
```

**JSON Parsing**:
- Gemini often wraps JSON in markdown code blocks
- System uses `parse_json_from_response()` utility
- Pattern: ` ```json\n{...}\n``` ` or ` ```json\n[...]\n``` `
- Supports both objects and arrays

**Error Handling**:
```python
try:
    response = gemini_call_text_free(...)
except Exception as e:
    logger.log_llm_error(
        task_name=task_name,
        error=str(e),
        prompts=prompts,
        batch_id=batch_id,
        chapter_id=chapter_id
    )
    raise
```

**Rate Limiting**:
- Key rotation: Multiple keys rotated randomly
- Sleep: 0.1s between requests (configurable)
- Retry: Automatic retry on transient errors

---

## Checkpoint & Recovery

### Checkpoint Mechanism

**Purpose**: Enable stopping and resuming story generation at any point

**Checkpoint File**: `projects/{id}/checkpoints/{id}_checkpoint.json`

**Structure**:
```json
{
  "story_id": "story_001",
  "created_at": "2024-11-07T10:00:00",
  "last_updated": "2024-11-07T12:30:00",
  "current_batch": 2,
  "current_chapter": 7,
  "completed_steps": {
    "outline_generation_batch1": {
      "completed_at": "2024-11-07T10:05:00",
      "metadata": {"num_chapters": 5}
    },
    "entity_extraction_batch_1": {
      "completed_at": "2024-11-07T10:10:00",
      "metadata": {"total_entities": 12}
    },
    "chapter_writing_1": {
      "completed_at": "2024-11-07T10:25:00",
      "metadata": {"title": "Chương 1: Khởi đầu", "word_count": 5234}
    },
    "event_extraction_1": {...},
    "conflict_extraction_1": {...},
    "summary_generation_1": {...},
    ...
  },
  "metadata": {
    "motif": {...},
    "super_summary": "Overall story summary updated periodically",
    ...
  }
}
```

**Step Naming Convention**:
- Batch-level: `{step_name}_batch{N}`
  - Example: `outline_generation_batch2`, `entity_extraction_batch_3`
- Chapter-level: `{step_name}_{N}`
  - Example: `chapter_writing_5`, `event_extraction_7`
- Mixed: `{step_name}_batch{B}_ch{C}`

**Checkpoint Flow**:
```
Before each major step:
    ↓
Check: is_step_completed(step_name, batch, chapter)
    ↓
If completed: Skip and load from file
    ↓
If not completed: Execute step
    ↓
After completion: mark_step_completed(step_name, batch, chapter, metadata)
    ↓
Save checkpoint to disk
```

**Resume Behavior**:
```
User stops at Chapter 7
    ↓
Restart: python main.py --project-id story_001 --batches 3
    ↓
System loads checkpoint
    ↓
Finds Chapter 1-7 completed
    ↓
Resumes from Chapter 8
    ↓
Continues until all batches done
```

**Metadata Usage**:
- Store motif for reference in later batches
- Store super_summary for context
- Store custom flags or state

---

## Cost Tracking

### Cost Tracking System

**Purpose**: Monitor and report API costs for budget control

**Components**:
1. **CostTracker** (`src/utils.py`)
2. **LLMClient** integration
3. **Pricing config** in `config.yaml`

**Data Structure**:
```python
{
    "total_cost": 12.45,  # USD
    "total_tokens": {
        "input": 150000,
        "output": 80000,
        "total": 230000
    },
    "total_calls": 45,
    "by_model": {
        "gemini-2.5-flash": {
            "calls": 35,
            "input_tokens": 120000,
            "output_tokens": 50000,
            "cost": 10.50
        },
        "gemini-2.5-pro": {
            "calls": 10,
            "input_tokens": 30000,
            "output_tokens": 30000,
            "cost": 1.95
        }
    },
    "by_step": {
        "outline_generation": {
            "calls": 3,
            "tokens": 25000,
            "cost": 1.20
        },
        "chapter_writing": {
            "calls": 10,
            "tokens": 180000,
            "cost": 8.50
        },
        "entity_extraction": {...},
        "event_extraction": {...},
        ...
    }
}
```

**Pricing Configuration** (`config.yaml`):
```yaml
cost_tracking:
  enabled: true
  pricing:
    gemini-2.5-pro:
      input: 1.25    # USD per 1M tokens
      output: 5.00
    gemini-2.5-flash:
      input: 0.075
      output: 0.30
```

**Cost Calculation**:
```python
def _calculate_gemini_cost(model, input_tokens, output_tokens):
    if 'pro' in model.lower():
        input_cost_per_1m = 1.25
        output_cost_per_1m = 5.00
    else:
        input_cost_per_1m = 0.075
        output_cost_per_1m = 0.30
    
    input_cost = (input_tokens / 1_000_000) * input_cost_per_1m
    output_cost = (output_tokens / 1_000_000) * output_cost_per_1m
    
    return input_cost + output_cost
```

**Tracking Flow**:
```
LLM API call completes
    ↓
Estimate tokens (input + output)
    ↓
Calculate cost using pricing config
    ↓
CostTracker.add_call(model, input_tokens, output_tokens, step, duration)
    ↓
Update totals and breakdowns
    ↓
At end: CostTracker.save_summary(cost_file)
```

**Real-time Logging**:
```
INFO - LLM call: model=gemini-2.5-flash, task=entity_extraction
INFO - Tokens: 3745 input, 2269 output (6014 total)
INFO - Cost: $0.0010, Duration: 34.73s
```

**Final Summary** (`cost_summary.json`):
```json
{
  "total_cost": 12.45,
  "total_tokens": {
    "input": 150000,
    "output": 80000,
    "total": 230000
  },
  "total_calls": 45,
  "by_model": {...},
  "by_step": {...},
  "summary": {
    "chapters_written": 15,
    "cost_per_chapter": 0.83,
    "tokens_per_chapter": 15333
  }
}
```

---

## Performance Considerations

### Token Estimation

**Current Method**: Character-based estimation
```python
def _estimate_tokens(text: str) -> int:
    # Vietnamese: ~2.5 chars per token
    return int(len(text) / 2.5)
```

**Accuracy**: ±15% (acceptable for cost estimation)

**Future**: Use tiktoken library for exact counts

### API Latency

**Average Response Times**:
- Outline generation (flash): 15-30s
- Entity extraction (flash): 20-40s
- Chapter writing (pro): 60-120s
- Event extraction (flash): 10-20s

**Bottlenecks**:
- Chapter writing is slowest (large output)
- Sequential processing (no parallelization yet)

**Optimization Opportunities**:
1. Parallel chapter writing (if independent)
2. Batch API calls for entity extraction
3. Caching for repeated prompts
4. Stream output for real-time feedback

### Storage

**Typical Project Size** (15 chapters):
- Chapters: ~750KB (15 × 50KB)
- Outlines: ~50KB
- Entities: ~30KB
- Events: ~20KB
- Conflicts: ~15KB
- Summaries: ~20KB
- Checkpoints: ~10KB
- Logs: ~500KB
- LLM request logs: ~2MB
- **Total**: ~3.4MB per project

**Scaling**: 100 projects = ~340MB (negligible)

---

## Error Handling

### Error Categories

**1. API Errors**
- Network timeout
- Invalid API key
- Rate limit exceeded
- Content policy violation

**Handling**:
```python
try:
    response = gemini_call_text_free(...)
except Exception as e:
    logger.log_llm_error(...)
    raise
```

**Logging**: Full prompts saved to separate error log file

**2. JSON Parsing Errors**
- Malformed JSON from LLM
- Missing markdown code blocks
- Unexpected format

**Handling**:
```python
try:
    data = parse_json_from_response(response)
except json.JSONDecodeError as e:
    logger.error(f"JSON parsing error: {e}")
    logger.error(f"Response preview: {response[:500]}")
    return default_value
```

**3. File I/O Errors**
- Permission denied
- Disk full
- Path not found

**Handling**: Ensure directories exist before writing

**4. Checkpoint Errors**
- Corrupted checkpoint file
- Version mismatch

**Handling**: Backup checkpoints before overwriting

### Retry Strategy

**Not Implemented Yet** (Future Enhancement):
```python
@retry(max_attempts=3, backoff=2.0)
def call_llm_with_retry(...):
    ...
```

### Graceful Degradation

If a non-critical step fails (e.g., event extraction):
- Log the error
- Continue with default/empty value
- Mark step as completed (to avoid re-attempting)

---

## Testing

### Manual Testing

**Test Script**: `test_json_parsing.py`
```bash
python3 test_json_parsing.py
```

Tests:
- ✓ Markdown wrapped array
- ✓ Markdown wrapped object
- ✓ Plain JSON array
- ✓ Plain JSON object
- ✓ Type mapping
- ✓ Real Gemini response

### Integration Testing

**Full Pipeline Test**:
```bash
python main.py --project-id test_001 --batches 1 --motif-id motif_001
```

Verify:
1. All modules initialize
2. Motif loaded
3. Outline generated (5 chapters)
4. Entities extracted
5. Chapters written
6. Post-processing completed
7. Checkpoint saved
8. Cost tracked
9. Logs created

### Unit Testing

**Not Implemented Yet** (Future):
- Test each module independently
- Mock LLM responses
- Verify checkpoint logic
- Test JSON parsing edge cases

---

## Security Considerations

### API Key Management

**Current**:
- Keys stored in `auth_files/keys.txt` (plain text)
- Not committed to git (in `.gitignore`)
- Random rotation

**Recommendations**:
- Use environment variables
- Encrypt keys at rest
- Implement key rotation policy
- Monitor for leaked keys

### Input Validation

**Current**: Limited validation

**Future**:
- Validate motif structure
- Sanitize user input
- Limit prompt lengths
- Check for injection attempts

### Output Sanitization

**Content Policy**:
- Gemini has built-in content filters
- Check for blocked responses
- Handle policy violations gracefully

---

## Future Enhancements

### Planned Features

**1. Parallel Processing**
```python
# Write multiple chapters in parallel
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(write_chapter, outline) for outline in outlines]
    chapters = [f.result() for f in futures]
```

**2. Advanced Entity Linking**
- Track entity relationships
- Visualize entity graph
- Detect inconsistencies

**3. Quality Checks**
- Coherence scoring
- Fact consistency checking
- Character development tracking

**4. Interactive Mode**
```python
# Allow user to modify outline before writing
outline = generate_outline(motif)
outline = user_review(outline)  # Interactive prompt
chapters = write_chapters(outline)
```

**5. Multiple Output Formats**
- ePub generation
- PDF with formatting
- HTML web version

**6. Web Interface**
- Flask/FastAPI backend
- React frontend
- Real-time progress tracking
- Live preview

### Research Directions

**1. Fine-tuning**
- Fine-tune on Chinese wuxia/xianxia corpus
- Improve Vietnamese translation quality
- Customize for story genre

**2. Reinforcement Learning**
- Use user feedback to improve
- Rank outputs by quality
- Optimize for engagement

**3. Multi-model Ensemble**
- Combine outputs from multiple models
- Vote on best version
- Improve consistency

---

## Troubleshooting

### Common Issues

**Issue**: JSON parsing error
```
ERROR - JSON parsing error: Expecting value: line 1 column 1 (char 0)
```
**Solution**: Check LLM request log, verify response format
**Fix**: v1.3.1 added robust JSON parsing

**Issue**: Module import error
```
ModuleNotFoundError: No module named 'prompts'
```
**Solution**: Use correct import path `from src.prompts.extract_prompt`
**Fix**: v1.3.0 updated all imports

**Issue**: Checkpoint not resuming
```
Completed chapter 5 but system starts from chapter 1
```
**Solution**: Verify checkpoint file exists and is valid JSON
**Debug**: Check `completed_steps` keys match step names

**Issue**: High API costs
```
Generated 5 chapters, cost = $50
```
**Solution**: Check model config, use flash instead of pro where possible
**Optimize**: Reduce max_tokens, optimize prompts

**Issue**: Empty entity extraction
```
Entity extraction returned 0 entities
```
**Solution**: Check LLM response in log file
**Debug**: Verify prompt includes clear instructions

### Debug Mode

Enable verbose logging:
```yaml
# config.yaml
logging:
  level: DEBUG
  log_prompts: true
  log_responses: true
```

Check logs:
```bash
tail -f projects/story_001/logs/StoryGenerator_*.log
```

Inspect LLM requests:
```bash
cat projects/story_001/logs/llm_requests/entity_extraction_*.txt
```

---

## Appendix

### Glossary

- **Batch**: Group of 5 chapters
- **Checkpoint**: Saved state for resume
- **Entity**: Character, location, item, etc.
- **Event**: Important story occurrence
- **Conflict**: Unresolved tension/problem
- **Motif**: Story template/seed
- **Outline**: High-level chapter plan
- **Super Summary**: Overall story summary

### File Extensions

- `.json` - Structured data (entities, events, etc.)
- `.txt` - Plain text (chapters, logs)
- `.yaml` - Configuration
- `.py` - Python source code
- `.md` - Documentation (Markdown)

### Naming Conventions

**Files**:
- Lowercase with underscores: `chapter_writer.py`
- Descriptive: `entity_extraction_batch001_*.txt`

**Classes**:
- PascalCase: `StoryGenerator`, `EntityManager`

**Methods**:
- snake_case: `generate_outline()`, `extract_entities()`

**Variables**:
- snake_case: `chapter_num`, `entity_file`

### Version History

- **v1.0.0**: Initial release
- **v1.1.0**: Added checkpoint system
- **v1.2.0**: Added cost tracking
- **v1.3.0**: Project-based structure, detailed logging
- **v1.3.1**: Fixed JSON parsing for Gemini responses

---

## Contact & Support

**Repository**: story_writer_v2  
**Documentation**: `/root/test_writer/`  
**Issues**: Create GitHub issue  
**Updates**: Check `CHANGELOG.md`

---

**Last Updated**: 2024-11-07  
**Document Version**: 2.0  
**System Version**: 1.3.1

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
