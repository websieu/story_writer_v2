"""
Test script to verify foreshadowing section appears in chapter writing prompt.
"""
import sys
import os
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_method_exists():
    """Test that _format_foreshadowing method exists in the source code"""
    print("=" * 80)
    print("TEST 1: Method existence check")
    print("=" * 80)
    
    # Read the chapter_writer.py source
    with open(os.path.join(os.path.dirname(__file__), 'src', 'chapter_writer.py'), 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if method is defined
    if "def _format_foreshadowing(" in content:
        print("✅ PASSED: _format_foreshadowing() method exists")
        
        # Extract the method to verify its signature
        method_match = re.search(r'def _format_foreshadowing\(self, ([^)]+)\)', content)
        if method_match:
            params = method_match.group(1)
            print(f"   Method signature: _format_foreshadowing(self, {params})")
            
            if "foreshadowing" in params:
                print("✅ PASSED: Method accepts 'foreshadowing' parameter")
            else:
                print("❌ FAILED: Method doesn't accept expected parameter")
        
        # Check docstring
        if '"""Format foreshadowing information from outline."""' in content:
            print("✅ PASSED: Method has descriptive docstring")
    else:
        print("❌ FAILED: _format_foreshadowing() method does NOT exist")
    
    print()

def test_method_implementation():
    """Test the implementation details of _format_foreshadowing"""
    print("=" * 80)
    print("TEST 2: Method implementation check")
    print("=" * 80)
    
    with open(os.path.join(os.path.dirname(__file__), 'src', 'chapter_writer.py'), 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract the method body
    method_start = content.find("def _format_foreshadowing(")
    if method_start == -1:
        print("❌ FAILED: Cannot find method")
        return
    
    # Find the next method definition to get the method body
    next_method = content.find("\n    def ", method_start + 1)
    method_body = content[method_start:next_method]
    
    # Check key implementation details
    checks = [
        ("reveal_chapter", "Extracts reveal_chapter from foreshadowing data"),
        ("importance", "Extracts importance score"),
        ("detail", "Extracts foreshadowing detail text"),
        ("(tiết lộ c{", "Formats reveal chapter marker"),
        ("quan trọng:", "Formats importance score"),
        ("Không có", "Handles empty foreshadowing case"),
    ]
    
    print("Checking implementation details:")
    all_passed = True
    for check_str, description in checks:
        if check_str in method_body:
            print(f"  ✅ {description}")
        else:
            print(f"  ❌ {description} - NOT FOUND")
            all_passed = False
    
    if all_passed:
        print("\n✅ ALL IMPLEMENTATION CHECKS PASSED")
    else:
        print("\n⚠️  SOME IMPLEMENTATION CHECKS FAILED")
    
    print()

def test_prompt_structure():
    """Test that foreshadowing appears in correct position in prompt template"""
    print("=" * 80)
    print("TEST 3: Foreshadowing position in prompt structure")
    print("=" * 80)
    
    # Read the chapter_writer.py source to check prompt structure
    with open(os.path.join(os.path.dirname(__file__), 'src', 'chapter_writer.py'), 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if foreshadowing section is defined in the prompt
    if "Foreshadowing (Cài cắm):" in content:
        print("✅ PASSED: Foreshadowing section header found in prompt template")
    else:
        print("❌ FAILED: Foreshadowing section header NOT found in prompt template")
    
    # Check if it calls _format_foreshadowing
    if "_format_foreshadowing(chapter_outline.get('foreshadowing', []))" in content:
        print("✅ PASSED: _format_foreshadowing() method called correctly with chapter_outline.get('foreshadowing', [])")
    else:
        print("❌ FAILED: _format_foreshadowing() method NOT called or incorrect syntax")
    
    # Find the prompt template section
    prompt_start = content.find('prompt = f"""Hãy viết nội dung')
    if prompt_start == -1:
        print("⚠️  WARNING: Cannot find prompt template")
        return
    
    # Extract a reasonable section of the prompt
    prompt_section = content[prompt_start:prompt_start + 2000]
    
    # Check the order: should be after conflicts and before settings
    conflicts_pos = prompt_section.find("Mâu thuẫn:")
    foreshadowing_pos = prompt_section.find("Foreshadowing (Cài cắm):")
    settings_pos = prompt_section.find("Địa điểm:")
    
    if conflicts_pos != -1 and foreshadowing_pos != -1 and settings_pos != -1:
        if conflicts_pos < foreshadowing_pos < settings_pos:
            print("✅ PASSED: Foreshadowing positioned correctly (Conflicts → Foreshadowing → Settings)")
        else:
            print(f"❌ FAILED: Foreshadowing NOT in expected position")
            print(f"   Positions: Conflicts={conflicts_pos}, Foreshadowing={foreshadowing_pos}, Settings={settings_pos}")
    else:
        print("⚠️  WARNING: Cannot determine relative positions")
    
    # Extract and display the relevant prompt section
    print("\n" + "-" * 80)
    print("PROMPT STRUCTURE PREVIEW:")
    print("-" * 80)
    
    outline_section_match = re.search(
        r'Mâu thuẫn:.*?Địa điểm:', 
        prompt_section, 
        re.DOTALL
    )
    
    if outline_section_match:
        section = outline_section_match.group(0)
        # Clean up the f-string formatting for display
        section = section.replace('{self._format_conflicts(', '[CONFLICTS]')
        section = section.replace('{self._format_foreshadowing(', '[FORESHADOWING]')
        section = re.sub(r'\{[^}]+\}', '[...]', section)
        print(section)
    else:
        print("Could not extract section")
    
    print()

def test_integration_with_outline():
    """Test that the implementation matches the outline JSON structure"""
    print("=" * 80)
    print("TEST 4: Integration with outline.json structure")
    print("=" * 80)
    
    # Check if there's an example outline file
    outline_path = "/root/test_writer/projects/story_001/outputs/outlines/batch_1_outline.json"
    
    if os.path.exists(outline_path):
        print(f"✅ Found outline file: {outline_path}")
        
        import json
        with open(outline_path, 'r', encoding='utf-8') as f:
            outline_data = json.load(f)
        
        # Check if chapters have foreshadowing data
        if 'chapters' in outline_data:
            chapters_with_foreshadowing = 0
            total_foreshadowing_items = 0
            
            for i, chapter in enumerate(outline_data['chapters'], 1):
                if 'foreshadowing' in chapter and chapter['foreshadowing']:
                    chapters_with_foreshadowing += 1
                    total_foreshadowing_items += len(chapter['foreshadowing'])
                    
                    if i == 1:  # Show example from first chapter
                        print(f"\n  Example from Chapter {i}:")
                        for fs in chapter['foreshadowing'][:2]:  # Show first 2
                            print(f"    - Detail: {fs.get('detail', '')[:80]}...")
                            print(f"      Reveal: Chapter {fs.get('reveal_chapter')}, Importance: {fs.get('importance')}")
            
            print(f"\n✅ Found {chapters_with_foreshadowing} chapters with foreshadowing")
            print(f"✅ Total {total_foreshadowing_items} foreshadowing items across all chapters")
            
            # Verify structure matches what our method expects
            if chapters_with_foreshadowing > 0:
                first_fs = None
                for chapter in outline_data['chapters']:
                    if chapter.get('foreshadowing'):
                        first_fs = chapter['foreshadowing'][0]
                        break
                
                if first_fs:
                    required_keys = ['detail', 'reveal_chapter', 'importance']
                    has_all_keys = all(key in first_fs for key in required_keys)
                    
                    if has_all_keys:
                        print("✅ PASSED: Outline foreshadowing structure matches expected format")
                    else:
                        print("⚠️  WARNING: Outline structure may not match expected format")
                        print(f"   Expected keys: {required_keys}")
                        print(f"   Found keys: {list(first_fs.keys())}")
        else:
            print("⚠️  WARNING: No chapters found in outline")
    else:
        print(f"⚠️  Outline file not found at: {outline_path}")
        print("   (This is OK if you haven't generated a story yet)")
    
    print()

def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("FORESHADOWING SECTION TEST SUITE")
    print("=" * 80)
    print()
    
    test_method_exists()
    test_method_implementation()
    test_prompt_structure()
    test_integration_with_outline()
    
    print("=" * 80)
    print("TEST SUITE COMPLETED")
    print("=" * 80)
    print("\nSUMMARY:")
    print("- ✅ = Test passed")
    print("- ❌ = Test failed")
    print("- ⚠️  = Warning (non-critical)")

if __name__ == "__main__":
    main()
