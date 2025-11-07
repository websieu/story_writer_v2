# Entity Filtering Optimization

## Tổng quan
Tối ưu hóa việc trích xuất entities trong `ChapterWriter` để giảm số lượng token gửi lên model khi viết chapter.

## Thay đổi chính

### 1. Cập nhật `_get_entities_from_outline()`
**Trước:**
```python
def _get_entities_from_outline(self, outline_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Lấy tất cả entities từ outline, không filter theo chapter
```

**Sau:**
```python
def _get_entities_from_outline(self, outline_entities: List[Dict[str, Any]], chapter_num: int) -> List[Dict[str, Any]]:
    # Chỉ lấy entities xuất hiện trong chapter hiện tại
    # Kiểm tra field 'appear_in_chapters' của mỗi entity
```

**Lợi ích:**
- Giảm số lượng entities không liên quan được gửi lên model
- Chỉ include entities có `chapter_num` trong `appear_in_chapters`

### 2. Thêm method mới `_filter_entities_by_chapter()`
```python
def _filter_entities_by_chapter(self, entities: List[Dict[str, Any]], chapter_num: int) -> List[Dict[str, Any]]:
    """
    Filter entities theo chapter number.
    
    - Nếu entity có 'appear_in_chapters': chỉ include nếu chapter_num trong list
    - Nếu entity không có 'appear_in_chapters': include (backward compatibility)
    """
```

**Công dụng:**
- Dùng để filter entities từ context khi outline không có entities
- Đảm bảo backward compatibility với entities cũ chưa có field `appear_in_chapters`

### 3. Cập nhật `_create_writing_prompt()`
**Trước:**
```python
if outline_entities:
    related_entities = self._get_entities_from_outline(outline_entities)
else:
    related_entities = context.get('related_entities', [])
```

**Sau:**
```python
if outline_entities:
    related_entities = self._get_entities_from_outline(outline_entities, chapter_num)
else:
    related_entities = self._filter_entities_by_chapter(
        context.get('related_entities', []), 
        chapter_num
    )
```

**Cải tiến:**
- Cả hai trường hợp đều được filter theo chapter_num
- Giảm đáng kể số lượng entities trong prompt

## Ví dụ thực tế

### Dữ liệu từ batch_001_entities.json:
- **Tổng entities:** 17 entities
- **Chapter 1:** 6 entities (Lý Hạo, Trần Lực, Vân Hải Tông, 3 locations)
- **Chapter 5:** 10 entities

### Trước tối ưu:
- **Chapter 1:** Gửi cả 17 entities → ~2000+ tokens
- **Chapter 5:** Gửi cả 17 entities → ~2000+ tokens

### Sau tối ưu:
- **Chapter 1:** Chỉ gửi 6 entities → ~700 tokens (tiết kiệm ~65%)
- **Chapter 5:** Chỉ gửi 10 entities → ~1200 tokens (tiết kiệm ~40%)

## Tác động

### Hiệu quả:
✅ Giảm 40-65% token consumption từ entities  
✅ Prompt tập trung hơn vào nội dung liên quan  
✅ Tiết kiệm chi phí API calls  
✅ Tăng tốc độ response từ model  

### Backward Compatibility:
✅ Entities cũ không có `appear_in_chapters` vẫn hoạt động bình thường  
✅ Không break existing functionality  

## Sử dụng

Không cần thay đổi cách gọi `write_chapter()`. Optimization tự động áp dụng:

```python
chapter_content = chapter_writer.write_chapter(
    chapter_outline=outline,  # có thể có hoặc không có 'entities'
    context={
        'related_entities': all_entities,  # sẽ được filter tự động
        # ... other context
    }
)
```

## Yêu cầu

Entity data phải có field `appear_in_chapters`:
```json
{
  "name": "Lý Hạo",
  "type": "character",
  "description": "...",
  "appear_in_chapters": [1, 2, 3, 4, 5]
}
```

Nếu không có field này, entity sẽ được include ở tất cả chapters (backward compatible).

---

**Ngày cập nhật:** 2025-11-07  
**File liên quan:** `/root/test_writer/src/chapter_writer.py`
