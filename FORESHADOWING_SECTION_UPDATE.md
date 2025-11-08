# Foreshadowing Section Implementation

## Tổng Quan

Bổ sung section **Foreshadowing (Cài cắm)** vào prompt viết chương để LLM biết các chi tiết setup cần được cài cắm trong chương hiện tại, giúp tạo sự liên kết và foreshadowing tốt hơn cho các chương sau.

## Vấn Đề

Khi kiểm tra log file `/root/test_writer/projects/story_001/logs/llm_requests/chapter_writing_chapter001_*.txt`, phát hiện prompt viết chương **thiếu hoàn toàn phần foreshadowing**:

- Outline JSON đã có dữ liệu foreshadowing với cấu trúc: `{detail, reveal_chapter, importance}`
- Nhưng prompt gửi cho LLM không chứa thông tin này
- LLM không biết cần cài cắm setup gì cho các chương sau
- Dẫn đến thiếu continuity và foreshadowing mechanics

## Giải Pháp

### 1. Thêm Method `_format_foreshadowing()`

**File:** `src/chapter_writer.py`

Thêm method mới sau `_format_conflicts()`:

```python
def _format_foreshadowing(self, foreshadowing: List[Dict[str, Any]]) -> str:
    """Format foreshadowing information from outline."""
    if not foreshadowing:
        return "Không có"
    
    foreshadowing_list = []
    for fs in foreshadowing:
        detail = fs.get('detail', '')
        reveal_chapter = fs.get('reveal_chapter', '?')
        importance = fs.get('importance', 0)
        
        fs_info = f"- (tiết lộ c{reveal_chapter}) {detail}"
        fs_info += f" (quan trọng: {importance:.1f})"
        foreshadowing_list.append(fs_info)
    
    return "\n".join(foreshadowing_list)
```

**Tính năng:**
- Extract `detail`, `reveal_chapter`, `importance` từ foreshadowing data
- Format thành dạng: `- (tiết lộ c{N}) {detail} (quan trọng: {score})`
- Xử lý trường hợp empty: return "Không có"
- Hỗ trợ multiple foreshadowing items cho mỗi chapter

### 2. Cập Nhật Prompt Template

**File:** `src/chapter_writer.py` - Method `_create_writing_prompt()`

Thêm foreshadowing section vào OUTLINE, giữa Conflicts và Settings:

```python
Mâu thuẫn:
{self._format_conflicts(chapter_outline.get('conflicts', []))}

Foreshadowing (Cài cắm):
{self._format_foreshadowing(chapter_outline.get('foreshadowing', []))}

Địa điểm: {', '.join(chapter_outline.get('settings', []))}
```

**Vị trí:**
- Sau phần "Mâu thuẫn" 
- Trước phần "Địa điểm"
- Trong phần **OUTLINE CHƯƠNG** (không phải NGỮ CẢNH)

## Cấu Trúc Dữ Liệu

### Input (từ outline.json)

```json
{
  "chapters": [
    {
      "chapter_number": 1,
      "foreshadowing": [
        {
          "detail": "Khi trúng độc, Lăng Thiên nhận ra 'Cửu Chuyển Phệ Hồn Tán' có một mùi hương Bạch Ngọc Lan rất nhạt, ông ghi nhớ chi tiết này.",
          "reveal_chapter": 3,
          "importance": 0.9
        },
        {
          "detail": "Dù kinh mạch của thân thể mới bị đứt gãy, Lăng Thiên cảm nhận được một luồng nhiệt khí lạ trong kinh mạch, dường như là dấu hiệu của Huyền Thiên Tâm Pháp.",
          "reveal_chapter": 2,
          "importance": 0.8
        }
      ]
    }
  ]
}
```

### Output (trong prompt)

```
Foreshadowing (Cài cắm):
- (tiết lộ c3) Khi trúng độc, Lăng Thiên nhận ra 'Cửu Chuyển Phệ Hồn Tán' có một mùi hương Bạch Ngọc Lan rất nhạt, ông ghi nhớ chi tiết này. (quan trọng: 0.9)
- (tiết lộ c2) Dù kinh mạch của thân thể mới bị đứt gãy, Lăng Thiên cảm nhận được một luồng nhiệt khí lạ trong kinh mạch, dường như là dấu hiệu của Huyền Thiên Tâm Pháp. (quan trọng: 0.8)
```

## Testing

### Test Script

File: `test_foreshadowing.py`

**Test Cases:**
1. **Method existence check** - Verify `_format_foreshadowing()` exists with correct signature
2. **Method implementation** - Check extract logic, formatting, empty handling
3. **Prompt structure** - Verify section header, method call, correct position
4. **Integration test** - Verify compatibility with existing outline.json structure

### Chạy Test

```bash
python test_foreshadowing.py
```

### Kết Quả Test

```
✅ PASSED: _format_foreshadowing() method exists
✅ PASSED: Method accepts 'foreshadowing' parameter
✅ PASSED: Method has descriptive docstring
✅ ALL IMPLEMENTATION CHECKS PASSED
✅ PASSED: Foreshadowing section header found in prompt template
✅ PASSED: _format_foreshadowing() method called correctly
✅ PASSED: Foreshadowing positioned correctly (Conflicts → Foreshadowing → Settings)
✅ Found 5 chapters with foreshadowing
✅ Total 10 foreshadowing items across all chapters
✅ PASSED: Outline foreshadowing structure matches expected format
```

## Tích Hợp Với Hệ Thống

### Liên Kết Với OutlineGenerator

Foreshadowing data được tạo bởi `OutlineGenerator` với các ràng buộc:
- Chỉ foreshadow cho **+1 hoặc +2 chapters** (không quá xa)
- Mỗi chapter có 2-3 foreshadowing items
- Có importance score để xác định mức độ quan trọng

**File:** `src/outline_generator.py`

Prompt đã được cập nhật với quy tắc foreshadowing:
```
LƯU Ý VỀ FORESHADOWING:
- Chapter 1: foreshadow cho chapter 2 hoặc 3 (reveal_chapter: 2 hoặc 3)
- Chapter 2: foreshadow cho chapter 3 hoặc 4 (reveal_chapter: 3 hoặc 4)
- ...
```

### Luồng Dữ Liệu

```
1. OutlineGenerator tạo outline.json với foreshadowing array
2. ChapterWriter đọc outline cho chapter hiện tại
3. _format_foreshadowing() format foreshadowing array
4. Foreshadowing section được thêm vào prompt
5. LLM nhận prompt với foreshadowing instructions
6. LLM cài cắm các chi tiết setup trong chapter content
```

## Lợi Ích

### 1. Setup/Payoff Mechanics
- LLM biết cần plant các detail gì để payoff ở chapters sau
- Tránh retcon hoặc plot holes
- Tạo sự cohesive trong storytelling

### 2. Controlled Foreshadowing
- Constraint +2 chapters giúp foreshadowing không quá xa
- Importance score giúp prioritize các setup quan trọng
- Reveal chapter rõ ràng giúp track payoff

### 3. Consistency
- Foreshadowing từ outline đảm bảo consistency với plot
- Không bị duplicate hoặc contradict
- Follow planning từ outline phase

## Ví Dụ Thực Tế

### Chapter 1 Outline

```json
"foreshadowing": [
  {
    "detail": "Khi trúng độc, Lăng Thiên nhận ra 'Cửu Chuyển Phệ Hồn Tán' có một mùi hương Bạch Ngọc Lan rất nhạt.",
    "reveal_chapter": 3,
    "importance": 0.9
  }
]
```

### Trong Prompt

```
Foreshadowing (Cài cắm):
- (tiết lộ c3) Khi trúng độc, Lăng Thiên nhận ra 'Cửu Chuyển Phệ Hồn Tán' có một mùi hương Bạch Ngọc Lan rất nhạt. (quan trọng: 0.9)
```

### Expected Chapter Content

Chapter 1 nên có scene:
> Lăng Thiên nằm trên giường, cảm nhận luồng độc khí lan tỏa. Trong hơi thở, ông chợt ngửi thấy một mùi hương rất nhạt, quen thuộc nhưng không nhớ nổi. "Bạch Ngọc Lan?" Ông tự hỏi, nhưng mùi hương quá yếu để xác định...

### Payoff ở Chapter 3

Chapter 3 reveal:
> "Bạch Ngọc Lan! Hóa ra 'Cửu Chuyển Phệ Hồn Tán' có thành phần Bạch Ngọc Lan!" Lăng Thiên sửng sốt nhận ra. Ông nhớ lại mùi hương nhạt khi bị trúng độc...

## Backward Compatibility

✅ **Không Breaking Changes:**
- Sử dụng `chapter_outline.get('foreshadowing', [])` - default empty list
- Empty list → return "Không có" (graceful handling)
- Không ảnh hưởng đến existing prompts nếu outline không có foreshadowing

## Files Modified

### 1. src/chapter_writer.py
- Added: `_format_foreshadowing()` method (line ~358)
- Modified: `_create_writing_prompt()` - added foreshadowing section in prompt template (line ~170)

### 2. test_foreshadowing.py (NEW)
- Test suite for foreshadowing implementation
- 4 test cases covering method, structure, integration

## Next Steps

### 1. Generate New Chapter
```bash
python main.py
```

### 2. Verify Log File
Check `/root/test_writer/projects/story_001/logs/llm_requests/chapter_writing_chapter00X_*.txt`

Should contain:
```
Foreshadowing (Cài cắm):
- (tiết lộ c3) [detail] (quan trọng: X.X)
- (tiết lộ c2) [detail] (quan trọng: X.X)
```

### 3. Verify Chapter Content
Check generated chapter có cài cắm các foreshadowing details hay không

## Related Documentation

- `FORESHADOWING_CONSTRAINT_UPDATE.md` - Constraint foreshadowing to +2 chapters in outline
- `NEXT_CHAPTER_PREVIEW_UPDATE.md` - Next chapter preview for continuity
- `ENTITY_EVENTS_CONTEXT_UPDATE.md` - Entity events context feature

## Summary

Bổ sung thành công **Foreshadowing section** vào chapter writing prompt:
- ✅ Method `_format_foreshadowing()` format dữ liệu từ outline
- ✅ Section được insert đúng vị trí (giữa Conflicts và Settings)
- ✅ Compatible với outline structure hiện tại
- ✅ Tested và verified
- ✅ Backward compatible

LLM giờ sẽ nhận được explicit instructions về foreshadowing cần cài cắm, giúp tạo better setup/payoff và story continuity.
