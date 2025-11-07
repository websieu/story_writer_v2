#!/usr/bin/env python3
"""
Individual step scripts for story generation.

This file contains scripts that can be run independently to execute specific steps.
"""
import argparse
import sys
from main import StoryGenerator


def run_generate_outline(args):
    """Generate outline for a specific batch."""
    generator = StoryGenerator(config_path=args.config, story_id=args.story_id)
    
    motif = generator.checkpoint.get_metadata('motif')
    if not motif:
        if args.motif_id:
            motif = generator.motif_loader.get_motif_by_id(args.motif_id)
        else:
            motif = generator.motif_loader.get_random_motif(args.genre)
        generator.checkpoint.set_metadata('motif', motif)
    
    if args.batch == 1:
        outlines = generator.outline_generator.generate_initial_outline(motif, args.batch)
    else:
        context = generator._prepare_batch_context(args.batch, args.user_input)
        outlines = generator.outline_generator.generate_continuation_outline(args.batch, context)
    
    print(f"✓ Generated outline for batch {args.batch} with {len(outlines)} chapters")


def run_extract_entities(args):
    """Extract entities from outlines for a specific batch."""
    generator = StoryGenerator(config_path=args.config, story_id=args.story_id)
    
    # Load outlines
    outlines = generator.outline_generator._load_outline(args.batch)
    
    # Extract entities
    entities = generator.entity_manager.extract_entities_from_outlines(outlines, args.batch)
    
    total = sum(len(v) for v in entities.values())
    print(f"✓ Extracted {total} entities from batch {args.batch}")


def run_write_chapter(args):
    """Write a specific chapter."""
    generator = StoryGenerator(config_path=args.config, story_id=args.story_id)
    
    # Load outline for this chapter
    batch = (args.chapter - 1) // 5 + 1
    outlines = generator.outline_generator._load_outline(batch)
    
    # Find chapter outline
    chapter_outline = None
    for outline in outlines:
        if outline.get('chapter_number') == args.chapter:
            chapter_outline = outline
            break
    
    if not chapter_outline:
        print(f"✗ Outline for chapter {args.chapter} not found")
        return
    
    # Get motif
    motif = generator.checkpoint.get_metadata('motif')
    if not motif:
        print("✗ Motif not found. Run outline generation first.")
        return
    
    # Prepare context and write
    context = generator._prepare_chapter_context(args.chapter, chapter_outline, motif)
    chapter_content = generator.chapter_writer.write_chapter(chapter_outline, context)
    
    print(f"✓ Wrote chapter {args.chapter}: {chapter_outline.get('title')}")
    print(f"  Word count: {len(chapter_content.split())}")


def run_process_chapter(args):
    """Post-process a specific chapter."""
    generator = StoryGenerator(config_path=args.config, story_id=args.story_id)
    
    # Load chapter
    chapter_content = generator.chapter_writer._load_chapter(args.chapter)
    
    # Extract entities
    print(f"Extracting entities from chapter {args.chapter}...")
    new_entities = generator.entity_manager.extract_entities_from_chapter(chapter_content, args.chapter)
    
    # Process chapter
    print(f"Processing chapter {args.chapter}...")
    post_data = generator.post_processor.process_chapter(chapter_content, args.chapter)
    
    print(f"✓ Post-processed chapter {args.chapter}")
    print(f"  New entities: {sum(len(v) for v in new_entities.values())}")
    print(f"  Events: {len(post_data['events'])}")
    print(f"  Conflicts: {len(post_data['conflicts'])}")


def run_generate_batch(args):
    """Generate a complete batch."""
    generator = StoryGenerator(config_path=args.config, story_id=args.story_id)
    
    motif = generator.checkpoint.get_metadata('motif')
    if not motif:
        if args.motif_id:
            motif = generator.motif_loader.get_motif_by_id(args.motif_id)
        else:
            motif = generator.motif_loader.get_random_motif(args.genre)
        generator.checkpoint.set_metadata('motif', motif)
    
    generator.generate_batch(args.batch, motif, args.user_input)
    print(f"✓ Completed batch {args.batch}")


def main():
    """Main entry point for individual scripts."""
    parser = argparse.ArgumentParser(description="Run individual story generation steps")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Common arguments
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--story-id', default='story_001', help='Story identifier')
    common.add_argument('--config', default='config/config.yaml', help='Config file path')
    
    # Generate outline
    outline_parser = subparsers.add_parser('outline', parents=[common], help='Generate outline for a batch')
    outline_parser.add_argument('--batch', type=int, required=True, help='Batch number')
    outline_parser.add_argument('--motif-id', help='Motif ID (for batch 1)')
    outline_parser.add_argument('--genre', help='Genre (for batch 1)')
    outline_parser.add_argument('--user-input', help='User suggestions (for batch 2+)')
    outline_parser.set_defaults(func=run_generate_outline)
    
    # Extract entities
    entity_parser = subparsers.add_parser('entities', parents=[common], help='Extract entities from batch')
    entity_parser.add_argument('--batch', type=int, required=True, help='Batch number')
    entity_parser.set_defaults(func=run_extract_entities)
    
    # Write chapter
    chapter_parser = subparsers.add_parser('chapter', parents=[common], help='Write a specific chapter')
    chapter_parser.add_argument('--chapter', type=int, required=True, help='Chapter number')
    chapter_parser.set_defaults(func=run_write_chapter)
    
    # Process chapter
    process_parser = subparsers.add_parser('process', parents=[common], help='Post-process a chapter')
    process_parser.add_argument('--chapter', type=int, required=True, help='Chapter number')
    process_parser.set_defaults(func=run_process_chapter)
    
    # Generate batch
    batch_parser = subparsers.add_parser('batch', parents=[common], help='Generate complete batch')
    batch_parser.add_argument('--batch', type=int, required=True, help='Batch number')
    batch_parser.add_argument('--motif-id', help='Motif ID (for batch 1)')
    batch_parser.add_argument('--genre', help='Genre (for batch 1)')
    batch_parser.add_argument('--user-input', help='User suggestions (for batch 2+)')
    batch_parser.set_defaults(func=run_generate_batch)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        args.func(args)
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
