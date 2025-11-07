# Project Structure Update - Version 1.3.0

## Date: 2025-11-07

## Overview
Major refactoring to organize all project data in project-specific folders and implement detailed LLM request logging.

## Changes Summary

### 1. Project-Based Folder Structure

**Old Structure:**
```
output/
  chapters/
  outlines/
  entities/
  events/
  conflicts/
  summaries/
checkpoints/
logs/
```

**New Structure:**
```
projects/
  {project_id}/
    outputs/
      chapters/
      outlines/
      entities/
      events/
      conflicts/
      summaries/
    checkpoints/
    logs/
      llm_requests/    # New: Detailed LLM request logs
```

### 2. Detailed LLM Request Logging

Each LLM request is now logged to a separate JSON file with complete context:

**File Naming Pattern:**
```
{task_name}_batch{batch_id}_chapter{chapter_id}_{timestamp}.json
```

**Examples:**
- `outline_generation_batch001_20251107_152030_123456.json`
- `chapter_writing_batch001_chapter005_20251107_153045_789012.json`
- `event_extraction_chapter010_20251107_154020_345678.json`

**Log Content:**
```json
{
  "timestamp": "2025-11-07T15:20:30.123456",
  "project_id": "story_001",
  "task_name": "chapter_writing",
  "batch_id": 1,
  "chapter_id": 5,
  "model": "gemini-2.5-pro",
  "prompts": {
    "system": "System prompt content...",
    "user": "User prompt content..."
  },
  "response": "LLM response...",
  "error": null,
  "metrics": {
    "tokens": {
      "input": 1500,
      "output": 3000,
      "total": 4500
    },
    "cost": 0.025,
    "duration": 12.5
  }
}
```

### 3. Exception Logging

When LLM calls fail, the system now:
1. Logs the error with full prompts to separate file
2. Saves to main log
3. Re-raises the exception for handling

**Error Log Example:**
```json
{
  "timestamp": "2025-11-07T15:25:45.678901",
  "project_id": "story_001",
  "task_name": "chapter_writing",
  "batch_id": 1,
  "chapter_id": 5,
  "model": "gemini-2.5-pro",
  "prompts": {
    "system": "...",
    "user": "..."
  },
  "response": null,
  "error": "HTTP 429: Rate limit exceeded",
  "metrics": null
}
```

## File-by-File Changes

### config/config.yaml
```yaml
# Old
paths:
  data_dir: "data"
  output_dir: "output"
  checkpoint_dir: "checkpoints"
  logs_dir: "logs"

# New
paths:
  projects_base_dir: "projects"
  project_subdirs:
    logs: "logs"
    checkpoints: "checkpoints"
    outputs: "outputs"
    chapters: "outputs/chapters"
    outlines: "outputs/outlines"
    entities: "outputs/entities"
    events: "outputs/events"
    conflicts: "outputs/conflicts"
    summaries: "outputs/summaries"
    llm_logs: "logs/llm_requests"
```

### src/utils.py

**New Functions:**
- `get_project_paths(project_id, config)` - Get all paths for a project
- `ensure_project_directories(project_id, config)` - Create project folders

**Logger Class Updates:**
- `__init__(name, project_id, config)` - Now requires project_id
- `log_llm_request(...)` - Log individual LLM request to separate file
- `log_llm_error(...)` - Log failed LLM requests with prompts

### src/llm_client.py

**LLMClient.call() Updates:**
- Added `batch_id` parameter
- Added `chapter_id` parameter
- Calls `logger.log_llm_request()` on success
- Calls `logger.log_llm_error()` on exception
- Enhanced exception handling

### main.py

**StoryGenerator Updates:**
- Constructor: `__init__(config_path, project_id)` (was `story_id`)
- Argument: `--project-id` (supports `--story-id` for backward compatibility)
- All modules initialized with `paths` parameter
- Uses `get_project_paths()` and `ensure_project_directories()`

### src/outline_generator.py

**Updates:**
- `__init__(..., paths)` - Added paths parameter
- `_save_outline()` - Uses `self.paths['outlines_dir']`
- `_load_outline()` - Uses `self.paths['outlines_dir']`
- All `llm_client.call()` include `batch_id=batch_num`

### src/entity_manager.py

**Updates:**
- `__init__(..., paths)` - Added paths parameter
- `entity_file` - Uses `paths['entities_dir']`
- `extract_entities_from_outlines()` - Passes `batch_id`
- `extract_entities_from_chapter()` - Passes `chapter_id`

### src/chapter_writer.py

**Updates:**
- `__init__(..., paths)` - Added paths parameter
- `write_chapter()` - Passes `chapter_id=chapter_num`
- `_save_chapter()` - Uses `self.paths['chapters_dir']`
- `_load_chapter()` - Uses `self.paths['chapters_dir']`

### src/post_processor.py

**Updates:**
- `__init__(..., paths)` - Added paths parameter
- All file paths use `paths['events_dir']`, `paths['conflicts_dir']`, `paths['summaries_dir']`
- `extract_events()` - Passes `chapter_id=chapter_num`
- `extract_conflicts()` - Passes `chapter_id=chapter_num`
- `generate_summary()` - Passes `chapter_id=chapter_num`
- `update_super_summary()` - Passes `chapter_id=chapter_num`

## Usage Changes

### Old Usage:
```bash
python main.py --story-id my_story --batches 2
```

### New Usage:
```bash
python main.py --project-id my_story --batches 2
```

**Note:** `--story-id` still works for backward compatibility.

## Benefits

### 1. Better Organization
- Each project completely isolated in its own folder
- Easy to manage multiple projects
- Clear separation of data

### 2. Complete Audit Trail
- Every LLM request logged with full context
- Can debug issues by reviewing exact prompts/responses
- Track which chapter/batch caused errors

### 3. Cost Analysis
- Detailed per-request cost tracking
- Can analyze costs by task type
- Easy to identify expensive operations

### 4. Error Debugging
- Failed requests logged with full prompts
- No information loss on errors
- Can replay failed requests

### 5. Development & Testing
- Can examine exact prompts sent
- Verify prompt engineering changes
- Compare prompts across batches/chapters

## Migration Guide

### For Existing Projects

If you have existing data in the old structure:

```bash
# Create new project structure
mkdir -p projects/old_story/

# Move data
mv output projects/old_story/outputs
mv checkpoints projects/old_story/checkpoints
mv logs projects/old_story/logs

# Create LLM logs directory
mkdir -p projects/old_story/logs/llm_requests
```

### For New Projects

Just run with `--project-id`:
```bash
python main.py --project-id new_story --batches 1
```

All folders will be created automatically in `projects/new_story/`.

## Backward Compatibility

✅ `--story-id` parameter still works (aliased to `--project-id`)
❌ Old hardcoded paths in config will not work

## Testing

To test the new structure:

```bash
# Test with a new project
python main.py --project-id test_project --batches 1

# Verify structure
ls -la projects/test_project/
ls -la projects/test_project/logs/llm_requests/

# Check LLM logs
cat projects/test_project/logs/llm_requests/*.json | head -50
```

## Future Enhancements

Potential improvements:
1. Web UI to browse LLM request logs
2. Analytics dashboard for cost/token usage
3. Replay failed requests with modified prompts
4. Compare prompts across different project versions
5. Export/import project data

## Breaking Changes

⚠️ **Important:** This update has breaking changes:

1. **Config Structure**: Old `paths` configuration will not work
2. **Module Initialization**: All modules now require `paths` parameter
3. **Logger Initialization**: Logger now requires `project_id` parameter
4. **File Locations**: All output files now in `projects/{project_id}/`

## Notes

- LLM request logs can grow large; consider cleanup strategy
- Each request creates a new file; monitor disk space
- Logs contain sensitive data (prompts); secure accordingly
- Consider archiving old project folders periodically
