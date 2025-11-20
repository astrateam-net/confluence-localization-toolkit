#!/usr/bin/env python3
"""
Import existing translations from a JSON file into the database.
Filters out English keys and sets status to 'translated' so they won't be translated again.
Detects target language based on TARGET_LANGUAGE env var or locale parameter.
"""

import json
import sys
import os
import re
import argparse
from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime
try:
    from .db_group_manager import GroupDBManager
except ImportError:
    from db_group_manager import GroupDBManager

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass

try:
    from locale_utils import get_target_locale, get_locale_info
except ImportError:
    def get_target_locale():
        return os.getenv('TARGET_LANGUAGE', 'ru_RU').strip()
    def get_locale_info(locale=None):
        if locale is None:
            locale = get_target_locale()
        # Fallback: extract from locale code
        parts = locale.split('_')
        return {'language': parts[0].lower() if parts else 'ru', 'name': locale}


# Language detection patterns
LANGUAGE_PATTERNS = {
    'ru': re.compile(r'[\u0400-\u04FF]'),  # Cyrillic
    'de': re.compile(r'[äöüÄÖÜß]'),  # German umlauts
    'fr': re.compile(r'[àâäéèêëïîôùûüÿç]'),  # French accents
    'es': re.compile(r'[ñáéíóúüÑÁÉÍÓÚÜ¿¡]'),  # Spanish
    'it': re.compile(r'[àèéìíîòóùú]'),  # Italian
    'pt': re.compile(r'[áàâãéêíóôõúç]'),  # Portuguese
    'ja': re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'),  # Japanese
    'ko': re.compile(r'[\uAC00-\uD7AF]'),  # Korean
    'zh': re.compile(r'[\u4E00-\u9FFF]'),  # Chinese
    'pl': re.compile(r'[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]'),  # Polish
    'nl': re.compile(r'[éëïöüÉËÏÖÜ]'),  # Dutch
    'sv': re.compile(r'[äöåÄÖÅ]'),  # Swedish
    'fi': re.compile(r'[äöåÄÖÅ]'),  # Finnish
    'uk': re.compile(r'[\u0400-\u04FF\u0401\u0451]'),  # Ukrainian
}


def contains_target_language(text: str, locale: str = None) -> bool:
    """
    Check if text contains characters from the target language.
    
    Args:
        text: Text to check
        locale: Target locale (e.g., 'ru_RU', 'de_DE'). Defaults to TARGET_LANGUAGE env var.
    
    Returns:
        True if text contains characters typical of the target language
    """
    if not text:
        return False
    
    if locale is None:
        locale = get_target_locale()
    
    # Extract language code (e.g., 'ru' from 'ru_RU')
    lang_code = locale.split('_')[0].lower() if '_' in locale else locale.lower()
    
    # Get pattern for this language
    pattern = LANGUAGE_PATTERNS.get(lang_code)
    if pattern:
        return bool(pattern.search(text))
    
    # Fallback: if text contains non-ASCII characters and is not obviously English
    # (this is a heuristic - English typically only has ASCII + a few special chars)
    if any(ord(c) > 127 for c in text):
        # Check if it's likely not English (contains characters outside common ASCII range)
        return True
    
    return False


def filter_translations(json_data: Dict, locale: str = None) -> Tuple[Dict, int]:
    """
    Filter out English keys, keeping only translations in the target language.
    
    Args:
        json_data: Dictionary with translation keys
        locale: Target locale (e.g., 'ru_RU', 'de_DE'). Defaults to TARGET_LANGUAGE env var.
        
    Returns:
        Tuple of (translations_dict, english_count)
    """
    if locale is None:
        locale = get_target_locale()
    
    translations = {}
    english_count = 0
    
    for key, text in json_data.items():
        if contains_target_language(text, locale):
            translations[key] = text
        else:
            english_count += 1
    
    return translations, english_count


def import_translations(json_file: str, group_name: str, 
                       db_path: str = "db/translations.db",
                       locale: str = None):
    """
    Import existing translations from JSON file into database.
    Filters based on target locale and sets status to 'translated'.
    
    Args:
        json_file: Path to JSON file with translation keys (may contain English and target language)
        group_name: Group name (e.g., 'comala-workflow')
        db_path: Database path
        locale: Target locale (e.g., 'ru_RU', 'de_DE'). Defaults to TARGET_LANGUAGE env var.
    """
    if locale is None:
        locale = get_target_locale()
    
    locale_info = get_locale_info(locale)
    lang_name = locale_info.get('name', locale)
    
    json_path = Path(json_file)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")
    
    print(f"Loading JSON file: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain a dictionary (key -> value), got {type(data)}")
    
    total_keys = len(data)
    print(f"Total keys in JSON: {total_keys}")
    
    # Filter to only target language translations
    print(f"\nFiltering {lang_name} translations (locale: {locale})...")
    translations, english_count = filter_translations(data, locale)
    translation_count = len(translations)
    
    print(f"  {lang_name} translations: {translation_count}")
    print(f"  English keys (skipped): {english_count}")
    
    if translation_count == 0:
        print(f"\n⚠ No {lang_name} translations found in the JSON file!")
        return
    
    # Import to database
    manager = GroupDBManager(db_path)
    table_name = manager.get_table_name(group_name)
    
    print(f"\nImporting {lang_name} translations to group table: {group_name}")
    
    imported = 0
    updated = 0
    skipped = 0
    
    with manager.connection() as conn:
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, (table_name,))
        if not cursor.fetchone():
            print(f"⚠ Table '{table_name}' does not exist. Creating it...")
            manager.create_group_table(group_name)
        
        for key, translated_text in translations.items():
            # Check if key exists in database
            cursor.execute(f"""
                SELECT key, translated_text, status FROM {table_name} 
                WHERE key = ?
            """, (key,))
            existing_row = cursor.fetchone()
            
            if existing_row:
                # Key exists - update with translation
                cursor.execute(f"""
                    UPDATE {table_name} 
                    SET translated_text = ?, 
                        translation_method = 'imported',
                        status = 'translated',
                        updated_at = ?
                    WHERE key = ?
                """, (translated_text, datetime.now().isoformat(), key))
                updated += 1
            else:
                # Key doesn't exist - insert new row
                # We need original_text, but we don't have it in translation JSON
                # Set it to empty for now
                now = datetime.now().isoformat()
                cursor.execute(f"""
                    INSERT INTO {table_name} 
                    (key, original_text, translated_text, plugin_key, 
                     translation_method, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'imported', 'translated', ?, ?)
                """, (key, '', translated_text, None, now, now))
                imported += 1
    
    stats = manager.get_statistics(group_name)
    
    print(f"\n{'='*60}")
    print(f"✓ Import completed:")
    print(f"  New keys imported ({lang_name}): {imported}")
    print(f"  Existing keys updated ({lang_name}): {updated}")
    print(f"  English keys skipped: {english_count}")
    print(f"\n  Database statistics:")
    print(f"    Total: {stats['total']}")
    print(f"    Translated: {stats['translated']}")
    print(f"    Pending: {stats['pending']}")
    print(f"    Progress: {stats['percentage']:.1f}%")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Import existing translations from JSON file into database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import translations from JSON file (uses TARGET_LANGUAGE env var or defaults to ru_RU)
  python3 src/import_russian_translations.py --file raw_data/comala-workflow_20251120_052446.json --group comala-workflow
  
  # Specify target locale
  python3 src/import_russian_translations.py --file raw_data/translations.json --group my-group --locale de_DE
        """
    )
    
    parser.add_argument('--file', required=True,
                       help='JSON file with translation keys (may contain English and target language)')
    parser.add_argument('--group', required=True,
                       help='Group name (e.g., comala-workflow)')
    parser.add_argument('--locale', default=None,
                       help='Target locale (e.g., ru_RU, de_DE). Defaults to TARGET_LANGUAGE env var or ru_RU')
    parser.add_argument('--db', default='db/translations.db',
                       help='Database path (default: db/translations.db)')
    
    args = parser.parse_args()
    
    try:
        import_translations(
            args.file,
            group_name=args.group,
            db_path=args.db,
            locale=args.locale
        )
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

