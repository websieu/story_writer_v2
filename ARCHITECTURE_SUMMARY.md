# Architecture Summary - Quick Reference

## System Overview

**Hệ thống tự động sinh truyện tu tiên/kiếm hiệp bằng AI (Google Gemini)**

```
User Input → Main Orchestrator → [5 Processing Modules] → Output Files
```

## Core Pipeline (5 Steps)

```
1. Motif Loader      → Load story template
2. Outline Generator → Generate 5 chapter outlines
3. Entity Manager    → Extract characters, locations, items, etc.
4. Chapter Writer    → Write detailed chapter content
5. Post Processor    → Extract events, conflicts, summaries
```

## Data Flow Diagram

```
motif.json
    ↓
┌─────────────────────────────────────┐
│  Batch Generation Loop (5 chapters) │
├─────────────────────────────────────┤
│                                     │
│  Step 1: Load Motif                │
│          ↓                          │
│  Step 2: Generate Outlines          │
│          ↓                          │
│  Step 3: Extract Entities           │
│          ↓                          │
│  Step 4: Write Chapter 1-5          │
│          ↓                          │
│  Step 5: Post-Process Each          │
│          - Events                   │
│          - Conflicts                │
│          - Summary                  │
│          - New Entities             │
│                                     │
└─────────────────────────────────────┘
    ↓
projects/{project_id}/
    outputs/
        chapters/
        entities/
        events/
        conflicts/
    logs/
    checkpoints/
```

## Input/Output Quick Reference

### Inputs
- **Motif**: `data/motif.json` - Story templates
- **Config**: `config/config.yaml` - System settings
- **API Keys**: `auth_files/keys.txt` - Gemini API keys

### Outputs
- **Chapters**: `projects/{id}/outputs/chapters/chapter_{N}.txt`
- **Entities**: `projects/{id}/outputs/entities/entities.json`
- **Events**: `projects/{id}/outputs/events/events.json`
- **Conflicts**: `projects/{id}/outputs/conflicts/conflicts.json`
- **Checkpoint**: `projects/{id}/checkpoints/{id}_checkpoint.json`
- **Logs**: `projects/{id}/logs/llm_requests/*.txt`

## Module Summary

| Module | Input | Output | LLM Model |
|--------|-------|--------|-----------|
| Motif Loader | motif.json | motif object | N/A |
| Outline Generator | motif/context | 5 outlines | gemini-2.5-flash |
| Entity Manager | outlines/chapters | categorized entities | gemini-2.5-flash |
| Chapter Writer | outline + context | chapter text (5000+ words) | gemini-2.5-pro |
| Post Processor | chapter text | events, conflicts, summary | gemini-2.5-flash |

## LLM Usage Pattern

```
Task                    Model              Temp   Max Tokens
─────────────────────────────────────────────────────────────
Outline Generation     gemini-2.5-flash    0.8    4000
Entity Extraction      gemini-2.5-flash    0.3    3000
Chapter Writing        gemini-2.5-pro      0.85   8000  ← Most expensive
Event Extraction       gemini-2.5-flash    0.3    2000
Conflict Extraction    gemini-2.5-flash    0.3    2000
Summary Generation     gemini-2.5-flash    0.5    1500
```

## Checkpoint System

```
Before each step:
    if is_completed(step):
        load from file
    else:
        execute step
        mark_completed(step)
        save checkpoint
```

**Allows resume from any point!**

## Cost Estimation

For 15 chapters (3 batches):
- **Outline**: 3 batches × $0.10 = $0.30
- **Entities**: 3 batches × $0.20 = $0.60
- **Chapters**: 15 chapters × $0.50 = $7.50 ← Largest cost
- **Post-processing**: 15 chapters × $0.10 = $1.50
- **Total**: ~$10-15 per 15 chapters

## Key Features

✅ **Project-based structure** - Each project isolated  
✅ **Checkpoint & resume** - Stop/start anytime  
✅ **Cost tracking** - Monitor API expenses  
✅ **Detailed logging** - Every LLM request saved  
✅ **Entity tracking** - Characters, locations, items  
✅ **Conflict management** - Track resolution  
✅ **JSON parsing** - Handles Gemini markdown output  

## Common Commands

```bash
# Generate story
python main.py --project-id story_001 --batches 3

# Resume stopped project
python main.py --project-id story_001 --batches 3

# Use specific motif
python main.py --project-id story_002 --motif-id motif_001

# Test JSON parsing
python test_json_parsing.py
```

## File Structure

```
projects/{project_id}/
├── outputs/
│   ├── chapters/       # Generated chapters
│   ├── outlines/       # Chapter outlines
│   ├── entities/       # Character/location database
│   ├── events/         # Story events
│   ├── conflicts/      # Tracked conflicts
│   └── summaries/      # Chapter summaries
├── checkpoints/        # Resume points
└── logs/
    ├── StoryGenerator_*.log    # Main log
    └── llm_requests/*.txt      # Detailed LLM logs
```

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| JSON parsing error | Check v1.3.1 fix applied |
| Import error | Use `from src.prompts.*` |
| High costs | Use flash model where possible |
| Checkpoint not working | Verify JSON file is valid |
| Empty entities | Check LLM response in logs |

---

**Full Documentation**: See `ARCHITECTURE.md`  
**Version**: 1.3.1  
**Updated**: 2024-11-07
