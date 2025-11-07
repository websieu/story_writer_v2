# Module Updates for Project Structure

## Changes Needed

### All modules need to:
1. Accept `paths` parameter in `__init__`
2. Use `paths` dict instead of `config['paths']`
3. Pass `batch_id` and/or `chapter_id` to `llm_client.call()`

## Module-by-Module Updates

### ✅ outline_generator.py
- [x] Add `paths` to __init__
- [x] Pass `batch_id` to llm_client.call() in generate_initial_outline
- [ ] Pass `batch_id` to llm_client.call() in generate_continuation_outline
- [ ] Update `_save_outline` and `_load_outline` to use `self.paths['outlines_dir']`

### entity_manager.py
- [ ] Add `paths` to __init__
- [ ] Pass `batch_id` to llm_client.call() in extract_entities_from_outlines
- [ ] Pass `chapter_id` to llm_client.call() in extract_entities_from_chapter  
- [ ] Update paths to use `self.paths['entities_dir']`

### chapter_writer.py
- [ ] Add `paths` to __init__
- [ ] Pass `chapter_id` to llm_client.call() in write_chapter
- [ ] Update paths to use `self.paths['chapters_dir']`

### post_processor.py
- [ ] Add `paths` to __init__
- [ ] Pass `chapter_id` to all llm_client.call() methods
- [ ] Update paths to use `self.paths['events_dir']`, `conflicts_dir`, `summaries_dir`

### checkpoint.py
- [ ] No path changes needed (already receives checkpoint_dir in __init__)

## Path Mappings

Old → New:
- `config['paths']['output_dir']` → `paths['outputs_dir']`
- `config['paths']['checkpoint_dir']` → `paths['checkpoints_dir']`
- `output/chapters/` → `paths['chapters_dir']`
- `output/outlines/` → `paths['outlines_dir']`
- `output/entities/` → `paths['entities_dir']`
- `output/events/` → `paths['events_dir']`
- `output/conflicts/` → `paths['conflicts_dir']`
- `output/summaries/` → `paths['summaries_dir']`
