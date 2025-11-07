# 🔄 Migration Summary: OpenAI → Gemini API

## ✅ Hoàn thành chuyển đổi sang Gemini API

### 📋 Những thay đổi chính

#### 1. **LLM Client** (`src/llm_client.py`)
- ✅ Thay thế OpenAI client bằng Gemini client pool
- ✅ Sử dụng `gemini_call_text_free()` và `gemini_call_json_free()`
- ✅ Token estimation cho tiếng Việt (2.5 chars/token)
- ✅ Cost calculation theo pricing Gemini
- ✅ Automatic retry & key rotation

#### 2. **Configuration** (`config/config.yaml`)
- ✅ Provider: `gemini`
- ✅ Models:
  - **Chapter writing:** `gemini-2.5-pro` (chất lượng cao)
  - **Other tasks:** `gemini-2.5-flash` (nhanh, rẻ)
- ✅ Pricing updated cho Gemini models
- ✅ Added `keys_file` configuration

#### 3. **API Keys Management**
- ✅ Multiple keys support
- ✅ File-based: `auth_files/keys.txt` (mỗi key một dòng)
- ✅ Environment: `GOOGLE_API_KEYS=key1,key2,key3`
- ✅ Automatic key rotation on 429
- ✅ Disabled key tracking với auto-recovery (5 giờ)

#### 4. **Dependencies** (`requirements.txt`)
- ❌ Removed: `openai`, `tiktoken`, `anthropic`
- ✅ Added: `requests`, `regex`
- ✅ Kept: `pyyaml`, `python-dotenv`, `pydantic`

#### 5. **Documentation Updates**
- ✅ `README.md` - Updated setup instructions
- ✅ `QUICKSTART.md` - New quick start guide
- ✅ `GEMINI_SETUP.md` - Comprehensive Gemini guide (NEW)
- ✅ `CHANGELOG.md` - Version 1.1.0 release notes
- ✅ `.env.example` - Gemini configuration
- ✅ `test_installation.py` - Updated tests

#### 6. **Security** (`.gitignore`)
- ✅ Added `auth_files/keys.txt`
- ✅ Added `auth_files/disable_log.json`
- ✅ Added `*.bak`, `*.backup`

---

## 🎯 Models & Usage

### Gemini 2.5 Pro
- **Task:** Chapter writing
- **Cost:** $1.25/1M input, $5.00/1M output
- **Why:** Chất lượng cao nhất, reasoning tốt

### Gemini 2.5 Flash  
- **Tasks:** Outline, entities, events, conflicts, summaries
- **Cost:** $0.075/1M input, $0.30/1M output
- **Why:** Nhanh, rẻ, chất lượng tốt

### Auto Fallback
- Gemini 2.5 Flash Lite (khi Flash lỗi)
- Gemma 3 27B IT (testing)

---

## 📊 Cost Comparison

### Trước (OpenAI GPT-4):
- 50 chapters × 5000 words
- Cost: ~$150-200

### Sau (Gemini Pro + Flash):
- Chapter writing (Pro): ~$40
- Other tasks (Flash): ~$2
- **Total: ~$42** (tiết kiệm 70-80%)

### Option Flash only:
- **Total: ~$5** (tiết kiệm 97%)

---

## 🚀 Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Gemini API Keys
- Visit: https://aistudio.google.com/app/apikey
- Create 3-5 API keys (free tier có generous limits)

### 3. Configure Keys

**Option A: File (Recommended)**
```bash
mkdir -p auth_files
cat > auth_files/keys.txt << EOF
AIzaSyAbc123...key1
AIzaSyDef456...key2
AIzaSyGhi789...key3
EOF
```

**Option B: Environment**
```bash
export GOOGLE_API_KEYS="key1,key2,key3"
```

### 4. Test
```bash
python test_installation.py
python main.py --story-id test --batches 1
```

---

## 🔧 Key Features

### 1. **Multi-Key Rotation**
- Tự động rotate keys khi rate limit
- Load balancing across keys
- Automatic retry logic

### 2. **Smart Error Handling**
- HTTP 429: Rotate key, retry 3 times
- HTTP 503: Sleep 60s, retry 3 times
- Network errors: Retry with exponential backoff

### 3. **Cost Optimization**
- Pro cho chapter writing (quan trọng)
- Flash cho tasks khác (tiết kiệm)
- Automatic fallback khi cần

### 4. **Disabled Key Management**
- Track keys bị disable
- Auto-enable sau 5 giờ
- Log file: `auth_files/disable_log.json`

---

## 📝 Configuration Examples

### High Quality (Expensive)
```yaml
task_configs:
  chapter_writing:
    model: "gemini-2.5-pro"
  outline_generation:
    model: "gemini-2.5-pro"
  entity_extraction:
    model: "gemini-2.5-pro"
```

### Balanced (Recommended)
```yaml
task_configs:
  chapter_writing:
    model: "gemini-2.5-pro"  # Chất lượng
  outline_generation:
    model: "gemini-2.5-flash"  # Tiết kiệm
  entity_extraction:
    model: "gemini-2.5-flash"
```

### Budget (Cheap)
```yaml
task_configs:
  chapter_writing:
    model: "gemini-2.5-flash"
  outline_generation:
    model: "gemini-2.5-flash"
  entity_extraction:
    model: "gemini-2.5-flash"
```

---

## 🐛 Troubleshooting

### No API keys found
```bash
# Check file
cat auth_files/keys.txt

# Check env
echo $GOOGLE_API_KEYS

# Create file
mkdir -p auth_files
nano auth_files/keys.txt
```

### HTTP 429 (Rate Limit)
- Tự động retry 3 lần
- Rotate sang key khác
- Nếu vẫn lỗi: thêm nhiều keys hơn

### All keys disabled
```bash
# Check log
cat auth_files/disable_log.json

# Reset
rm auth_files/disable_log.json

# Or wait 5 hours for auto-recovery
```

---

## ✅ Testing Checklist

- [x] LLM client updated
- [x] Config updated
- [x] Dependencies updated
- [x] Documentation updated
- [x] Test script updated
- [x] .gitignore updated
- [x] Example files created
- [x] Security measures in place

---

## 📚 New Files

1. `GEMINI_SETUP.md` - Comprehensive setup guide
2. `auth_files/keys.txt.example` - Example keys file
3. `MIGRATION.md` - This file

---

## 🎉 Benefits

1. **Cost:** Giảm 70-97% chi phí
2. **Speed:** Gemini Flash nhanh hơn GPT-4
3. **Quality:** Pro model chất lượng tương đương GPT-4
4. **Reliability:** Multi-key rotation, auto-retry
5. **Free Tier:** Generous limits cho testing

---

## 🔜 Next Steps

1. Test với batch nhỏ
2. Monitor cost qua `output/cost_summary.json`
3. Adjust models dựa trên quality/cost
4. Scale up khi hài lòng

---

**Migration completed!** 🎊

Version: 1.1.0
Date: 2025-01-07
