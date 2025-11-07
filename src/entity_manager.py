"""
Step 3-4: Entity extraction and management
"""
import os
from typing import Dict, Any, List, Optional
from src.utils import save_json, load_json


class EntityManager:
    """Extract and manage story entities (characters, locations, items, etc.)."""
    
    def __init__(self, llm_client, checkpoint_manager, logger, config, paths):
        self.llm_client = llm_client
        self.checkpoint = checkpoint_manager
        self.logger = logger
        self.config = config
        self.paths = paths
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
        
        system_message = """Bạn là một chuyên gia phân tích văn bản, có khả năng trích xuất và phân loại các entity 
        từ outline truyện. Hãy trích xuất chi tiết và đầy đủ nhất."""
        
        # Call LLM with batch_id
        result = self.llm_client.call(
            prompt=prompt,
            task_name="entity_extraction",
            system_message=system_message,
            batch_id=batch_num
        )
        
        # Parse entities
        new_entities = self._parse_entity_response(result['response'])
        
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
        
        system_message = """Bạn là chuyên gia phân tích, hãy trích xuất các entity mới xuất hiện trong chương này 
        mà chưa có trong danh sách entity hiện tại."""
        
        # Call LLM with chapter_id
        result = self.llm_client.call(
            prompt=prompt,
            task_name="entity_extraction",
            system_message=system_message,
            chapter_id=chapter_num
        )
        
        # Parse new entities
        new_entities = self._parse_entity_response(result['response'])
        
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

**YÊU CẦU:**

Trích xuất và phân loại các entity theo các nhóm sau:

1. **Nhân vật (characters)**: Tất cả nhân vật xuất hiện
   - Tên, mô tả ngoại hình, tính cách, năng lực, cảnh giới tu luyện, mục tiêu
   
2. **Địa điểm (locations)**: Các địa điểm, thành phố, tông môn, hang động, v.v.
   - Tên, mô tả chi tiết, đặc điểm nổi bật
   
3. **Vật phẩm (items)**: Vũ khí, bảo bối, pháp bảo
   - Tên, loại, năng lực, nguồn gốc
   
4. **Linh dược (spiritual_herbs)**: Dược thảo, linh đan
   - Tên, công dụng, độ hiếm
   
5. **Yêu thú (beasts)**: Quái thú, linh thú
   - Tên, loại, năng lực, cảnh giới
   
6. **Công pháp (techniques)**: Võ công, phép thuật, kỹ năng
   - Tên, loại, mức độ, hiệu quả
   
7. **Thế lực (factions)**: Tông môn, gia tộc, bang hội
   - Tên, quy mô, ảnh hưởng, lãnh đạo

**ĐỊNH DẠNG OUTPUT (JSON):**

```json
{{
  "characters": [
    {{
      "name": "Tên nhân vật",
      "description": "Mô tả tổng quan",
      "appearance": "Ngoại hình",
      "personality": "Tính cách",
      "cultivation_level": "Cảnh giới tu luyện",
      "abilities": ["Năng lực 1", "Năng lực 2"],
      "background": "Lai lịch",
      "goals": "Mục tiêu",
      "relationships": [{{"character": "Tên nhân vật khác", "relation": "Quan hệ"}}]
    }}
  ],
  "locations": [
    {{
      "name": "Tên địa điểm",
      "type": "thành phố/tông môn/hang động/etc",
      "description": "Mô tả chi tiết",
      "features": ["Đặc điểm 1", "Đặc điểm 2"]
    }}
  ],
  "items": [
    {{
      "name": "Tên vật phẩm",
      "type": "vũ khí/pháp bảo/etc",
      "description": "Mô tả",
      "abilities": ["Năng lực"],
      "grade": "Phẩm cấp",
      "owner": "Chủ nhân hiện tại"
    }}
  ],
  "spiritual_herbs": [
    {{
      "name": "Tên linh dược",
      "type": "linh thảo/linh đan/etc",
      "description": "Mô tả",
      "effects": ["Công dụng"],
      "rarity": "Độ hiếm"
    }}
  ],
  "beasts": [
    {{
      "name": "Tên yêu thú",
      "type": "Loại",
      "description": "Mô tả",
      "cultivation_level": "Cảnh giới",
      "abilities": ["Năng lực"]
    }}
  ],
  "techniques": [
    {{
      "name": "Tên công pháp",
      "type": "võ công/phép thuật/etc",
      "description": "Mô tả",
      "grade": "Cấp độ",
      "effects": ["Hiệu quả"],
      "requirements": "Yêu cầu tu luyện"
    }}
  ],
  "factions": [
    {{
      "name": "Tên thế lực",
      "type": "tông môn/gia tộc/bang hội/etc",
      "description": "Mô tả",
      "leader": "Lãnh đạo",
      "members": ["Thành viên nổi bật"],
      "influence": "Mức độ ảnh hưởng",
      "territory": "Lãnh địa"
    }}
  ]
}}
```

Hãy trích xuất theo đúng định dạng JSON trên."""
        
        return prompt
    
    def _create_chapter_extraction_prompt(self, chapter_content: str, chapter_num: int) -> str:
        """Create prompt for extracting new entities from chapter content."""
        # Truncate content if too long
        max_chars = 10000
        truncated_content = chapter_content[:max_chars] + "..." if len(chapter_content) > max_chars else chapter_content
        
        # Get existing entity names for reference
        existing_names = self._get_all_entity_names()
        
        prompt = f"""Hãy trích xuất các entity MỚI xuất hiện trong chương {chapter_num} mà chưa có trong danh sách hiện tại:

**NỘI DUNG CHƯƠNG:**
{truncated_content}

**ENTITY ĐÃ CÓ (không cần trích xuất lại):**
{', '.join(existing_names[:100])}

**YÊU CẦU:**
- Chỉ trích xuất entity MỚI, không có trong danh sách đã có
- Mô tả chi tiết cho mỗi entity mới
- Phân loại đúng category

**ĐỊNH DẠNG OUTPUT:** Giống như prompt trích xuất từ outline, trả về JSON với các category."""
        
        return prompt
    
    def _parse_entity_response(self, response: str) -> Dict[str, List[Dict[str, Any]]]:
        """Parse entity extraction response."""
        import json
        import re
        
        # Extract JSON
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                self.logger.warning("Could not extract JSON from entity response")
                return {}
        
        try:
            entities = json.loads(json_str)
            return entities
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            return {}
    
    def _merge_entities(self, new_entities: Dict[str, List[Dict[str, Any]]]):
        """Merge new entities with existing ones, avoiding duplicates."""
        for category, entities in new_entities.items():
            if category not in self.entities:
                self.entities[category] = []
            
            existing_names = {e.get('name', '').lower() for e in self.entities[category]}
            
            for entity in entities:
                entity_name = entity.get('name', '').lower()
                if entity_name and entity_name not in existing_names:
                    self.entities[category].append(entity)
                    existing_names.add(entity_name)
                    self.logger.info(f"Added new entity: {entity.get('name')} ({category})")
    
    def _save_entities(self):
        """Save entities to file."""
        save_json(self.entities, self.entity_file)
        self.logger.info(f"Saved entities to {self.entity_file}")
    
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
