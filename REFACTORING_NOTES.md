# Refactoring Notes: Random Key Selection

## Ngày thay đổi: 2025-11-07

## Mục đích
Mỗi lần gọi API Gemini, hệ thống sẽ tự động load lại danh sách keys và chọn ngẫu nhiên một key để sử dụng. Điều này giúp:
- Phân tán tải đều trên tất cả các API keys
- Giảm nguy cơ bị rate limit trên một key cụ thể
- Tự động loại trừ các key đã bị disable (dưới 5 giờ)
- Đơn giản hóa code, không cần quản lý key pool ở level cao

## Các thay đổi chính

### 1. `src/gemini_client_pool.py`

#### a) Thêm hàm `_get_config_keys_path()`
```python
def _get_config_keys_path() -> Optional[str]:
    """Load keys file path from config.yaml."""
```
- Tự động đọc path của file keys từ `config/config.yaml`
- Lấy từ `default_llm.keys_file`
- Fallback về `auth_files/keys.txt` nếu không tìm thấy trong config

#### b) Cập nhật `load_keys()`
```python
def load_keys(keys_file: Optional[str] = None, keys_env: Optional[str] = None) -> List[str]:
```
- Nếu `keys_file=None`, tự động load path từ config
- Shuffle ngẫu nhiên danh sách keys sau khi load
- Loại bỏ keys đã bị disable trong vòng 5 giờ qua
- In ra số lượng keys active sau khi filter

#### c) Đơn giản hóa `gemini_call_text_free()`
**Trước:**
```python
def gemini_call_text_free(system_prompt, user_prompt, *,
                     keys: Optional[List[str]] = None,
                     keys_file: Optional[str] = "keys.txt",
                     keys_env: Optional[str] = None, ...)
```

**Sau:**
```python
def gemini_call_text_free(system_prompt, user_prompt, *,
                     model: Optional[str] = None,
                     temperature: float = 0.3,
                     response_mime_type: Optional[str] = None,
                     per_job_sleep: float = DEFAULT_PER_JOB_SLEEP) -> str:
```

- Loại bỏ params: `keys`, `keys_file`, `keys_env`
- Mỗi lần gọi tự động `_keys = load_keys()` để lấy key ngẫu nhiên mới
- Tạo `KeyPool` mới cho mỗi request

#### d) Đơn giản hóa `gemini_call_json_free()`
- Tương tự như `gemini_call_text_free()`
- Loại bỏ tất cả params liên quan đến keys
- Tự động load keys trong mỗi lần gọi

### 2. `src/llm_client.py`

#### a) Đơn giản hóa `__init__()`
**Trước:**
```python
def __init__(self, config, logger, cost_tracker):
    # ...
    keys_file = self.default_config.get('keys_file', 'auth_files/keys.txt')
    self.api_keys = load_keys(keys_file=keys_file)
    if not self.api_keys:
        raise ValueError("No Gemini API keys found...")
    self.logger.info(f"Loaded {len(self.api_keys)} Gemini API keys")
```

**Sau:**
```python
def __init__(self, config, logger, cost_tracker):
    # ...
    # Không cần load keys ở đây nữa
    self.logger.info("LLMClient initialized. Keys will be loaded dynamically on each API call.")
```

- Loại bỏ hoàn toàn việc load và cache keys
- Không cần import `load_keys` nữa
- Đơn giản hóa initialization

#### b) Cập nhật `call()`
**Trước:**
```python
response_text = gemini_call_text_free(
    system_prompt=sys_msg,
    user_prompt=prompt,
    model=model,
    temperature=temperature,
    keys=self.api_keys,  # ❌ Truyền cached keys
    per_job_sleep=0.1
)
```

**Sau:**
```python
response_text = gemini_call_text_free(
    system_prompt=sys_msg,
    user_prompt=prompt,
    model=model,
    temperature=temperature,
    per_job_sleep=0.1  # ✅ Không cần truyền keys
)
```

- Loại bỏ tham số `keys=self.api_keys`
- Keys sẽ tự động load mới trong mỗi lần gọi

## Luồng hoạt động mới

```
1. User gọi LLMClient.call()
   ↓
2. llm_client.py gọi gemini_call_text_free() (không truyền keys)
   ↓
3. gemini_call_text_free() tự động:
   - Gọi load_keys() để load danh sách keys mới
   - Load từ config/config.yaml -> default_llm.keys_file
   - Shuffle ngẫu nhiên
   - Loại bỏ keys disabled (dưới 5h)
   ↓
4. Tạo KeyPool với danh sách keys đã shuffle
   ↓
5. Lấy key ngẫu nhiên từ pool (do đã shuffle, mỗi lần khác nhau)
   ↓
6. Gọi API với key đó
   ↓
7. Nếu 429: disable key đó, lấy key khác từ pool
```

## Lợi ích

### 1. Random Key Selection
- Mỗi API call load keys mới → shuffle mới → key ngẫu nhiên khác nhau
- Không bị "dính" vào một key cố định
- Phân tán tải tự nhiên

### 2. Always Fresh Keys
- Mỗi lần gọi đều check disable log mới nhất
- Tự động loại trừ keys vừa bị disable
- Không cần restart app để refresh key list

### 3. Simpler Code
- Không cần quản lý key pool ở LLMClient
- Không cần cache keys
- Ít state, ít bugs

### 4. Config-Driven
- Path của keys file đọc từ config
- Dễ thay đổi location của keys
- Không hardcode paths

## Testing

Chạy test để verify:
```bash
python test_random_keys.py
```

Test sẽ kiểm tra:
1. Keys load được từ config
2. Mỗi API call hoạt động độc lập
3. Keys được chọn ngẫu nhiên

## Migration Guide

Nếu code cũ có:
```python
# ❌ Cách cũ
client = LLMClient(config, logger, cost_tracker)
# client.api_keys sẽ có list keys cached
```

Bây giờ:
```python
# ✅ Cách mới
client = LLMClient(config, logger, cost_tracker)
# Không có client.api_keys nữa, keys load tự động trong mỗi call
```

Nếu gọi trực tiếp gemini_call_text_free:
```python
# ❌ Cách cũ
response = gemini_call_text_free(
    system_prompt="...",
    user_prompt="...",
    keys=my_keys,
    keys_file="path/to/keys.txt"
)

# ✅ Cách mới
response = gemini_call_text_free(
    system_prompt="...",
    user_prompt="..."
    # Keys tự động load từ config
)
```

## Configuration

Trong `config/config.yaml`:
```yaml
default_llm:
  provider: "gemini"
  model: "gemini-2.5-flash"
  keys_file: "auth_files/keys.txt"  # ← Path này sẽ được dùng tự động
```

## Notes

- Yêu cầu thư viện `pyyaml` (đã có trong requirements.txt)
- Config file phải tồn tại tại `config/config.yaml`
- Keys file phải có ít nhất 1 key active
- Disabled keys được track trong `auth_files/disable_log.json`

## Backward Compatibility

⚠️ **Breaking Changes:**
- `LLMClient.__init__()` không còn thuộc tính `api_keys`
- `gemini_call_text_free()` và `gemini_call_json_free()` không còn nhận params `keys`, `keys_file`, `keys_env`

Code cần update nếu:
- Truy cập trực tiếp `client.api_keys`
- Truyền `keys` parameter vào gemini functions
- Expect keys được cache trong LLMClient
