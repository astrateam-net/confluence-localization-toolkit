#!/usr/bin/env python3
"""
Export group translations from database to Java properties file.
Includes Unicode escaping for Cyrillic characters.
"""

import sys
import os
import re
from pathlib import Path
from db_group_manager import GroupDBManager


def cyrillic_to_unicode_escape(text: str) -> str:
    """Convert Cyrillic text to Unicode escape sequences for Java properties files."""
    result = []
    for char in text:
        code = ord(char)
        if code > 127:
            # Create literal \uXXXX string (single backslash, not double)
            # In Python: '\\u' creates a string with single backslash
            result.append('\\u' + f'{code:04X}')
        else:
            result.append(char)
    return ''.join(result)


def verify_unicode_escape(original_text: str, escaped_text: str) -> bool:
    """
    Verify that Unicode escape conversion is correct by decoding and comparing.
    
    Returns True if the decoded escape matches the original text.
    """
    def replace_unicode(match):
        code = int(match.group(1), 16)
        return chr(code)
    
    # Decode Unicode escapes back to text
    try:
        decoded = re.sub(r'\\u([0-9A-Fa-f]{4})', replace_unicode, escaped_text)
        return decoded == original_text
    except Exception:
        return False


def export_group_properties(group_key: str, output_file: str, 
                            db_path: str = "db/translations.db",
                            only_translated: bool = True,
                            raw_output: bool = False):
    """
    Export group translations to Java properties file.
    
    Args:
        group_key: Group key to export
        output_file: Output properties file path
        db_path: Database path
        only_translated: Only export translated keys (default: True)
        raw_output: If True, export raw Cyrillic without Unicode escapes (default: False)
    
    Returns:
        bool: True if export and verification succeeded, False otherwise
    """
    manager = GroupDBManager(db_path)
    
    # Get statistics
    stats = manager.get_statistics(group_key)
    print(f"Exporting group: {group_key}")
    print(f"Total keys: {stats['total']}")
    print(f"Translated: {stats['translated']}")
    print(f"Pending: {stats['pending']}")
    
    if only_translated and stats['translated'] == 0:
        print("⚠ No translated keys found!")
        return False
    
    # Get translations using the manager's method
    # We'll get them directly since we have the table name
    table_name = manager.get_table_name(group_key)
    
    with manager.connection() as conn:
        cursor = conn.cursor()
        query = f"SELECT key, translated_text FROM {table_name} WHERE translated_text IS NOT NULL"
        if only_translated:
            query += " AND status = 'translated'"
        query += " ORDER BY key"
        cursor.execute(query)
        rows = cursor.fetchall()
        # Rows are already dict-like due to sqlite3.Row factory
        translations = [(row['key'], row['translated_text']) for row in rows]
    
    if not translations:
        print("⚠ No keys to export!")
        return False
    
    # Write to properties file
    # Create group-specific folder in output/
    output_path = Path(output_file)
    
    # If output_file is just a filename or relative path, create group folder
    if not output_path.is_absolute() and (output_path.parent == Path('.') or str(output_path.parent) == '' or str(output_path.parent) == output_file):
        # No directory specified, create group folder in output/
        output_dir = Path('output') / group_key
        output_dir.mkdir(parents=True, exist_ok=True)
        # Default filename: {group_key}_ru_RU.properties
        if not output_path.name or output_path.name == '.':
            output_path = output_dir / f"{group_key}_ru_RU.properties"
        else:
            output_path = output_dir / output_path.name
    elif not output_path.is_absolute() and 'output' not in str(output_path.parent):
        # Path specified but not in output/, create group folder anyway
        output_dir = Path('output') / group_key
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / output_path.name
    else:
        # Directory specified, ensure it exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\nWriting {len(translations)} keys to: {output_path}")
    
    # Java Properties files: UTF-8 is supported since Java 9, but ISO-8859-1 is the legacy standard
    # Using UTF-8 for better compatibility with Unicode escapes
    # If Confluence requires ISO-8859-1, we can change encoding here
    encoding = 'utf-8'  # Change to 'iso-8859-1' if Confluence requires it
    with open(output_path, 'w', encoding=encoding, errors='strict') as f:
        f.write("# Generated translation properties file\n")
        f.write(f"# Group: {group_key}\n")
        f.write(f"# Total keys: {len(translations)}\n")
        f.write(f"# Generated: {os.popen('date').read().strip()}\n")
        f.write("\n")
        
        verification_errors = []
        verification_count = 0
        
        for key, translated_text in translations:
            # Escape key if needed
            escaped_key = key.replace('\\', '\\\\').replace('=', '\\=').replace(':', '\\:')
            # Escape value
            if raw_output:
                # Export raw Cyrillic text without Unicode conversion
                escaped_value = translated_text.replace('\\', '\\\\').replace('\n', '\\n')
            else:
                # Convert to Unicode escapes (default behavior)
                escaped_value = cyrillic_to_unicode_escape(translated_text)
                
                # Verification: Decode and compare with original
                if not verify_unicode_escape(translated_text, escaped_value):
                    verification_errors.append({
                        'key': key,
                        'original': translated_text[:100],
                        'escaped': escaped_value[:100]
                    })
                verification_count += 1
                
                # Escape newlines only
                # Unicode escapes (\uXXXX) don't need backslash escaping in Java properties files
                escaped_value = escaped_value.replace('\n', '\\n')
            
            f.write(f"{escaped_key}={escaped_value}\n")
        
        # Report verification results
        if not raw_output and verification_count > 0:
            print(f"\n✓ Verification: Checked {verification_count} translations")
            if verification_errors:
                print(f"⚠ Verification errors: {len(verification_errors)}")
                for i, err in enumerate(verification_errors[:5], 1):
                    print(f"  {i}. Key: {err['key']}")
                    print(f"     Original: {err['original']}...")
                    print(f"     Escaped: {err['escaped']}...")
                if len(verification_errors) > 5:
                    print(f"     ... and {len(verification_errors) - 5} more errors")
                verification_passed = False
            else:
                print(f"✓ All {verification_count} translations verified correctly")
                verification_passed = True
        else:
            verification_passed = True
    
    print(f"✓ Exported {len(translations)} keys to: {output_path}")
    
    # Verify file was written correctly
    if not raw_output and output_path.exists():
        # Check first few lines for double backslashes
        with open(output_path, 'rb') as f:
            first_1000_bytes = f.read(1000)
            if b'\\\\u' in first_1000_bytes:
                print("⚠ Warning: Found double backslashes (\\\\u) in output file!")
                print("   This may cause issues. File format should use single backslashes (\\u)")
                verification_passed = False
            else:
                print("✓ File format verified: Single backslashes (\\uXXXX)")
    
    # Show statistics
    final_stats = manager.get_statistics(group_key)
    print(f"\n  Statistics:")
    print(f"    Total: {final_stats['total']}")
    print(f"    Translated: {final_stats['translated']}")
    print(f"    Pending: {final_stats['pending']}")
    print(f"    Progress: {final_stats['percentage']:.1f}%")
    
    return verification_passed


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Export group translations to Java properties file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export only translated keys (with Unicode escapes)
  python3 src/export_group.py --group linchpin-suite --output output/linchpin_suite_ru_RU.properties
  
  # Export raw Cyrillic without Unicode conversion (for comparison)
  python3 src/export_group.py --group linchpin-suite --output output/linchpin_suite_raw.properties --raw
  
  # Export all keys (including untranslated)
  python3 src/export_group.py --group linchpin-suite --output output/all_keys.properties --all
        """
    )
    
    parser.add_argument('--group', required=True,
                       help='Group key to export (e.g., linchpin-suite)')
    parser.add_argument('--output', required=True,
                       help='Output properties file path')
    parser.add_argument('--all', action='store_true',
                       help='Export all keys, not just translated ones')
    parser.add_argument('--raw', action='store_true',
                       help='Export raw Cyrillic text without Unicode escapes (for comparison)')
    parser.add_argument('--db', default='db/translations.db',
                       help='Database path (default: db/translations.db)')
    
    args = parser.parse_args()
    
    try:
        success = export_group_properties(
            args.group,
            args.output,
            args.db,
            only_translated=not args.all,
            raw_output=args.raw
        )
        if not success:
            print("\n⚠ Export completed but verification failed. Please review errors above.")
            sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

