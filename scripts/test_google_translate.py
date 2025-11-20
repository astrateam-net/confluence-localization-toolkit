#!/usr/bin/env python3
"""
Test Google Cloud Translation API connection.
"""

import sys
import os
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

try:
    from google.cloud import translate_v2 as translate
except ImportError:
    print("ERROR: google-cloud-translate not installed. Install with: pip install google-cloud-translate")
    sys.exit(1)

def test_connection():
    """Test Google Cloud Translation API connection."""
    
    print("=" * 60)
    print("Testing Google Cloud Translation API Connection")
    print("=" * 60)
    print()
    
    # Check credentials path
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        print("❌ ERROR: GOOGLE_APPLICATION_CREDENTIALS not set in .env file")
        return False
    
    print(f"✓ Credentials path: {creds_path}")
    
    # Check if file exists
    if not os.path.exists(creds_path):
        print(f"❌ ERROR: Credentials file not found: {creds_path}")
        return False
    
    print(f"✓ Credentials file exists")
    
    # Initialize client
    try:
        print("\nInitializing Google Cloud Translation client...")
        client = translate.Client.from_service_account_json(creds_path)
        print("✓ Client initialized successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize client: {e}")
        return False
    
    # Test 1: Get supported languages
    try:
        print("\nTest 1: Getting supported languages...")
        languages = client.get_languages(target_language='ru')
        print(f"✓ Success! Found {len(languages)} supported languages")
        print(f"  Sample languages: {', '.join([l['name'] for l in languages[:5]])}")
    except Exception as e:
        print(f"❌ ERROR: Failed to get languages: {e}")
        return False
    
    # Test 2: Simple translation
    try:
        print("\nTest 2: Translating sample text...")
        test_text = "Hello world! This is a test translation."
        result = client.translate(
            test_text,
            source_language='en',
            target_language='ru'
        )
        translated = result['translatedText']
        print(f"✓ Translation successful!")
        print(f"  Original: {test_text}")
        print(f"  Translated: {translated}")
    except Exception as e:
        print(f"❌ ERROR: Failed to translate: {e}")
        return False
    
    # Test 3: Translation with HTML tags
    try:
        print("\nTest 3: Translating text with HTML tags...")
        html_text = "Click <strong>here</strong> to continue"
        result = client.translate(
            html_text,
            source_language='en',
            target_language='ru',
            format_='html'
        )
        translated = result['translatedText']
        print(f"✓ HTML translation successful!")
        print(f"  Original: {html_text}")
        print(f"  Translated: {translated}")
    except Exception as e:
        print(f"❌ ERROR: Failed to translate HTML: {e}")
        return False
    
    # Test 4: Translation with placeholders
    try:
        print("\nTest 4: Translating text with placeholders...")
        placeholder_text = "Welcome {0}, you have {1} messages"
        result = client.translate(
            placeholder_text,
            source_language='en',
            target_language='ru',
            format_='html'
        )
        translated = result['translatedText']
        print(f"✓ Placeholder translation successful!")
        print(f"  Original: {placeholder_text}")
        print(f"  Translated: {translated}")
    except Exception as e:
        print(f"❌ ERROR: Failed to translate with placeholders: {e}")
        return False
    
    print()
    print("=" * 60)
    print("✅ All tests passed! Google Cloud Translation API is working.")
    print("=" * 60)
    
    return True

if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)

