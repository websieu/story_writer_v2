#!/usr/bin/env python3
"""
Test script to verify JSON parsing fix.
Run this to ensure all JSON parsers work correctly with Gemini responses.
"""

import sys
from src.utils import parse_json_from_response


def test_markdown_wrapped_array():
    """Test parsing JSON array wrapped in markdown code blocks."""
    response = '''```json
[
  {"name": "Test Character", "type": "character"},
  {"name": "Test Location", "type": "location"}
]
```'''
    
    try:
        result = parse_json_from_response(response)
        assert isinstance(result, list), "Expected list"
        assert len(result) == 2, "Expected 2 items"
        print("✓ Markdown wrapped array: PASSED")
        return True
    except Exception as e:
        print(f"✗ Markdown wrapped array: FAILED - {e}")
        return False


def test_markdown_wrapped_object():
    """Test parsing JSON object wrapped in markdown code blocks."""
    response = '''```json
{
  "chapters": [
    {"number": 1, "title": "Test Chapter"}
  ]
}
```'''
    
    try:
        result = parse_json_from_response(response)
        assert isinstance(result, dict), "Expected dict"
        assert 'chapters' in result, "Expected 'chapters' key"
        print("✓ Markdown wrapped object: PASSED")
        return True
    except Exception as e:
        print(f"✗ Markdown wrapped object: FAILED - {e}")
        return False


def test_plain_json_array():
    """Test parsing plain JSON array without markdown."""
    response = '[{"name": "Test"}, {"name": "Test2"}]'
    
    try:
        result = parse_json_from_response(response)
        assert isinstance(result, list), "Expected list"
        assert len(result) == 2, "Expected 2 items"
        print("✓ Plain JSON array: PASSED")
        return True
    except Exception as e:
        print(f"✗ Plain JSON array: FAILED - {e}")
        return False


def test_plain_json_object():
    """Test parsing plain JSON object without markdown."""
    response = '{"key": "value", "number": 123}'
    
    try:
        result = parse_json_from_response(response)
        assert isinstance(result, dict), "Expected dict"
        assert result['key'] == 'value', "Expected correct value"
        print("✓ Plain JSON object: PASSED")
        return True
    except Exception as e:
        print(f"✗ Plain JSON object: FAILED - {e}")
        return False


def test_type_mapping():
    """Test entity type mapping."""
    entities = [
        {"name": "Trần Phàm", "type": "character"},
        {"name": "Ngọc Bội", "type": "artifact"},
        {"name": "Thái Cực Huyền Công", "type": "technique"},
        {"name": "Linh Đan", "type": "elixir"},
    ]
    
    type_mapping = {
        'character': 'characters',
        'beast': 'beasts',
        'faction': 'factions',
        'artifact': 'items',
        'location': 'locations',
        'technique': 'techniques',
        'elixir': 'spiritual_herbs',
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
    
    try:
        for entity in entities:
            entity_type = entity.get('type', 'other')
            storage_key = type_mapping.get(entity_type, 'other')
            categorized[storage_key].append(entity)
        
        assert len(categorized['characters']) == 1, "Expected 1 character"
        assert len(categorized['items']) == 1, "Expected 1 item (artifact)"
        assert len(categorized['techniques']) == 1, "Expected 1 technique"
        assert len(categorized['spiritual_herbs']) == 1, "Expected 1 spiritual_herb (elixir)"
        
        print("✓ Type mapping: PASSED")
        return True
    except Exception as e:
        print(f"✗ Type mapping: FAILED - {e}")
        return False


def test_real_gemini_response():
    """Test with actual Gemini response format."""
    response = '''```json
[
  {
    "name": "Trần Phàm",
    "type": "character",
    "description": "giới tính: nam; ngoại hình: unknow; thuộc: unknow; tiến trình: (c1) sinh ra trong gia đình nghèo khó",
    "appear_in_chapters": [1, 2, 3]
  },
  {
    "name": "Lạc Diệp Trấn",
    "type": "location",
    "description": "mô tả: làng nhỏ nơi Trần Phàm sinh ra",
    "appear_in_chapters": [1]
  }
]
```'''
    
    try:
        result = parse_json_from_response(response)
        assert isinstance(result, list), "Expected list"
        assert len(result) == 2, "Expected 2 entities"
        assert result[0]['name'] == 'Trần Phàm', "Expected correct character name"
        assert result[0]['type'] == 'character', "Expected correct type"
        assert isinstance(result[0]['appear_in_chapters'], list), "Expected chapters list"
        
        print("✓ Real Gemini response: PASSED")
        return True
    except Exception as e:
        print(f"✗ Real Gemini response: FAILED - {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("JSON Parsing Fix - Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        test_markdown_wrapped_array,
        test_markdown_wrapped_object,
        test_plain_json_array,
        test_plain_json_object,
        test_type_mapping,
        test_real_gemini_response,
    ]
    
    results = [test() for test in tests]
    
    print()
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All tests passed! ({passed}/{total})")
        print("=" * 60)
        return 0
    else:
        print(f"❌ Some tests failed! ({passed}/{total})")
        print("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
