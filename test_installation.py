#!/usr/bin/env python3
"""
Test script to verify system installation and configuration.
"""
import os
import sys

def test_imports():
    """Test if all required modules can be imported."""
    print("Testing imports...")
    try:
        import yaml
        print("  ✓ pyyaml")
    except ImportError:
        print("  ✗ pyyaml - Run: pip install pyyaml")
        return False
    
    try:
        import requests
        print("  ✓ requests")
    except ImportError:
        print("  ✗ requests - Run: pip install requests")
        return False
    
    try:
        import regex
        print("  ✓ regex")
    except ImportError:
        print("  ✗ regex - Run: pip install regex")
        return False
    
    return True

def test_config():
    """Test if config file exists and is valid."""
    print("\nTesting configuration...")
    
    config_path = "config/config.yaml"
    if not os.path.exists(config_path):
        print(f"  ✗ Config file not found: {config_path}")
        return False
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"  ✓ Config file loaded")
        
        # Check required sections
        required = ['default_llm', 'task_configs', 'paths', 'story']
        for section in required:
            if section in config:
                print(f"  ✓ Section '{section}' exists")
            else:
                print(f"  ✗ Section '{section}' missing")
                return False
        
        return True
    except Exception as e:
        print(f"  ✗ Error loading config: {str(e)}")
        return False

def test_motif():
    """Test if motif file exists and is valid."""
    print("\nTesting motif file...")
    
    motif_path = "data/motif.json"
    if not os.path.exists(motif_path):
        print(f"  ✗ Motif file not found: {motif_path}")
        return False
    
    try:
        import json
        with open(motif_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        motifs = data.get('motifs', [])
        print(f"  ✓ Motif file loaded")
        print(f"  ✓ Found {len(motifs)} motifs")
        
        if motifs:
            print(f"  ✓ Sample motif: {motifs[0].get('title')}")
        
        return True
    except Exception as e:
        print(f"  ✗ Error loading motif: {str(e)}")
        return False

def test_api_key():
    """Test if API key is configured."""
    print("\nTesting Gemini API keys...")
    
    # Check file
    keys_file = "auth_files/keys.txt"
    if os.path.exists(keys_file):
        try:
            with open(keys_file, 'r') as f:
                keys = [line.strip() for line in f if line.strip()]
            if keys:
                print(f"  ✓ Found {len(keys)} API keys in {keys_file}")
                return True
            else:
                print(f"  ✗ {keys_file} exists but is empty")
        except Exception as e:
            print(f"  ✗ Error reading {keys_file}: {e}")
    else:
        print(f"  ⚠ {keys_file} not found")
    
    # Check environment variable
    api_keys = os.getenv('GOOGLE_API_KEYS')
    if api_keys:
        keys_list = [k.strip() for k in api_keys.split(',') if k.strip()]
        print(f"  ✓ GOOGLE_API_KEYS is set with {len(keys_list)} keys")
        return True
    
    print("  ✗ No Gemini API keys found")
    print("     Add keys to auth_files/keys.txt (one per line)")
    print("     Or set: export GOOGLE_API_KEYS='key1,key2,key3'")
    print("     Get keys from: https://aistudio.google.com/app/apikey")
    return False

def test_directories():
    """Test if required directories exist or can be created."""
    print("\nTesting directories...")
    
    from src.utils import ensure_directories
    
    try:
        ensure_directories()
        print("  ✓ All required directories created/verified")
        return True
    except Exception as e:
        print(f"  ✗ Error creating directories: {str(e)}")
        return False

def test_modules():
    """Test if custom modules can be imported."""
    print("\nTesting custom modules...")
    
    modules = [
        'src.utils',
        'src.checkpoint',
        'src.llm_client',
        'src.motif_loader',
        'src.outline_generator',
        'src.entity_manager',
        'src.chapter_writer',
        'src.post_processor'
    ]
    
    all_ok = True
    for module_name in modules:
        try:
            __import__(module_name)
            print(f"  ✓ {module_name}")
        except Exception as e:
            print(f"  ✗ {module_name}: {str(e)}")
            all_ok = False
    
    return all_ok

def main():
    """Run all tests."""
    print("=" * 60)
    print("AI Story Generation System - Installation Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Config", test_config()))
    results.append(("Motif", test_motif()))
    results.append(("API Key", test_api_key()))
    results.append(("Directories", test_directories()))
    results.append(("Custom Modules", test_modules()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n🎉 All tests passed! System is ready to use.")
        print("\nTry running:")
        print("  python main.py --story-id test --batches 1")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
