# Entity Manager Update - Lưu Entity Theo Batch và Chapter

## Ngày cập nhật
7 tháng 11, 2025

## Tổng quan thay đổi

Đã cập nhật `entity_manager.py` để lưu entities riêng biệt sau mỗi lần gọi LLM, giúp dễ dàng theo dõi entities mới được trích xuất từ từng batch outline và từng chapter.

## Luồng dữ liệu INPUT/OUTPUT

### 1. Extract Entities from Outlines (Batch Level)

**INPUT:**
- `outlines`: List[Dict[str, Any]] - Danh sách outline của các chapter trong batch
- `batch_num`: int - Số thứ tự của batch

**PROCESS:**
1. Tạo prompt từ outlines
2. Gọi LLM với `batch_id` để trích xuất entities
3. Parse JSON response từ LLM
4. **MỚI**: Lưu entities vào file riêng `batch_{batch_num:03d}_entities.json`
5. Merge entities vào entities tổng hợp
6. Lưu entities tổng hợp vào `entities.json`

**OUTPUT:**
- `batch_{batch_num:03d}_entities.json` - Entities riêng từ batch này
- `entities.json` - Tất cả entities được merge (cập nhật)
- Return: Dict chứa tất cả entities hiện tại

### 2. Extract Entities from Chapter (Chapter Level)

**INPUT:**
- `chapter_content`: str - Nội dung đầy đủ của chapter
- `chapter_num`: int - Số thứ tự chapter

**PROCESS:**
1. Tạo prompt với nội dung chapter và danh sách entities đã có
2. Gọi LLM với `chapter_id` để trích xuất entities MỚI
3. Parse JSON response từ LLM
4. **MỚI**: Lưu entities vào file riêng `chapter_{chapter_num:03d}_entities.json`
5. Merge entities mới vào entities tổng hợp
6. Lưu entities tổng hợp vào `entities.json`

**OUTPUT:**
- `chapter_{chapter_num:03d}_entities.json` - Entities mới từ chapter này
- `entities.json` - Tất cả entities được merge (cập nhật)
- Return: Dict chứa entities mới được trích xuất

## Cấu trúc file entities mới

### Batch Entities File: `batch_XXX_entities.json`
```json
{
  "batch_number": 1,
  "extraction_type": "from_outlines",
  "total_count": 15,
  "entities": {
    "characters": [...],
    "locations": [...],
    "items": [...],
    "spiritual_herbs": [...],
    "beasts": [...],
    "techniques": [...],
    "factions": [...],
    "other": [...]
  }
}
```

### Chapter Entities File: `chapter_XXX_entities.json`
```json
{
  "chapter_number": 1,
  "extraction_type": "from_chapter_content",
  "total_count": 8,
  "entities": {
    "characters": [...],
    "locations": [...],
    "items": [...],
    "spiritual_herbs": [...],
    "beasts": [...],
    "techniques": [...],
    "factions": [...],
    "other": [...]
  }
}
```

### Master Entities File: `entities.json` (không đổi)
```json
{
  "characters": [...],
  "locations": [...],
  "items": [...],
  "spiritual_herbs": [...],
  "beasts": [...],
  "techniques": [...],
  "factions": [...],
  "other": [...]
}
```

## Lợi ích của việc thay đổi

### 1. Traceability (Khả năng truy vết)
- Biết chính xác entities nào được trích xuất từ batch/chapter nào
- Dễ dàng debug khi có vấn đề với entity extraction

### 2. Incremental Analysis (Phân tích tăng dần)
- Xem sự phát triển của entities qua từng batch/chapter
- Phân tích những entities nào xuất hiện sớm, entities nào xuất hiện muộn

### 3. Re-extraction (Trích xuất lại)
- Nếu cần trích xuất lại một batch/chapter cụ thể, có thể xem output cũ để so sánh
- Hữu ích khi điều chỉnh prompt hoặc model

### 4. Quality Control (Kiểm soát chất lượng)
- Dễ dàng review entities được trích xuất từ từng giai đoạn
- Phát hiện nhanh nếu LLM trích xuất sai hoặc thiếu entities

## Cách sử dụng

### Workflow không thay đổi
Code gọi vẫn như cũ:
```python
# Extract from batch outlines
self.entity_manager.extract_entities_from_outlines(outlines, batch_num)

# Extract from chapter content
self.entity_manager.extract_entities_from_chapter(chapter_content, chapter_num)
```

### Truy cập entities riêng
Nếu cần xem entities của batch/chapter cụ thể:
```python
from src.utils import load_json
import os

# Load batch entities
batch_file = os.path.join(paths['entities_dir'], f'batch_{batch_num:03d}_entities.json')
batch_data = load_json(batch_file)
batch_entities = batch_data['entities']

# Load chapter entities
chapter_file = os.path.join(paths['entities_dir'], f'chapter_{chapter_num:03d}_entities.json')
chapter_data = load_json(chapter_file)
chapter_entities = chapter_data['entities']
```

## Thay đổi trong code

### Các phương thức mới:

1. **`_save_batch_entities(entities, batch_num)`**
   - Lưu entities từ batch vào file riêng
   - Thêm metadata: batch_number, extraction_type, total_count

2. **`_save_chapter_entities(entities, chapter_num)`**
   - Lưu entities từ chapter vào file riêng
   - Thêm metadata: chapter_number, extraction_type, total_count

### Các phương thức được cập nhật:

1. **`extract_entities_from_outlines()`**
   - Thêm bước: Gọi `_save_batch_entities()` trước khi merge
   - Thứ tự: Parse → Save batch → Merge → Save all

2. **`extract_entities_from_chapter()`**
   - Thêm bước: Gọi `_save_chapter_entities()` trước khi merge
   - Thứ tự: Parse → Save chapter → Merge → Save all

## Ví dụ về cấu trúc thư mục output

```
projects/story_001/outputs/entities/
├── entities.json                    # Master file (tất cả entities merged)
├── batch_001_entities.json         # Entities từ batch 1 (chapters 1-5)
├── batch_002_entities.json         # Entities từ batch 2 (chapters 6-10)
├── chapter_001_entities.json       # Entities mới từ chapter 1
├── chapter_002_entities.json       # Entities mới từ chapter 2
├── chapter_003_entities.json       # Entities mới từ chapter 3
├── ...
└── chapter_020_entities.json       # Entities mới từ chapter 20
```

## Ghi chú kỹ thuật

### Timing của việc lưu file
- **Batch entities**: Lưu TRƯỚC khi merge, để giữ nguyên output của LLM
- **Chapter entities**: Lưu TRƯỚC khi merge, để giữ nguyên output của LLM
- **Master entities**: Lưu SAU khi merge, chứa tất cả entities đã được deduplicate

### Deduplicate (Loại bỏ trùng lặp)
- Batch/Chapter files: Chứa raw output từ LLM (có thể có trùng lặp nội bộ)
- Master file: Đã được deduplicate dựa trên tên entity (lowercase comparison)

### Checkpoint
- Checkpoint vẫn hoạt động như cũ
- Nếu step đã completed, không gọi LLM và không tạo file mới
- File batch/chapter chỉ được tạo khi extraction thực sự chạy

## Testing

Để test các thay đổi:

```bash
# Test extraction từ outline
python scripts.py extract-entities-batch --project story_001 --batch 1

# Test extraction từ chapter
python scripts.py extract-entities-chapter --project story_001 --chapter 1

# Kiểm tra files đã được tạo
ls -la projects/story_001/outputs/entities/
```

## Backward Compatibility

✅ Hoàn toàn tương thích ngược:
- Interface của EntityManager không thay đổi
- Master file `entities.json` vẫn được tạo như cũ
- Các file batch/chapter là bổ sung, không ảnh hưởng logic cũ
- Code gọi EntityManager không cần thay đổi

## Future Enhancements

Có thể mở rộng trong tương lai:

1. **Entity Timeline**: Vẽ timeline về sự xuất hiện của entities
2. **Entity Analytics**: Phân tích thống kê về entities theo batch/chapter
3. **Entity Diff**: So sánh sự khác biệt của entities giữa các version
4. **Entity Validation**: Validate entities mới với entities đã có để tránh mâu thuẫn
