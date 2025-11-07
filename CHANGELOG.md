# Changelog

All notable changes to the AI Story Generation System will be documented in this file.

## [1.3.0] - 2025-11-07

### 🏗️ Major Refactoring - Project-Based Structure & Detailed Logging

**Breaking Changes:**
- All project data now stored in `projects/{project_id}/` structure
- Modules now require `paths` parameter in `__init__()`
- Logger requires `project_id` parameter
- Config `paths` structure completely changed

**New Features:**
- ✨ **Project-based folder structure**: Each project has isolated directory
- ✨ **Detailed LLM request logging**: Every API call logged to separate JSON file
- ✨ **Exception logging**: Failed requests saved with full prompts
- ✨ **Batch/Chapter context**: All LLM calls tagged with batch_id/chapter_id
- ✨ **Complete audit trail**: Full prompts, responses, errors, metrics per request

**File Organization:**
```
projects/{project_id}/
  outputs/          # All output files
    chapters/
    outlines/
    entities/
    events/
    conflicts/
    summaries/
  checkpoints/      # Checkpoint files
  logs/             # Project logs
    llm_requests/   # Individual LLM request logs (NEW)
```

**LLM Request Logging:**
- File naming: `{task}_batch{N}_chapter{M}_{timestamp}.json`
- Contains: system prompt, user prompt, response, error, metrics
- Organized by task/batch/chapter for easy analysis

**Core Changes:**
- `src/utils.py`: New `get_project_paths()`, `ensure_project_directories()`
- `src/utils.py`: Logger adds `log_llm_request()`, `log_llm_error()`
- `src/llm_client.py`: Added `batch_id`, `chapter_id` parameters to `call()`
- `main.py`: Changed from `story_id` to `project_id`
- All modules: Added `paths` parameter, updated file operations
- `config.yaml`: New `paths` structure with `projects_base_dir`

**CLI Changes:**
- New: `--project-id` (preferred)
- Backward compatible: `--story-id` (aliased to `--project-id`)

**Documentation:**
- `PROJECT_STRUCTURE_UPDATE.md` - Comprehensive refactoring guide
- `UPDATE_MODULES.md` - Module-by-module changes

**Benefits:**
- Complete isolation between projects
- Full debugging capability with request logs
- Better cost analysis per task/batch/chapter
- Easier error diagnosis
- Audit trail for all LLM interactions

## [1.2.0] - 2025-11-07

### 🔄 Refactoring - Random Key Selection

**Breaking Changes:**
- `gemini_call_text_free()`, `gemini_call_json_free()`, and `gemini_batch()` no longer accept `keys`, `keys_file`, or `keys_env` parameters
- `LLMClient.__init__()` no longer loads or caches API keys in `self.api_keys` attribute

**Key Changes:**
- ✨ Keys are now loaded fresh on **each API call** for true random selection
- ✨ Added `_get_config_keys_path()` to automatically read keys file path from `config.yaml`
- ✨ Enhanced `load_keys()` to auto-detect config path and shuffle keys randomly
- ✨ Each API call now uses a different random key, improving load distribution
- ✨ Keys list is refreshed on every call, automatically excluding recently disabled keys

**Benefits:**
- 🚀 Better load distribution across all API keys
- 🚀 Reduced rate limiting on individual keys
- 🚀 Simpler code with less state management
- 🚀 Auto-refresh of key list without restart
- 🚀 Config-driven key file location

**Migration Guide:**
```python
# ❌ Old code (will break)
client = LLMClient(config, logger, cost_tracker)
my_keys = client.api_keys  # No longer exists

response = gemini_call_text_free(
    system_prompt="...",
    user_prompt="...",
    keys=my_keys  # No longer accepted
)

# ✅ New code
client = LLMClient(config, logger, cost_tracker)
# No need to access keys

response = gemini_call_text_free(
    system_prompt="...",
    user_prompt="..."
    # Keys loaded automatically from config
)
```

**Documentation:**
- Added `REFACTORING_NOTES.md` with detailed technical explanation
- Added `test_random_keys.py` to verify random key selection

## [1.1.0] - 2025-01-07

### 🔄 Major Changes - Gemini API Integration

**Breaking Changes:**
- Migrated from OpenAI to Google Gemini API
- Changed API key configuration method

**New Features:**
- ✨ Multi-key rotation system for Gemini API
- ✨ Automatic key rotation on rate limits (HTTP 429)
- ✨ Intelligent fallback model selection
- ✨ Disabled key tracking with auto-recovery (5 hours)
- ✨ Support for multiple Gemini models (Pro, Flash, Flash Lite, Gemma)

**LLM Client Updates:**
- Replaced OpenAI client with Gemini client pool
- Added `gemini_call_text_free()` and `gemini_call_json_free()`
- Implemented automatic retry logic (429, 503, network errors)
- Token estimation for Vietnamese text (2.5 chars/token)
- Gemini-specific cost calculation

**Configuration Changes:**
- Updated default models to Gemini 2.5 series
- Chapter writing: `gemini-2.5-pro`
- Other tasks: `gemini-2.5-flash`
- Added `keys_file` configuration
- Updated pricing for Gemini models

**Dependencies:**
- Removed: `openai`, `tiktoken`, `anthropic`
- Added: `requests`, `regex`

**Setup Changes:**
- Keys now stored in `auth_files/keys.txt` (one per line)
- Or via `GOOGLE_API_KEYS` environment variable
- Added `auth_files/disable_log.json` for key tracking

### 📚 Documentation

- Added `GEMINI_SETUP.md` with comprehensive setup guide
- Updated `README.md` for Gemini configuration
- Updated `QUICKSTART.md` with new setup steps
- Updated all examples to use Gemini

### 🐛 Bug Fixes

- Fixed cost tracking for non-OpenAI models
- Improved error handling for rate limits
- Better JSON parsing from model responses

---

## [1.0.0] - 2025-01-07

### 🎉 Initial Release

Complete AI-powered story generation system for Vietnamese cultivation novels (tu tiên truyện).

#### ✨ Features

**Core System**
- Checkpoint & resume functionality
- Comprehensive logging (prompts, responses, tokens, costs)
- Cost tracking with configurable pricing
- Task-specific LLM configurations
- Modular architecture

**Story Generation Pipeline**
- Motif loading from JSON with random/filtered selection
- Outline generation with foreshadowing
- Entity extraction and management (7 categories)
- Chapter writing (configurable word count)
- Post-chapter processing (events, conflicts, summaries)

**Entity Categories**
- Characters (nhân vật)
- Locations (địa điểm)
- Items (vật phẩm)
- Spiritual Herbs (linh dược)
- Beasts (yêu thú)
- Techniques (công pháp)
- Factions (thế lực)

**Conflict Management**
- Timeline-based classification (immediate to epic)
- Status tracking (active/resolved)
- Automatic selection for next batch

**Context Management**
- Intelligent entity selection
- Event importance scoring
- Super summary generation
- Multi-level context (outline, entities, summaries, etc.)

#### 📦 Components

**Core Modules**
- `utils.py`: File I/O, logging, cost tracking
- `checkpoint.py`: State management and resume
- `llm_client.py`: OpenAI API wrapper

**Pipeline Modules**
- `motif_loader.py`: Motif loading and selection
- `outline_generator.py`: Chapter outline generation
- `entity_manager.py`: Entity extraction and tracking
- `chapter_writer.py`: Chapter content generation
- `post_processor.py`: Post-chapter analysis

**Scripts**
- `main.py`: Full pipeline orchestrator
- `scripts.py`: Individual step execution

#### 📚 Documentation

- `README.md`: Comprehensive user guide
- `QUICKSTART.md`: 5-minute quick start
- `ARCHITECTURE.md`: System architecture documentation
- `SUMMARY.md`: Project completion summary
- Example configuration and data files

#### ⚙️ Configuration

- YAML-based configuration system
- Task-specific LLM settings
- Configurable paths and parameters
- Environment variable support

#### 🔧 Tools

- Installation test script
- Individual step scripts
- Batch processing support
- Cost summary generation

### 📋 Requirements

- Python 3.8+
- openai >= 1.0.0
- pyyaml >= 6.0
- tiktoken >= 0.5.0
- python-dotenv >= 1.0.0
- pydantic >= 2.0.0

### 🎯 Usage

```bash
# Full pipeline
python main.py --story-id my_story --batches 3

# Individual steps
python scripts.py outline --batch 1 --story-id my_story
python scripts.py chapter --chapter 1 --story-id my_story

# Test installation
python test_installation.py
```

### 📊 Output Structure

```
output/
├── chapters/        # Chapter content and metadata
├── outlines/        # Batch outlines
├── entities/        # Entity database
├── events/          # Event tracking
├── conflicts/       # Conflict management
├── summaries/       # Chapter and super summaries
└── cost_summary.json
```

### 🔐 Security

- API keys from environment variables
- No hardcoded credentials
- Safe file operations

### 🎨 Customization Points

- Entity types
- LLM providers
- Prompt templates
- Post-processing tasks
- Configuration parameters

---

## Future Enhancements (Planned)

### [1.1.0] - TBD
- [ ] Anthropic Claude support
- [ ] Parallel chapter generation
- [ ] Web UI dashboard
- [ ] Advanced caching
- [ ] Multi-language support

### [1.2.0] - TBD
- [ ] Character relationship graph
- [ ] Plot consistency checker
- [ ] Auto-editing suggestions
- [ ] Export to EPUB/PDF
- [ ] Collaboration features

### [2.0.0] - TBD
- [ ] Real-time generation
- [ ] Interactive story planning
- [ ] AI-assisted editing
- [ ] Version control for stories
- [ ] Publishing integration

---

**Version History**
- v1.0.0 (2025-01-07): Initial release with complete feature set
