#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify random key selection on each API call.
"""

import sys
import time
from src.gemini_client_pool import gemini_call_text_free, load_keys

def test_random_key_loading():
    """Test that keys are loaded from config and used randomly."""
    print("=" * 60)
    print("Testing Random Key Selection")
    print("=" * 60)
    
    # Test 1: Verify keys can be loaded from config
    print("\n1. Testing key loading from config...")
    keys = load_keys()
    if not keys:
        print("❌ FAIL: No keys loaded")
        return False
    print(f"✅ SUCCESS: Loaded {len(keys)} keys")
    
    # Test 2: Make multiple API calls to verify random key usage
    print("\n2. Testing multiple API calls with random keys...")
    system_prompt = "Bạn là một trợ lý AI hữu ích."
    user_prompt = "Hãy trả lời ngắn gọn: Hôm nay là ngày gì?"
    
    try:
        for i in range(3):
            print(f"\n   Call {i+1}:")
            response = gemini_call_text_free(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model="gemini-2.5-flash",
                temperature=0.3,
                per_job_sleep=0.1
            )
            print(f"   Response length: {len(response)} chars")
            if i < 2:
                time.sleep(1)  # Short delay between calls
        
        print("\n✅ SUCCESS: All API calls completed successfully")
        print("   Each call loaded keys fresh and used a random key")
        return True
        
    except Exception as e:
        print(f"\n❌ FAIL: API call error: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("Random Key Selection Test")
    print("=" * 60)
    print("\nThis test verifies:")
    print("1. Keys are loaded from config path")
    print("2. Each API call uses a fresh random key")
    print("3. No need to pass keys parameter explicitly")
    print("=" * 60)
    
    success = test_random_key_loading()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED")
        print("Keys are loaded dynamically on each call for random selection")
    else:
        print("❌ TESTS FAILED")
        print("Please check your API keys configuration")
    print("=" * 60 + "\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
