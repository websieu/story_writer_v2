"""
Test script to verify next chapter summary appears in prompt
"""
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils import load_config, get_project_paths, load_json
from src.post_processor import PostChapterProcessor
from src.entity_manager import EntityManager
from src.chapter_writer import ChapterWriter
from src.checkpoint import CheckpointManager
from src.utils import Logger


def test_next_chapter_in_prompt():
    """Test that next chapter summary appears in writing prompt"""
    config = load_config("config/config.yaml")
    project_id = "story_001"
    paths = get_project_paths(project_id, config)
    
    # Initialize logger and checkpoint
    logger = Logger("TestNextChapter", project_id, config)
    checkpoint = CheckpointManager(paths['checkpoints_dir'], project_id)
    
    # Initialize post processor
    post_processor = PostChapterProcessor(
        llm_client=None,
        checkpoint_manager=checkpoint,
        logger=logger,
        config=config,
        paths=paths
    )
    
    # Initialize entity manager
    entity_manager = EntityManager(
        llm_client=None,
        checkpoint_manager=checkpoint,
        logger=logger,
        config=config,
        paths=paths
    )
    
    # Initialize chapter writer
    chapter_writer = ChapterWriter(
        llm_client=None,
        checkpoint_manager=checkpoint,
        logger=logger,
        config=config,
        entity_manager=entity_manager,
        paths=paths,
        post_processor=post_processor
    )
    
    print("=" * 80)
    print("TESTING NEXT CHAPTER SUMMARY IN PROMPT")
    print("=" * 80)
    
    # Load outline for batch 1
    outline_file = os.path.join(paths['outlines_dir'], 'batch_1_outline.json')
    
    if not os.path.exists(outline_file):
        print(f"\nERROR: Outline file not found: {outline_file}")
        print("Please generate a batch first!")
        return
    
    outline_data = load_json(outline_file)
    chapters = outline_data.get('chapters', [])
    
    if len(chapters) < 2:
        print("ERROR: Need at least 2 chapters to test")
        return
    
    # Test with chapter 2 (should show chapter 3 as next)
    chapter_2 = chapters[1]
    chapter_3 = chapters[2]
    
    print(f"\nCurrent Chapter: {chapter_2.get('chapter_number')} - {chapter_2.get('title')}")
    print(f"Next Chapter: {chapter_3.get('chapter_number')} - {chapter_3.get('title')}")
    
    # Prepare context
    context = {
        'motif': {
            'title': 'Test Motif',
            'description': 'Thiên tài tu tiên bị hại mất tu vi',
            'themes': ['phục hận', 'tái sinh']
        },
        'related_entities': entity_manager.get_relevant_entities(chapter_2),
        'recent_summaries': ['Summary 1', 'Summary 2'],
        'super_summary': 'Test super summary',
        'previous_chapter_end': 'Test previous chapter end...',
        'next_chapter_outline': chapter_3  # <-- This is the key addition
    }
    
    # Create the prompt
    prompt = chapter_writer._create_writing_prompt(chapter_2, context)
    
    print("\n" + "=" * 80)
    print("CHECKING FOR NEXT CHAPTER SECTION IN PROMPT")
    print("=" * 80)
    
    # Search for next chapter section
    if '**Chương tiếp theo (Preview):**' in prompt:
        print("\n✅ SUCCESS: Next chapter section found in prompt!")
        
        # Extract and show the section
        lines = prompt.split('\n')
        in_next_section = False
        next_section_lines = []
        
        for line in lines:
            if 'Chương tiếp theo (Preview)' in line:
                in_next_section = True
            elif in_next_section:
                if line.startswith('**') or line.startswith('---'):
                    break
                next_section_lines.append(line)
        
        if next_section_lines:
            print("\n**Chương tiếp theo (Preview):**")
            for line in next_section_lines:
                print(line)
    else:
        print("\n❌ FAILED: Next chapter section NOT found in prompt!")
        print("\nSearching for any mention of chapter 3...")
        if str(chapter_3.get('chapter_number')) in prompt or chapter_3.get('title') in prompt:
            print(f"Found some reference to chapter 3, but not in expected format")
        else:
            print("No reference to chapter 3 found at all!")
    
    # Also check position of next chapter section
    print("\n" + "=" * 80)
    print("SECTION ORDER IN PROMPT")
    print("=" * 80)
    
    sections = [
        'OUTLINE CHƯƠNG',
        'Bối cảnh:',
        'Tóm tắt toàn bộ:',
        'Kết chương trước:',
        'Chương tiếp theo (Preview):',
        'Entity liên quan:',
        'Các sự kiện liên quan từ các entity:'
    ]
    
    for section in sections:
        if section in prompt:
            pos = prompt.find(section)
            print(f"✅ {section:<50} at position {pos}")
        else:
            print(f"❌ {section:<50} NOT FOUND")
    
    # Save full prompt to file
    output_file = "/root/test_writer/test_next_chapter_prompt.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"\n" + "=" * 80)
    print(f"Full prompt saved to: {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    test_next_chapter_in_prompt()
