#!/usr/bin/env python3
"""
Convert .properties files to JSON format for external translation hosting.
Supports both backend (message_*.properties) and frontend (bigpicture_*.properties) files.

Usage:
    python src/convert_properties_to_json.py --file output/bigpicture/message_ru_RU.properties --output translations/message_ru-RU.json
    python src/convert_properties_to_json.py --file output/bigpicture-admin/bigpicture_ru_RU.properties --output translations/bigpicture_ru-RU.json
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any


def parse_properties_file(filepath: Path) -> Dict[str, str]:
    """
    Parse a .properties file and return a dictionary of key-value pairs.
    Handles Unicode escapes and comments.
    """
    translations = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Remove leading/trailing whitespace
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Split on first '=' sign
            if '=' not in line:
                continue
            
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Handle Unicode escapes (\uXXXX)
            value = decode_unicode_escapes(value)
            
            translations[key] = value
    
    return translations


def decode_unicode_escapes(text: str) -> str:
    r"""
    Decode Unicode escape sequences (\uXXXX) in text.
    Example: \u0413\u043B\u043E\u0431\u0430\u043B\u044C\u043D\u044B\u0435 → Глобальные
    """
    def replace_unicode(match):
        code = int(match.group(1), 16)
        return chr(code)
    
    # Match \uXXXX patterns
    pattern = r'\\u([0-9a-fA-F]{4})'
    return re.sub(pattern, replace_unicode, text)


def create_bigpicture_api_format(translations: Dict[str, str], locale: str = "ru-RU") -> Dict[str, Any]:
    """
    Create BigPicture API response format:
    {
        "locale": "ru-RU",
        "translation": {
            "KEY1": "Value 1",
            "KEY2": "Value 2",
            ...
        }
    }
    """
    return {
        "locale": locale,
        "translation": translations
    }


def convert_properties_to_json(properties_file: Path, output_file: Path, locale: str = None, 
                               api_format: bool = True) -> None:
    """
    Convert .properties file to JSON format.
    
    Args:
        properties_file: Path to .properties file
        output_file: Path to output JSON file
        locale: Locale code (auto-detected from filename if not provided)
        api_format: If True, wraps in BigPicture API format with "locale" and "translation" keys
    """
    if not properties_file.exists():
        raise FileNotFoundError(f"Properties file not found: {properties_file}")
    
    # Auto-detect locale from filename if not provided
    if locale is None:
        filename = properties_file.stem
        # Try to extract locale from filename (e.g., message_ru_RU or message_ru-RU)
        match = re.search(r'_(ru[-_]RU|en[-_]US|de[-_]DE|fr[-_]FR|pl[-_]PL|pt[-_]BR|es[-_]ES|uk[-_]UA)', filename, re.IGNORECASE)
        if match:
            locale_str = match.group(1).upper().replace('_', '-')
            locale = locale_str
        else:
            locale = "ru-RU"  # Default
    
    print(f"Converting {properties_file.name} to JSON...")
    print(f"Locale: {locale}")
    
    # Parse properties file
    translations = parse_properties_file(properties_file)
    print(f"✓ Parsed {len(translations)} translation keys")
    
    # Create output format
    if api_format:
        output_data = create_bigpicture_api_format(translations, locale)
    else:
        output_data = translations
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Saved JSON to: {output_file}")
    print(f"  Size: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"  Keys: {len(translations)}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert .properties files to JSON format for external translation hosting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert backend translations
  python src/convert_properties_to_json.py --file output/bigpicture/message_ru_RU.properties --output translations/message_ru-RU.json
  
  # Convert frontend translations
  python src/convert_properties_to_json.py --file output/bigpicture-admin/bigpicture_ru_RU.properties --output translations/bigpicture_ru-RU.json
  
  # Convert without API format (just key-value pairs)
  python src/convert_properties_to_json.py --file message_ru_RU.properties --output translations.json --no-api-format
  
  # Specify locale explicitly
  python src/convert_properties_to_json.py --file message_ru_RU.properties --output translations.json --locale ru-RU
        """
    )
    
    parser.add_argument('--file', '-f', type=Path,
                       help='Path to .properties file to convert (required unless --all-bigpicture)')
    parser.add_argument('--output', '-o', type=Path,
                       help='Path to output JSON file (required unless --all-bigpicture)')
    parser.add_argument('--locale', '-l', type=str,
                       help='Locale code (e.g., ru-RU). Auto-detected from filename if not provided')
    parser.add_argument('--no-api-format', action='store_true',
                       help='Output simple key-value JSON instead of BigPicture API format')
    parser.add_argument('--all-bigpicture', action='store_true',
                       help='Convert all BigPicture translation files to JSON')
    
    args = parser.parse_args()
    
    if args.all_bigpicture:
        # Convert all BigPicture translation files
        base_dir = Path('output')
        
        files_to_convert = [
            {
                'input': base_dir / 'bigpicture' / 'message_ru_RU.properties',
                'output': Path('translations') / 'message_ru-RU.json',
                'locale': 'ru-RU'
            },
            {
                'input': base_dir / 'bigpicture-admin' / 'bigpicture_ru_RU.properties',
                'output': Path('translations') / 'bigpicture_ru-RU.json',
                'locale': 'ru-RU'
            }
        ]
        
        print("=== Converting All BigPicture Translation Files ===\n")
        
        for file_info in files_to_convert:
            if file_info['input'].exists():
                convert_properties_to_json(
                    file_info['input'],
                    file_info['output'],
                    file_info.get('locale'),
                    api_format=not args.no_api_format
                )
                print()
            else:
                print(f"⚠️  Skipping {file_info['input']} - not found\n")
    else:
        # Convert single file
        if not args.file:
            parser.error('--file/-f is required unless --all-bigpicture is used')
        if not args.output:
            parser.error('--output/-o is required unless --all-bigpicture is used')
        
        convert_properties_to_json(
            args.file,
            args.output,
            args.locale,
            api_format=not args.no_api_format
        )


if __name__ == '__main__':
    main()

