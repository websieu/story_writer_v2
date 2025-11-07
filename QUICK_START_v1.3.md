# Quick Start with New Project Structure (v1.3.0)

## Starting a New Project

```bash
# Generate a story with project ID
python main.py --project-id my_first_story --batches 2

# All data will be in:
# projects/my_first_story/
#   ├── outputs/
#   │   ├── chapters/
#   │   ├── outlines/
#   │   ├── entities/
#   │   ├── events/
#   │   ├── conflicts/
#   │   └── summaries/
#   ├── checkpoints/
#   └── logs/
#       ├── StoryGenerator_*.log
#       └── llm_requests/
#           ├── outline_generation_batch001_*.json
#           ├── chapter_writing_batch001_chapter001_*.json
#           ├── event_extraction_chapter001_*.json
#           └── ...
```

## Viewing LLM Request Logs

### Check a specific request
```bash
# View outline generation log for batch 1
cat projects/my_first_story/logs/llm_requests/outline_generation_batch001_*.json | jq .

# Example output:
{
  "timestamp": "2025-11-07T15:20:30.123456",
  "project_id": "my_first_story",
  "task_name": "outline_generation",
  "batch_id": 1,
  "chapter_id": null,
  "model": "gemini-2.5-flash",
  "prompts": {
    "system": "Bạn là một tác giả truyện tu tiên chuyên nghiệp...",
    "user": "Dựa trên motif sau, hãy tạo outline chi tiết cho 5 chương đầu tiên:..."
  },
  "response": "{\"batch\": 1, \"chapters\": [...]}",
  "error": null,
  "metrics": {
    "tokens": {
      "input": 1200,
      "output": 2500,
      "total": 3700
    },
    "cost": 0.015,
    "duration": 8.5
  }
}
```

### Find all chapter writing logs
```bash
cd projects/my_first_story/logs/llm_requests/
ls -la chapter_writing_*.json
```

### Find error logs
```bash
cd projects/my_first_story/logs/llm_requests/
grep -l '"error":' *.json
```

### Analyze costs by task
```bash
# Get all event extraction costs
cd projects/my_first_story/logs/llm_requests/
for f in event_extraction_*.json; do
  echo "$f: $(jq '.metrics.cost' $f)"
done

# Sum total costs
jq -s 'map(.metrics.cost) | add' *.json
```

## Multiple Projects

```bash
# Project 1: Cultivation story
python main.py --project-id cultivation_001 --batches 3 --genre "tu_tien"

# Project 2: Modern fantasy
python main.py --project-id modern_fantasy_001 --batches 2 --genre "huyen_huyen"

# Projects are completely isolated:
# projects/
#   ├── cultivation_001/
#   │   ├── outputs/
#   │   ├── checkpoints/
#   │   └── logs/
#   └── modern_fantasy_001/
#       ├── outputs/
#       ├── checkpoints/
#       └── logs/
```

## Debugging Failed Requests

### Scenario: Chapter writing failed

1. **Find the error log:**
```bash
cd projects/my_story/logs/llm_requests/
grep -l '"error"' chapter_writing_*.json
# Output: chapter_writing_batch001_chapter005_20251107_153045_789012.json
```

2. **Examine the error:**
```bash
cat chapter_writing_batch001_chapter005_20251107_153045_789012.json | jq '.'
```

3. **View the exact prompts:**
```bash
cat chapter_writing_batch001_chapter005_20251107_153045_789012.json | jq '.prompts'
```

4. **Check what was sent:**
```json
{
  "prompts": {
    "system": "Bạn là một tác giả truyện tu tiên tài năng...",
    "user": "**CHƯƠNG 5: [Title]**\n\n**OUTLINE:**\n..."
  },
  "error": "HTTP 429: Rate limit exceeded"
}
```

5. **Resume generation:** System automatically retries with different key

## Cost Analysis

### Total cost for project
```bash
cd projects/my_story/logs/llm_requests/
jq -s 'map(.metrics.cost) | add' *.json
```

### Cost by task type
```bash
# Chapter writing costs
jq -s 'map(select(.task_name == "chapter_writing") | .metrics.cost) | add' *.json

# Outline generation costs
jq -s 'map(select(.task_name == "outline_generation") | .metrics.cost) | add' *.json
```

### Tokens used per chapter
```bash
for i in {1..5}; do
  echo "Chapter $i:"
  jq -s "map(select(.chapter_id == $i) | .metrics.tokens.total) | add" *.json
done
```

## Tips & Best Practices

### 1. Regular Backups
```bash
# Backup entire project
tar -czf my_story_backup_$(date +%Y%m%d).tar.gz projects/my_story/
```

### 2. Clean Old Logs
```bash
# LLM request logs can grow large
# Archive logs older than 7 days
find projects/*/logs/llm_requests/ -name "*.json" -mtime +7 -exec gzip {} \;
```

### 3. Compare Prompts Across Batches
```bash
# Compare outline generation prompts
diff <(jq '.prompts.user' outline_generation_batch001_*.json) \
     <(jq '.prompts.user' outline_generation_batch002_*.json)
```

### 4. Monitor Costs in Real-Time
```bash
# Watch total cost during generation
watch -n 5 'cd projects/my_story/logs/llm_requests && jq -s "map(.metrics.cost) | add" *.json'
```

### 5. Export Request Data
```bash
# Create CSV of all requests
cd projects/my_story/logs/llm_requests/
echo "timestamp,task,batch,chapter,model,tokens,cost,duration" > requests.csv
for f in *.json; do
  jq -r '[.timestamp, .task_name, .batch_id // "null", .chapter_id // "null", .model, .metrics.tokens.total, .metrics.cost, .metrics.duration] | @csv' $f >> requests.csv
done
```

## Troubleshooting

### No LLM logs created
**Issue:** `logs/llm_requests/` folder empty

**Solution:**
```bash
# Check main log for errors
tail -f projects/my_story/logs/StoryGenerator_*.log

# Verify permissions
ls -la projects/my_story/logs/llm_requests/
```

### Can't find project folder
**Issue:** `projects/my_story/` doesn't exist

**Solution:**
```bash
# Verify you used correct project-id
ls -la projects/

# Check if using old structure
ls -la output/  # Old location
```

### Old data in wrong location
**Issue:** Data in `output/`, `checkpoints/`, `logs/`

**Solution:** Migrate to new structure
```bash
# Create project folder
mkdir -p projects/old_story/

# Move data
mv output projects/old_story/outputs
mv checkpoints projects/old_story/checkpoints
mv logs projects/old_story/logs

# Create llm_requests folder
mkdir -p projects/old_story/logs/llm_requests
```

## Advanced Usage

### Custom Analysis Script
```python
#!/usr/bin/env python3
import json
import glob
from pathlib import Path

project_id = "my_story"
logs_dir = f"projects/{project_id}/logs/llm_requests/"

# Load all logs
logs = []
for file in glob.glob(f"{logs_dir}/*.json"):
    with open(file) as f:
        logs.append(json.load(f))

# Analyze
total_cost = sum(log['metrics']['cost'] for log in logs if log.get('metrics'))
total_tokens = sum(log['metrics']['tokens']['total'] for log in logs if log.get('metrics'))
avg_duration = sum(log['metrics']['duration'] for log in logs if log.get('metrics')) / len(logs)

print(f"Project: {project_id}")
print(f"Total API calls: {len(logs)}")
print(f"Total cost: ${total_cost:.2f}")
print(f"Total tokens: {total_tokens:,}")
print(f"Average duration: {avg_duration:.2f}s")

# By task
from collections import defaultdict
by_task = defaultdict(lambda: {'count': 0, 'cost': 0, 'tokens': 0})
for log in logs:
    task = log['task_name']
    if log.get('metrics'):
        by_task[task]['count'] += 1
        by_task[task]['cost'] += log['metrics']['cost']
        by_task[task]['tokens'] += log['metrics']['tokens']['total']

print("\nBy Task:")
for task, stats in sorted(by_task.items()):
    print(f"  {task}:")
    print(f"    Calls: {stats['count']}")
    print(f"    Cost: ${stats['cost']:.2f}")
    print(f"    Tokens: {stats['tokens']:,}")
```

### Run analysis
```bash
chmod +x analyze_project.py
./analyze_project.py
```

## See Also

- `PROJECT_STRUCTURE_UPDATE.md` - Complete refactoring documentation
- `CHANGELOG.md` - Version history
- `README.md` - Full system documentation
