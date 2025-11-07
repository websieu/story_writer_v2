"""
Step 3-4: Entity extraction and management
"""
import os
from typing import Dict, Any, List, Optional
from src.prompts.extract_prompt import SYSTEM_ENTITY_EXTRACTOR, SYSTEM_ENTITY_EXTRACTOR_OUTLINE
from src.utils import save_json, load_json, parse_json_from_response


class EntityManager:
    """Extract and manage story entities (characters, locations, items, etc.)."""
    
    def __init__(self, llm_client, checkpoint_manager, logger, config, paths):
        self.llm_client = llm_client
        self.checkpoint = checkpoint_manager
        self.logger = logger
        self.config = config
        self.paths = paths
        self.max_chars = config.get('story', {}).get('max_chars_for_llm', 30000)
        self.entity_file = os.path.join(paths['entities_dir'], 'entities.json')
        self.entities = self._load_entities()
    
    def _load_entities(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load existing entities from file."""
        if os.path.exists(self.entity_file):
            return load_json(self.entity_file)
        return {
            'characters': [],
            'locations': [],
            'items': [],
            'spiritual_herbs': [],
            'beasts': [],
            'techniques': [],
            'factions': [],
            'other': []
        }
    
    def extract_entities_from_outlines(self, outlines: List[Dict[str, Any]], batch_num: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract entities from batch outlines.
        
        Returns dictionary with entity categories.
        """
        step_name = f"entity_extraction_batch_{batch_num}"
        
        # Check checkpoint
        if self.checkpoint.is_step_completed(step_name, batch=batch_num):
            self.logger.info(f"Entities for batch {batch_num} already extracted")
            return self.entities
        
        self.logger.info(f"Extracting entities from batch {batch_num} outlines")
        
        # Create prompt
        prompt = self._create_extraction_prompt(outlines)
        
        system_message = SYSTEM_ENTITY_EXTRACTOR_OUTLINE
        # Call LLM with batch_id
        result = self.llm_client.call(
            prompt=prompt,
            task_name="entity_extraction",
            system_message=system_message,
            batch_id=batch_num
        )
        
        # Parse entities
        new_entities = self._parse_entity_response(result['response'])
        
        # Save entities for this batch (before merging)
        self._save_batch_entities(new_entities, batch_num)
        
        # Merge with existing entities
        self._merge_entities(new_entities)
        
        # Save entities
        self._save_entities()
        
        # Mark as completed
        self.checkpoint.mark_step_completed(
            step_name,
            batch=batch_num,
            metadata={'total_entities': self._count_entities()}
        )
        
        return self.entities
    
    def extract_entities_from_chapter(self, chapter_content: str, chapter_num: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract new entities that appeared in a chapter.
        
        Returns newly discovered entities.
        """
        step_name = f"entity_extraction_chapter_{chapter_num}"
        
        if self.checkpoint.is_step_completed(step_name, chapter=chapter_num):
            self.logger.info(f"Entities for chapter {chapter_num} already extracted")
            return {}
        
        self.logger.info(f"Extracting new entities from chapter {chapter_num}")
        
        # Create prompt
        prompt = self._create_chapter_extraction_prompt(chapter_content, chapter_num)
        
        system_message =  SYSTEM_ENTITY_EXTRACTOR
        
        # Call LLM with chapter_id
        result = self.llm_client.call(
            prompt=prompt,
            task_name="entity_extraction",
            system_message=system_message,
            chapter_id=chapter_num
        )
        
        # Parse new entities
        new_entities = self._parse_entity_response(result['response'])
        
        # Save entities for this chapter (before merging)
        self._save_chapter_entities(new_entities, chapter_num)
        
        # Merge with existing entities
        self._merge_entities(new_entities)
        
        # Save entities
        self._save_entities()
        
        # Mark as completed
        self.checkpoint.mark_step_completed(
            step_name,
            chapter=chapter_num,
            metadata={'new_entities_count': sum(len(v) for v in new_entities.values())}
        )
        
        return new_entities
    
    def get_relevant_entities(self, chapter_outline: Dict[str, Any], 
                             max_entities: int = 20) -> List[Dict[str, Any]]:
        """
        Get entities relevant to a specific chapter outline.
        
        Uses character names, settings, and conflicts to find relevant entities.
        """
        relevant = []
        
        # Get character names from outline
        character_names = [c.get('name', '') for c in chapter_outline.get('characters', [])]
        settings = chapter_outline.get('settings', [])
        
        # Add characters that appear in the chapter
        for char in self.entities.get('characters', []):
            if char.get('name') in character_names:
                relevant.append(char)
        
        # Add locations mentioned in settings
        for loc in self.entities.get('locations', []):
            if any(setting in loc.get('name', '') for setting in settings):
                relevant.append(loc)
        
        # Add other entities associated with characters
        for entity_type in ['items', 'techniques', 'spiritual_herbs', 'beasts', 'factions']:
            for entity in self.entities.get(entity_type, []):
                # Check if entity is associated with any character in the chapter
                associated = entity.get('associated_characters', [])
                if any(name in associated for name in character_names):
                    relevant.append(entity)
        
        return relevant[:max_entities]
    
    def _create_extraction_prompt(self, outlines: List[Dict[str, Any]]) -> str:
        """Create prompt for entity extraction from outlines."""
        outline_text = "\n\n".join([
            f"**Chương {o.get('chapter_number')}:** {o.get('title')}\n{o.get('summary', '')}"
            for o in outlines
        ])
        
        prompt = f"""Hãy trích xuất tất cả các entity từ các outline sau:

{outline_text}

"""
        return prompt
    
    def _create_chapter_extraction_prompt(self, chapter_content: str, chapter_num: int) -> str:
        """Create prompt for extracting new entities from chapter content."""
        # Truncate content if too long
        truncated_content = chapter_content[:self.max_chars] + "..." if len(chapter_content) > self.max_chars else chapter_content
        
        # Get existing entity names for reference
        existing_names = self._get_all_entity_names()
        
        prompt = f"""Hãy trích xuất các entity MỚI xuất hiện trong chương {chapter_num} mà chưa có trong danh sách hiện tại:

**NỘI DUNG CHƯƠNG:**
{truncated_content}

**ENTITY ĐÃ CÓ (không cần trích xuất lại):**
{', '.join(existing_names[:100])}

"""
        
        return prompt
    
    def _parse_entity_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse entity extraction response."""
        try:
            entities = parse_json_from_response(response)
            # If response is a list, convert to dict format
            if isinstance(entities, list):
                # Group entities by type
                # Map from prompt types to storage keys
                type_mapping = {
                    'character': 'characters',
                    'beast': 'beasts',
                    'faction': 'factions',
                    'artifact': 'items',  # artifacts stored as items
                    'location': 'locations',
                    'technique': 'techniques',
                    'elixir': 'spiritual_herbs',  # elixirs stored as spiritual_herbs
                    'other': 'other'
                }
                
                categorized = {
                    'characters': [],
                    'locations': [],
                    'items': [],
                    'spiritual_herbs': [],
                    'beasts': [],
                    'techniques': [],
                    'factions': [],
                    'other': []
                }
                
                for entity in entities:
                    entity_type = entity.get('type', 'other')
                    storage_key = type_mapping.get(entity_type, 'other')
                    categorized[storage_key].append(entity)
                
                return categorized
            return entities
        except Exception as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            self.logger.error(f"Response preview: {response[:500]}")
            return {}
    
    def _merge_entities(self, new_entities: Dict[str, List[Dict[str, Any]]]):
        """Merge new entities with existing ones, updating appear_in_chapters."""
        for category, entities in new_entities.items():
            if category not in self.entities:
                self.entities[category] = []

            # Create index for faster lookup
            existing_index = {e.get('name', '').lower(): i
                            for i, e in enumerate(self.entities[category])}

            for entity in entities:
                entity_name = entity.get('name', '').lower()
                if not entity_name:
                    continue

                if entity_name in existing_index:
                    # Entity exists - merge appear_in_chapters
                    idx = existing_index[entity_name]
                    existing_entity = self.entities[category][idx]

                    # Merge appear_in_chapters
                    existing_chapters = set(existing_entity.get('appear_in_chapters', []))
                    new_chapters = set(entity.get('appear_in_chapters', []))
                    merged_chapters = sorted(list(existing_chapters | new_chapters))

                    if merged_chapters:
                        existing_entity['appear_in_chapters'] = merged_chapters
                        self.logger.info(f"Updated entity: {entity.get('name')} ({category}) - chapters: {merged_chapters}")

                    # Update description if new one is longer/more detailed
                    new_desc = entity.get('description', '')
                    old_desc = existing_entity.get('description', '')
                    if len(new_desc) > len(old_desc):
                        existing_entity['description'] = new_desc
                else:
                    # New entity - add it
                    self.entities[category].append(entity)
                    self.logger.info(f"Added new entity: {entity.get('name')} ({category}) - chapters: {entity.get('appear_in_chapters', [])}")
    
    def _save_entities(self):
        """Save entities to file."""
        save_json(self.entities, self.entity_file)
        self.logger.info(f"Saved entities to {self.entity_file}")
    
    def _save_batch_entities(self, entities: Dict[str, List[Dict[str, Any]]], batch_num: int):
        """Save entities extracted from a specific batch."""
        batch_file = os.path.join(self.paths['entities_dir'], f'batch_{batch_num:03d}_entities.json')
        
        # Add metadata
        entity_data = {
            'batch_number': batch_num,
            'extraction_type': 'from_outlines',
            'total_count': sum(len(v) for v in entities.values()),
            'entities': entities
        }
        
        save_json(entity_data, batch_file)
        self.logger.info(f"Saved batch {batch_num} entities to {batch_file}")
    
    def _save_chapter_entities(self, entities: Dict[str, List[Dict[str, Any]]], chapter_num: int):
        """Save entities extracted from a specific chapter."""
        chapter_file = os.path.join(self.paths['entities_dir'], f'chapter_{chapter_num:03d}_entities.json')
        
        # Add metadata
        entity_data = {
            'chapter_number': chapter_num,
            'extraction_type': 'from_chapter_content',
            'total_count': sum(len(v) for v in entities.values()),
            'entities': entities
        }
        
        save_json(entity_data, chapter_file)
        self.logger.info(f"Saved chapter {chapter_num} entities to {chapter_file}")
    
    def _count_entities(self) -> int:
        """Count total number of entities."""
        return sum(len(entities) for entities in self.entities.values())
    
    def _get_all_entity_names(self) -> List[str]:
        """Get all entity names across all categories."""
        names = []
        for entities in self.entities.values():
            names.extend([e.get('name', '') for e in entities if e.get('name')])
        return names
    
    def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find an entity by name across all categories."""
        name_lower = name.lower()
        for category, entities in self.entities.items():
            for entity in entities:
                if entity.get('name', '').lower() == name_lower:
                    return {**entity, 'category': category}
        return None
