# Cập Nhật: Thêm Preview Chương Tiếp Theo Vào Context

## Ngày: 2025-11-08

## Vấn Đề

Khi viết một chapter, LLM chỉ có thông tin về:
- ✅ Outline của chapter hiện tại
- ✅ Kết thúc của chapter trước
- ✅ Tóm tắt các chapter gần đây
- ❌ **THIẾU**: Thông tin về chương tiếp theo

**Hậu quả**:
- LLM không biết hướng phát triển sắp tới
- Khó cài cắm foreshadowing phù hợp
- Có thể viết kết thúc không phù hợp với chương tiếp theo
- Thiếu tính liên kết giữa các chương

## Giải Pháp

Thêm **preview của chương tiếp theo** (từ outline) vào context khi viết chapter hiện tại.

### Lợi Ích

1. **Foreshadowing Tốt Hơn**: LLM biết chính xác những gì sẽ xảy ra ở chương sau, có thể cài cắm setup phù hợp
2. **Kết Nối Chặt Chẽ**: Kết thúc chapter có thể lead-in tự nhiên vào chương sau
3. **Pacing Tốt Hơn**: Biết được tension/climax của chương sau để điều chỉnh
4. **Tránh Mâu Thuẫn**: Không viết nội dung conflict với chương sau

### Format Preview

Preview được giới hạn **300 ký tự đầu** của summary để:
- ✅ Cung cấp đủ context
- ✅ Tránh "spoil" quá nhiều chi tiết
- ✅ Tiết kiệm tokens

## Thay Đổi Code

### 1. File: `src/chapter_writer.py`

#### a. Thêm method `_format_next_chapter_summary()`:

```python
def _format_next_chapter_summary(self, next_chapter_outline: Optional[Dict[str, Any]]) -> str:
    """Format next chapter summary from outline."""
    if not next_chapter_outline:
        return ""
    
    chapter_num = next_chapter_outline.get('chapter_number', '?')
    title = next_chapter_outline.get('title', '')
    summary = next_chapter_outline.get('summary', '')
    
    # Limit summary to 300 chars to avoid too much spoiler
    summary_preview = summary[:300] + "..." if len(summary) > 300 else summary
    
    return f"""**Chương tiếp theo (Preview):**
Chương {chapter_num}: {title}
{summary_preview}"""
```

#### b. Cập nhật `_create_writing_prompt()`:

```python
# Get next chapter summary from outline (if available)
next_chapter_summary = self._format_next_chapter_summary(context.get('next_chapter_outline'))
```

#### c. Thêm vào prompt template:

```python
{previous_end_section}

{next_chapter_summary}  # <-- NEW SECTION

{entities_section}

{events_section}
```

### 2. File: `main.py`

#### a. Cập nhật `generate_batch()`:

**TRƯỚC**:
```python
for chapter_outline in outlines:
    chapter_num = chapter_outline.get('chapter_number')
    self._generate_chapter(chapter_num, chapter_outline, motif)
```

**SAU**:
```python
for i, chapter_outline in enumerate(outlines):
    chapter_num = chapter_outline.get('chapter_number')
    # Get next chapter outline if exists
    next_chapter_outline = outlines[i + 1] if i + 1 < len(outlines) else None
    self._generate_chapter(chapter_num, chapter_outline, motif, next_chapter_outline)
```

#### b. Cập nhật signature của `_generate_chapter()`:

```python
def _generate_chapter(self, chapter_num: int, chapter_outline: Dict[str, Any],
                     motif: Dict[str, Any], next_chapter_outline: Optional[Dict[str, Any]] = None):
```

#### c. Cập nhật `_prepare_chapter_context()`:

**Thêm parameter**:
```python
def _prepare_chapter_context(self, chapter_num: int, chapter_outline: Dict[str, Any],
                             motif: Dict[str, Any], next_chapter_outline: Optional[Dict[str, Any]] = None):
```

**Thêm vào return**:
```python
return {
    'motif': motif,
    'related_entities': related_entities,
    'related_characters': related_characters,
    'related_events': related_events,
    'recent_summaries': recent_summaries,
    'super_summary': super_summary,
    'previous_chapter_end': previous_chapter_end,
    'next_chapter_outline': next_chapter_outline  # <-- NEW
}
```

## Ví Dụ Output Trong Prompt

### Khi Viết Chương 2:

```
**NGỮ CẢNH:**

**Bối cảnh:** Thiên tài tu tiên bị hại mất tu vi...

**Tóm tắt toàn bộ:** Lăng Vân, thiên tài Trúc Cơ đỉnh phong, bị...

**Các chương gần đây:**
1. Chương 1 chứng kiến Lăng Vân tỉnh dậy...

**Kết chương trước:**
...ngọn lửa báo thù trong mắt hắn, không những không suy giảm...

**Chương tiếp theo (Preview):**
Chương 3: Mưu Sinh Và Tầm Đạo
Trong U Cốc Viện, Lăng Vân đối mặt với cơ thể phế bỏ và nỗi sỉ nhục. 
Hắn quyết tâm sống sót và mạnh lên, nhận ra con đường duy nhất là 
luyện thể kết hợp Dược đạo. Đọc sách, hắn bất ngờ phát hiện mình 
sở hữu kiến thức Dược đạo bẩm sinh sâu sắc...

**Entity liên quan:**
- Lăng Vân (character): ...
```

### Khi Viết Chương 5 (Chương Cuối Batch):

```
**Chương tiếp theo (Preview):**
[KHÔNG CÓ - vì đây là chương cuối của batch]
```

## Use Cases

### 1. Foreshadowing Setup

**Chương 2 biết chương 3 có:**
> "Để có nguyên liệu bào chế Thanh Thể Dịch, Lăng Vân phải mạo hiểm vào rừng cấm..."

**Chương 2 có thể cài cắm:**
> "Hắn nhìn qua cửa sổ về phía rừng cấm xa xa, ánh mắt long lên quyết tâm nguy hiểm..."

### 2. Cliffhanger Phù Hợp

**Chương 3 biết chương 4 có:**
> "Lão Huyết xuất hiện và điều tra về Mộc Linh Tinh Túy..."

**Chương 3 kết thúc:**
> "Một luồng Mộc Linh Tinh Túy thoát ra ngoài căn phòng... Trong bóng đêm, một đôi mắt già nua bỗng mở to..."

### 3. Character Introduction

**Chương 4 biết chương 5 có:**
> "Lão Huyết tiếp cận Lăng Vân và đưa ra lời đề nghị..."

**Chương 4 có thể:**
> "...Lão Huyết rời đi với lời nói ẩn ý, để lại Lăng Vân đầy băn khoăn về ý định thật sự của lão..."

## Edge Cases

### Chương 5 (Cuối Batch)

Khi viết chương 5, `next_chapter_outline = None` vì:
- Chương 6 thuộc batch 2
- Outline batch 2 chưa được tạo khi viết batch 1

**Xử lý**: Method `_format_next_chapter_summary()` return empty string nếu `next_chapter_outline is None`

### Cross-Batch Foreshadowing

Nếu cần foreshadowing cho batch sau:
- ✅ Sử dụng conflict timeline (short-term, medium-term)
- ✅ Sử dụng foreshadowing field với reveal_chapter = null
- ❌ KHÔNG dựa vào next chapter preview (không có)

## Validation & Testing

### Test Script: `test_next_chapter_prompt.py`

Kiểm tra:
1. ✅ Next chapter section có xuất hiện trong prompt không
2. ✅ Thông tin có chính xác (chapter number, title, summary) không
3. ✅ Vị trí của section có đúng (sau "Kết chương trước", trước "Entity liên quan") không
4. ✅ Summary có bị truncate đúng 300 chars không

### Chạy Test:

```bash
python test_next_chapter_prompt.py
```

**Expected Output**:
```
================================================================================
TESTING NEXT CHAPTER SUMMARY IN PROMPT
================================================================================

Current Chapter: 2 - [Title]
Next Chapter: 3 - [Title]

================================================================================
CHECKING FOR NEXT CHAPTER SECTION IN PROMPT
================================================================================

✅ SUCCESS: Next chapter section found in prompt!

**Chương tiếp theo (Preview):**
Chương 3: [Title]
[First 300 chars of summary]...

================================================================================
SECTION ORDER IN PROMPT
================================================================================
✅ OUTLINE CHƯƠNG                                     at position 0
✅ Bối cảnh:                                          at position 150
✅ Tóm tắt toàn bộ:                                   at position 250
✅ Kết chương trước:                                  at position 350
✅ Chương tiếp theo (Preview):                        at position 450
✅ Entity liên quan:                                  at position 700
✅ Các sự kiện liên quan từ các entity:              at position 1200
```

## Lợi Ích Cụ Thể

### 1. **Better Continuity** 
- Mỗi chapter biết chính xác điều gì sẽ xảy ra tiếp theo
- Kết thúc có thể natural lead-in
- Tránh plot holes

### 2. **Smarter Foreshadowing**
- Setup ở chapter N phù hợp với payoff ở chapter N+1
- Follow foreshadowing constraint (max +2 chapters)
- Chi tiết được cài cắm có mục đích rõ ràng

### 3. **Better Pacing**
- Chapter trước climax có thể build tension
- Chapter sau climax có thể cool down
- Flow tự nhiên hơn

### 4. **Character Development**
- Biết character sẽ làm gì ở chương sau
- Có thể hint về motivation/decision
- Arc development mượt mà

## So Sánh Trước/Sau

### TRƯỚC (Không có Next Chapter Preview)

**Prompt cho Chapter 3**:
```
**Kết chương trước:**
...Lăng Vân quyết tâm tìm con đường mới...

**Entity liên quan:**
- Lăng Vân: ...
```

**Vấn đề**: LLM không biết chapter 4 là gì, khó cài cắm foreshadowing phù hợp.

### SAU (Có Next Chapter Preview)

**Prompt cho Chapter 3**:
```
**Kết chương trước:**
...Lăng Vân quyết tâm tìm con đường mới...

**Chương tiếp theo (Preview):**
Chương 4: Huyết Ngọc Thành Kim
Sau khi hấp thụ Thanh Thể Dịch, Lăng Vân cảm nhận cơ thể được cường hóa 
và phát hiện viên đá màu xám có khả năng 'Trích Tinh Thuật'...

**Entity liên quan:**
- Lăng Vân: ...
```

**Lợi ích**: 
- ✅ LLM biết chương 4 sẽ về viên đá màu xám
- ✅ Có thể cài cắm: "Lăng Vân cầm viên đá xám, chợt thấy nó ấm lên..."
- ✅ Kết chương 3 có thể hint về Trích Tinh Thuật

## Token Cost

**Impact**: +100-150 tokens mỗi chapter

**Justification**:
- Preview chỉ 300 chars (~75-100 tokens)
- +Title và formatting (~25-50 tokens)
- **Total**: ~100-150 tokens extra per chapter

**ROI**: 
- Tăng quality đáng kể
- Giảm cần edit sau
- Better foreshadowing tự động
- ✅ **Worth it!**

## Files Thay Đổi

1. ✅ `src/chapter_writer.py`
   - Thêm `_format_next_chapter_summary()`
   - Cập nhật `_create_writing_prompt()`

2. ✅ `main.py`
   - Cập nhật `generate_batch()` để pass next_chapter_outline
   - Cập nhật `_generate_chapter()` signature
   - Cập nhật `_prepare_chapter_context()` để include next_chapter_outline

3. ✅ `test_next_chapter_prompt.py` (new)
   - Test script để verify

4. ✅ `NEXT_CHAPTER_PREVIEW_UPDATE.md` (this file)
   - Documentation

## Kết Luận

Thay đổi này giúp:
- ✅ LLM có đầy đủ context về hướng phát triển
- ✅ Foreshadowing chính xác và có mục đích
- ✅ Chapter transitions mượt mà hơn
- ✅ Story flow tự nhiên và chặt chẽ
- ✅ Giảm cần human intervention để fix continuity

**Trade-off**: +100-150 tokens/chapter, nhưng quality improvement đáng giá!

---

**Status**: ✅ Implemented & Ready to Test  
**Impact**: High (Better continuity & foreshadowing)  
**Cost**: Low (+100-150 tokens per chapter)  
**Priority**: High  
