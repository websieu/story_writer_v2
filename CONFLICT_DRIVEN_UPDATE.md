# Conflict-Driven Story Generation Update

## Tóm tắt

Đã cập nhật logic hoạt động của code để hướng theo mâu thuẫn (conflict-driven approach) từ batch 2 trở đi.

## Các thay đổi chính

### 1. Cập nhật cấu trúc dữ liệu

#### Events (`src/post_processor.py`)
- **Thêm field mới**: `entities_involved` - danh sách các entity liên quan đến event
- Field đã có: `characters_involved` - danh sách nhân vật liên quan

#### Conflicts (`src/post_processor.py`)
- **Thêm field mới**:
  - `characters_involved` - danh sách nhân vật liên quan đến mâu thuẫn
  - `entities_involved` - danh sách entity liên quan đến mâu thuẫn

### 2. Logic tạo Outline từ batch 2 (`src/outline_generator.py`)

#### Quy trình mới cho batch >= 2:

1. **Lấy active conflicts** từ batch trước (conflicts chưa được resolved)

2. **Phân tích conflicts** (`_analyze_conflicts_for_batch`):
   - Request LLM xác định:
     - Conflicts nào NÊN ĐƯỢC GIẢI QUYẾT trong batch này
     - Conflicts nào TIẾP TỤC PHÁT TRIỂN
     - Gợi ý conflicts mới cần thiết lập
   - Dựa theo timeline của conflict:
     - `immediate` (1 chapter): BẮT BUỘC giải quyết ngay
     - `batch` (5 chapters): NÊN giải quyết trong batch này
     - `short_term` (10 chapters): CÓ THỂ giải quyết hoặc tiếp tục
     - `medium_term`, `long_term`, `epic`: TIẾP TỤC PHÁT TRIỂN

3. **Tìm characters và entities** liên quan đến active conflicts

4. **Tìm events** liên quan đến characters/entities đó

5. **Tạo outline** với:
   - Context về conflicts cần xử lý
   - Related characters, entities, events
   - Mỗi chapter outline có thêm:
     - `conflict_ids`: danh sách ID các mâu thuẫn được đề cập trong chương
     - `expected_conflict_updates`: mapping conflict_id -> expected status sau chapter
     - `entities`: danh sách entities liên quan đến chương
     - `key_events` có field `related_entities`

### 3. Logic viết Chapter (`src/chapter_writer.py`)

- **Ưu tiên sử dụng entities từ outline**:
  - Nếu outline có field `entities`, sẽ lấy chi tiết đầy đủ từ entity_manager
  - Fallback về related_entities từ context nếu outline không có

- **Thêm method**: `_get_entities_from_outline()`
  - Lấy chi tiết đầy đủ của entities từ tên trong outline

### 4. Context Preparation cho Batch >= 2 (`main.py`)

#### Method `_prepare_batch_context()` được cập nhật:

```python
1. Lấy active_conflicts từ post_processor
2. Từ conflicts → tìm related_characters (_get_characters_from_conflicts)
3. Từ conflicts → tìm related_entities (_get_entities_from_conflicts)  
4. Từ characters + entities → tìm related_events (_get_events_from_characters_entities)
```

#### Các helper methods mới:

- `_get_characters_from_conflicts()`: Lấy characters từ field `characters_involved` của conflicts
- `_get_entities_from_conflicts()`: Lấy entities từ field `entities_involved` của conflicts
- `_get_events_from_characters_entities()`: Lấy events có characters/entities trùng khớp

### 5. Dependency Injection

- Inject `entity_manager` và `post_processor` vào `outline_generator` trong `StoryGenerator.__init__()`
- Cho phép outline_generator truy cập entity và conflict data khi cần

## Workflow mới cho Batch >= 2

```
1. _prepare_batch_context():
   ├─ Lấy active_conflicts
   ├─ Tìm related_characters từ conflicts
   ├─ Tìm related_entities từ conflicts
   └─ Tìm related_events từ characters/entities

2. generate_continuation_outline():
   ├─ _analyze_conflicts_for_batch() → LLM phân tích conflicts
   │  ├─ conflicts_to_resolve
   │  ├─ conflicts_to_develop
   │  └─ conflicts_to_introduce
   │
   └─ _create_continuation_outline_prompt() → Tạo outline
      ├─ Input: conflict plan + related data
      └─ Output: outlines với conflict_ids & expected_conflict_updates

3. write_chapter():
   ├─ Lấy entities từ outline (nếu có)
   ├─ Lấy related_events và related_characters từ context
   └─ Tạo chapter content dựa trên outline và context
```

## Lợi ích

1. **Conflict-driven storytelling**: Câu chuyện phát triển dựa trên việc xử lý các mâu thuẫn một cách có kế hoạch

2. **Better continuity**: Sử dụng entities và events liên quan trực tiếp đến conflicts đang active, tạo sự liên kết chặt chẽ hơn

3. **Structured conflict resolution**: LLM được hướng dẫn rõ ràng về việc giải quyết/phát triển conflicts nào

4. **Entity tracking**: Entities và characters được track qua conflicts, đảm bảo các yếu tố quan trọng không bị bỏ quên

5. **Timeline-based planning**: Phân loại conflicts theo timeline giúp LLM có kế hoạch dài hạn rõ ràng hơn

## Files đã thay đổi

1. `src/outline_generator.py` - Logic tạo outline mới
2. `src/post_processor.py` - Thêm fields vào events và conflicts
3. `src/chapter_writer.py` - Sử dụng entities từ outline
4. `main.py` - Context preparation mới

## Backward Compatibility

- Batch 1 vẫn sử dụng logic cũ (`generate_initial_outline`)
- Chỉ batch >= 2 sử dụng logic conflict-driven mới
- Các field mới trong events/conflicts là optional, không ảnh hưởng đến data cũ

## Testing

Tất cả modules đã được test import thành công:
- ✅ outline_generator.py
- ✅ post_processor.py  
- ✅ chapter_writer.py
- ✅ main.py

Không có syntax errors.
