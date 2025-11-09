# Sơ Đồ Hệ Thống Conflict Trong Story Writer

## Tổng Quan Luồng Hoạt Động

```mermaid
graph TB
    Start[Bắt đầu Generate Story] --> LoadMotif[Load Motif từ motif.json]
    LoadMotif --> InitialOutline[OutlineGenerator: Generate Initial Outline]
    
    InitialOutline --> OutlineHasConflicts{Outline có<br/>conflicts?}
    OutlineHasConflicts -->|Có| WriteChapter[ChapterWriter: Write Chapter Content]
    
    WriteChapter --> ChapterComplete[Chapter Content Complete]
    ChapterComplete --> ExtractConflicts[PostProcessor: Extract Conflicts]
    
    ExtractConflicts --> AnalyzeConflicts[Analyze & Parse Conflicts]
    AnalyzeConflicts --> SaveConflicts[(Save to conflicts.json)]
    
    SaveConflicts --> NextChapter{Còn chapter<br/>trong batch?}
    NextChapter -->|Có| WriteChapter
    NextChapter -->|Hết| CheckBatch{Còn batch<br/>tiếp theo?}
    
    CheckBatch -->|Có| PrepareContext[Prepare Context cho Batch mới]
    PrepareContext --> GetUnresolvedConflicts[Get Unresolved Conflicts]
    GetUnresolvedConflicts --> ConflictAnalysis[OutlineGenerator: Analyze Conflicts]
    ConflictAnalysis --> ConflictPlan[Tạo Conflict Plan]
    ConflictPlan --> ContinuationOutline[Generate Continuation Outline]
    ContinuationOutline --> OutlineHasConflicts
    
    CheckBatch -->|Hết| End[End]
    
    style ExtractConflicts fill:#ff9999
    style GetUnresolvedConflicts fill:#99ccff
    style ConflictAnalysis fill:#99ff99
    style SaveConflicts fill:#ffcc99
```

## Chi Tiết Các Giai Đoạn

### 1. CONFLICT TRONG INITIAL OUTLINE

```mermaid
graph LR
    A[Motif Input] --> B[OutlineGenerator]
    B --> C[LLM: Create Initial Outline]
    C --> D[Parse JSON Response]
    D --> E[Extract Conflicts từ Outline]
    
    E --> F{Conflicts Structure}
    F --> G[id]
    F --> H[description]
    F --> I[type]
    F --> J[timeline]
    F --> K[characters_involved]
    F --> L[entities_involved]
    F --> M[introduced_chapter]
    F --> N[status: active]
    
    style E fill:#ffcc99
    style F fill:#ff9999
```

**Timeline Types:**
- `immediate`: 1 chapter (phải giải quyết ngay)
- `batch`: 5 chapters (trong batch hiện tại)
- `short_term`: 10 chapters
- `medium_term`: 30 chapters
- `long_term`: 100 chapters
- `epic`: 300 chapters

### 2. CONFLICT TRONG CHAPTER WRITING

```mermaid
graph TB
    A[Chapter Outline với Conflicts] --> B[ChapterWriter._create_writing_prompt]
    B --> C[_format_conflicts method]
    
    C --> D{Format Conflict Info}
    D --> E["[timeline] description (status)"]
    
    E --> F[Insert vào OUTLINE Section]
    F --> G[Prompt Template]
    
    G --> H[LLM nhận thông tin conflicts]
    H --> I[LLM viết chapter với conflicts]
    I --> J[Chapter Content]
    
    style C fill:#99ccff
    style H fill:#99ff99
```

**Format trong Prompt:**
```
Mâu thuẫn:
- [batch] Lăng Thiên cần tìm cách khắc chế độc tố trong cơ thể (trạng thái: active)
- [short_term] Xung đột với gia tộc Liễu về quyền thừa kế (trạng thái: developing)
```

### 3. EXTRACT CONFLICTS SAU KHI VIẾT CHAPTER

```mermaid
graph TB
    A[Chapter Content Complete] --> B[PostProcessor.extract_conflicts]
    
    B --> C[Load Existing Conflicts]
    C --> D[Get Unresolved Conflicts]
    D --> E[Format Conflicts List]
    
    E --> F[Create Extraction Prompt]
    F --> G[LLM Call: Analyze Chapter]
    
    G --> H{LLM Response}
    H --> I[new_conflicts array]
    H --> J[updated_conflicts array]
    
    I --> K[Parse New Conflicts]
    J --> L[Parse Updates]
    
    K --> M[_update_conflicts method]
    L --> M
    
    M --> N{Update Type?}
    N -->|New| O[Append to conflicts list]
    N -->|Update| P[Find by ID & Update status]
    
    O --> Q[(Save conflicts.json)]
    P --> Q
    
    Q --> R[Mark Step Completed]
    
    style B fill:#ff9999
    style G fill:#99ff99
    style M fill:#ffcc99
    style Q fill:#ffcc99
```

**LLM Extraction Prompt Structure:**
```python
"""
Hãy trích xuất các mâu thuẫn từ chương {chapter_num}.

**NỘI DUNG CHƯƠNG:**
{chapter_content}

**MÂU THUẪN ĐÃ CÓ:**
{formatted_unresolved_conflicts}

**YÊU CẦU:**
1. Xác định mâu thuẫn MỚI phát sinh
2. Cập nhật trạng thái mâu thuẫn cũ (nếu có tiến triển/giải quyết)
3. Phân loại timeline

**OUTPUT JSON:**
{
  "new_conflicts": [...],
  "updated_conflicts": [...]
}
"""
```

### 4. SỬ DỤNG CONFLICTS CHO BATCH TIẾP THEO

```mermaid
graph TB
    A[Start New Batch] --> B[main.py._prepare_batch_context]
    
    B --> C[PostProcessor.get_unresolved_conflicts]
    C --> D{Filter conflicts.json}
    D --> E[status == 'active']
    
    E --> F[Return Active Conflicts List]
    
    F --> G[OutlineGenerator.generate_continuation_outline]
    G --> H[_analyze_conflicts_for_batch]
    
    H --> I[Create Conflict Analysis Prompt]
    I --> J[LLM: Phân loại conflicts]
    
    J --> K{Conflict Planning}
    K --> L[conflicts_to_resolve]
    K --> M[conflicts_to_develop]
    K --> N[conflicts_to_introduce]
    
    L --> O[_create_continuation_outline_prompt]
    M --> O
    N --> O
    
    O --> P[LLM: Generate New Outline]
    P --> Q[New Outline with Conflicts]
    
    Q --> R[Loop back to Chapter Writing]
    
    style C fill:#99ccff
    style H fill:#99ff99
    style K fill:#ffcc99
```

**Conflict Planning Logic:**
```python
# NGUYÊN TẮC XẾP LOẠI:
- immediate (1 chapter): BẮT BUỘC giải quyết ngay
- batch (5 chapters): ƯU TIÊN giải quyết trong batch này
- short_term (10 chapters): CÓ THỂ bắt đầu giải quyết hoặc tiếp tục phát triển
- medium_term (30 chapters): PHÁT TRIỂN thêm, không giải quyết
- long_term/epic: CHỈ DUY TRÌ, không tập trung
```

## Cấu Trúc Dữ Liệu Conflict

### Trong Outline JSON

```json
{
  "chapters": [
    {
      "chapter_number": 1,
      "conflicts": [
        {
          "id": "conflict_ch1_0",
          "description": "Lăng Thiên bị trúng độc Cửu Chuyển Phệ Hồn Tán, cần tìm cách giải độc",
          "type": "external",
          "timeline": "batch",
          "characters_involved": ["Lăng Thiên"],
          "entities_involved": ["Cửu Chuyển Phệ Hồn Tán"],
          "introduced_chapter": 1,
          "status": "active"
        }
      ]
    }
  ]
}
```

### Trong conflicts.json

```json
[
  {
    "id": "conflict_ch1_0",
    "description": "Lăng Thiên bị trúng độc Cửu Chuyển Phệ Hồn Tán, cần tìm cách giải độc",
    "type": "external",
    "timeline": "batch",
    "characters_involved": ["Lăng Thiên"],
    "entities_involved": ["Cửu Chuyển Phệ Hồn Tán"],
    "introduced_chapter": 1,
    "status": "active"
  },
  {
    "id": "conflict_ch3_1",
    "description": "Xung đột với gia tộc Liễu về quyền thừa kế",
    "type": "external",
    "timeline": "short_term",
    "characters_involved": ["Lăng Thiên", "Liễu Như Yên"],
    "entities_involved": ["Gia tộc Liễu"],
    "introduced_chapter": 3,
    "status": "developing",
    "resolution_chapter": null
  },
  {
    "id": "conflict_ch2_0",
    "description": "Nội tâm mâu thuẫn về việc lợi dụng kiến thức kiếp trước",
    "type": "internal",
    "timeline": "medium_term",
    "characters_involved": ["Lăng Thiên"],
    "entities_involved": [],
    "introduced_chapter": 2,
    "status": "resolved",
    "resolution_chapter": 8
  }
]
```

## Các Method Liên Quan Đến Conflict

### PostChapterProcessor

```python
class PostChapterProcessor:
    
    # 1. Extract conflicts từ chapter content
    def extract_conflicts(chapter_content, chapter_num) -> List[Dict]:
        """Gọi LLM để trích xuất conflicts mới và cập nhật cũ"""
        
    # 2. Get active conflicts
    def get_unresolved_conflicts() -> List[Dict]:
        """Return conflicts có status == 'active'"""
        
    # 3. Get conflicts by timeline
    def get_conflicts_by_timeline(timeline: str) -> List[Dict]:
        """Filter conflicts theo timeline (batch, short_term, etc.)"""
    
    # 4. Internal helpers
    def _parse_conflicts_response(response, chapter_num):
        """Parse LLM JSON response thành new_conflicts và updated_conflicts"""
        
    def _update_conflicts(new_conflicts, updated, chapter_num):
        """
        - Add new conflicts to list
        - Update existing conflicts by ID
        - Save to conflicts.json
        """
    
    def _format_conflicts_list(conflicts) -> str:
        """Format conflicts cho prompt"""
        # Output: "- [timeline] description (ID: xxx)"
```

### ChapterWriter

```python
class ChapterWriter:
    
    def _format_conflicts(conflicts: List[Dict]) -> str:
        """
        Format conflicts từ outline để insert vào prompt
        
        Output:
        - [batch] Lăng Thiên cần tìm cách khắc chế độc tố (trạng thái: active)
        - [short_term] Xung đột với gia tộc Liễu (trạng thái: developing)
        """
        return "\n".join([
            f"- [{c.get('timeline', 'unknown')}] {c.get('description', '')} "
            f"(trạng thái: {c.get('status', 'unknown')})"
            for c in conflicts
        ])
```

### OutlineGenerator

```python
class OutlineGenerator:
    
    def _analyze_conflicts_for_batch(batch_num, context) -> Dict:
        """
        Phân tích conflicts để quyết định:
        - Conflicts nào cần resolve trong batch này
        - Conflicts nào tiếp tục develop
        - Conflicts mới nên introduce
        
        Returns:
        {
            'conflicts_to_resolve': [...],
            'conflicts_to_develop': [...],
            'conflicts_to_introduce': [...]
        }
        """
    
    def _create_continuation_outline_prompt(batch_num, context, conflict_plan):
        """
        Tạo prompt cho LLM với conflict plan
        LLM sẽ generate outline dựa trên conflict planning
        """
```

### main.py

```python
class StoryGenerator:
    
    def _prepare_batch_context(batch_num) -> Dict:
        """
        Prepare context cho batch mới:
        1. Get active conflicts
        2. Get related characters/entities from conflicts
        3. Get related events
        
        Returns context dict với active_conflicts
        """
    
    def _select_conflicts_for_batch(batch_num, all_conflicts) -> List:
        """
        Select conflicts dựa trên priority:
        - immediate: bắt buộc
        - batch: ưu tiên
        - short_term: một số
        - medium/long_term: awareness
        """
```

## Luồng Dữ Liệu Đầy Đủ

```mermaid
sequenceDiagram
    participant M as main.py
    participant OG as OutlineGenerator
    participant CW as ChapterWriter
    participant PP as PostProcessor
    participant LLM as LLM Client
    participant FS as File System
    
    Note over M,FS: BATCH 1: Initial Outline
    M->>OG: generate_initial_outline(motif, batch=1)
    OG->>LLM: Prompt: Create outline với conflicts
    LLM-->>OG: JSON với chapters + conflicts
    OG->>FS: Save outline_batch_1.json
    
    Note over M,FS: Write Chapters in Batch 1
    loop Mỗi chapter trong batch
        M->>CW: write_chapter(outline, context)
        CW->>CW: _format_conflicts(outline.conflicts)
        CW->>LLM: Prompt với conflicts section
        LLM-->>CW: Chapter content
        CW->>FS: Save chapter_00X.txt
        
        Note over M,FS: Extract Conflicts
        M->>PP: extract_conflicts(content, chapter_num)
        PP->>FS: Load conflicts.json
        PP->>PP: get_unresolved_conflicts()
        PP->>LLM: Prompt: Extract new & update old
        LLM-->>PP: {new_conflicts, updated_conflicts}
        PP->>PP: _update_conflicts()
        PP->>FS: Save conflicts.json
    end
    
    Note over M,FS: BATCH 2: Continuation
    M->>M: _prepare_batch_context(batch=2)
    M->>PP: get_unresolved_conflicts()
    PP->>FS: Load conflicts.json
    PP-->>M: Active conflicts list
    
    M->>OG: generate_continuation_outline(batch=2, context)
    OG->>OG: _analyze_conflicts_for_batch()
    OG->>LLM: Prompt: Analyze conflicts for planning
    LLM-->>OG: {to_resolve, to_develop, to_introduce}
    
    OG->>LLM: Prompt: Create outline với conflict plan
    LLM-->>OG: JSON với new chapters + conflicts
    OG->>FS: Save outline_batch_2.json
    
    Note over M,FS: Loop back to Write Chapters
```

## Ví Dụ Thực Tế

### Ví Dụ 1: Conflict Lifecycle

#### Chapter 1: Introduce
```json
{
  "id": "conflict_poison",
  "description": "Lăng Thiên bị trúng độc Cửu Chuyển Phệ Hồn Tán",
  "timeline": "batch",
  "introduced_chapter": 1,
  "status": "active"
}
```

#### Chapter 2-4: Developing
- Chapter 2: Lăng Thiên tìm kiếm thông tin về loại độc này
- Chapter 3: Phát hiện manh mối về Bạch Ngọc Lan
- Chapter 4: Tìm được Bạch Ngọc Lan nhưng cần chế thuốc

Status vẫn là `active`, không có `resolution_chapter`

#### Chapter 5: Resolve
```json
{
  "id": "conflict_poison",
  "description": "Lăng Thiên bị trúng độc Cửu Chuyển Phệ Hồn Tán",
  "timeline": "batch",
  "introduced_chapter": 1,
  "status": "resolved",
  "resolution_chapter": 5
}
```

### Ví Dụ 2: Multiple Timelines

**Batch 1 (Chapters 1-5):**

```python
conflicts = [
    {
        "id": "c1",
        "description": "Độc tố cần giải quyết gấp",
        "timeline": "immediate",  # Must resolve in chapter 2
        "status": "active"
    },
    {
        "id": "c2", 
        "description": "Tìm kiếm võ công phù hợp",
        "timeline": "batch",  # Resolve trong 5 chapters
        "status": "active"
    },
    {
        "id": "c3",
        "description": "Xây dựng nền tảng tu luyện",
        "timeline": "short_term",  # 10 chapters
        "status": "active"
    },
    {
        "id": "c4",
        "description": "Khôi phục đỉnh cao kiếp trước",
        "timeline": "long_term",  # 100 chapters
        "status": "active"
    }
]
```

**Batch 2 Analysis:**
```python
conflict_plan = {
    "conflicts_to_resolve": ["c2"],  # Batch timeline đã hết
    "conflicts_to_develop": ["c3"],  # Short-term tiếp tục
    "conflicts_to_introduce": [
        "Conflict với môn phái mới",
        "Phát hiện bí mật gia tộc"
    ]
}
```

## File Locations

```
projects/story_001/
├── outputs/
│   ├── conflicts/
│   │   └── conflicts.json          ← All conflicts storage
│   ├── outlines/
│   │   ├── batch_1_outline.json    ← Conflicts in outline
│   │   └── batch_2_outline.json
│   └── chapters/
│       ├── chapter_001.txt         ← Generated with conflicts context
│       └── chapter_002.txt
```

## Key Features

### 1. **Conflict Tracking**
- Mỗi conflict có ID unique để track qua nhiều chapters
- Status tracking: `active` → `developing` → `resolved`
- Resolution chapter được ghi nhận

### 2. **Timeline Management**
- 6 timeline levels từ immediate đến epic
- Giúp prioritize conflicts cần resolve
- Prevent conflicts bị quên hoặc resolve quá sớm/muộn

### 3. **Context Propagation**
- Conflicts từ outline → chapter writing prompt
- Extracted conflicts → next batch context
- Unresolved conflicts → conflict planning

### 4. **LLM-Driven Analysis**
- LLM extract conflicts từ chapter content
- LLM analyze và plan conflict resolution
- LLM update conflict status

### 5. **Data Persistence**
- conflicts.json lưu trữ tất cả conflicts
- Checkpoint system track extraction steps
- Không mất data khi restart

## Summary

Hệ thống conflict hoạt động theo vòng lặp:

1. **Outline** → Conflicts được define với timeline
2. **Writing** → Conflicts xuất hiện trong prompt để guide LLM
3. **Extraction** → LLM extract conflicts mới và update cũ từ content
4. **Storage** → Save vào conflicts.json
5. **Analysis** → Analyze unresolved conflicts cho batch tiếp theo
6. **Planning** → Quyết định conflicts nào resolve/develop
7. **Loop** → Quay lại bước 1 với context mới

Điều này đảm bảo:
- ✅ Conflicts được track consistently
- ✅ Không bị quên hoặc drop conflicts
- ✅ Resolution có kế hoạch rõ ràng
- ✅ Story có tension và structure tốt
