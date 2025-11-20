#!/usr/bin/env python3
"""
Export group translations from database to Java properties files in chunks.

Each chunk will contain up to N keys (default 500).
Chunks are named with sequential numbers: prefix_1_locale.properties, prefix_2_locale.properties, etc.
"""

import sys
import os
from pathlib import Path
from db_group_manager import GroupDBManager


def cyrillic_to_unicode_escape(text: str) -> str:
    """Convert Cyrillic text to Unicode escape sequences for Java properties files."""
    result = []
    for char in text:
        code = ord(char)
        if code > 127:
            result.append(f'\\u{code:04X}')
        else:
            result.append(char)
    return ''.join(result)


def export_group_chunks(
    group_key: str,
    output_dir: str,
    prefix: str = None,
    locale: str = "ru_RU",
    keys_per_chunk: int = 500,
    db_path: str = "db/translations.db",
    only_translated: bool = True
):
    """
    Export group translations to Java properties files in chunks.
    
    Args:
        group_key: Group key to export
        output_dir: Directory to write chunk files
        prefix: Prefix for output files (e.g., 'linchpin_suite'). If None, uses group_key
        locale: Locale code (e.g., 'ru_RU')
        keys_per_chunk: Maximum number of keys per chunk (default 500)
        db_path: Database path
        only_translated: Only export translated keys (default: True)
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
        return []
    
    # Use group_key as prefix if not provided
    if not prefix:
        prefix = group_key.replace('-', '_')
    
    # Get table name
    table_name = manager.get_table_name(group_key)
    
    # Fetch all translations
    with manager.connection() as conn:
        cursor = conn.cursor()
        query = f"SELECT key, translated_text FROM {table_name} WHERE translated_text IS NOT NULL"
        if only_translated:
            query += " AND status = 'translated'"
        query += " ORDER BY key"
        cursor.execute(query)
        rows = cursor.fetchall()
        translations = [(row['key'], row['translated_text']) for row in rows]
    
    if not translations:
        print("⚠ No keys to export!")
        return []
    
    total_keys = len(translations)
    num_chunks = (total_keys + keys_per_chunk - 1) // keys_per_chunk  # Ceiling division
    
    print(f"\nExporting {total_keys} keys into {num_chunks} chunks of up to {keys_per_chunk} keys each")
    print()
    
    # Create output directory - use group-specific folder in output/
    if not Path(output_dir).is_absolute() and 'output' not in output_dir:
        # Create group folder in output/
        output_path = Path('output') / group_key / output_dir
    else:
        output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    chunk_files = []
    
    # Create chunks
    for chunk_num in range(1, num_chunks + 1):
        start_idx = (chunk_num - 1) * keys_per_chunk
        end_idx = min(start_idx + keys_per_chunk, total_keys)
        
        chunk_keys = translations[start_idx:end_idx]
        
        # Generate filename: prefix_1_locale.properties
        chunk_filename = f"{prefix}_{chunk_num}_{locale}.properties"
        chunk_filepath = output_path / chunk_filename
        
        # Write chunk file
        with open(chunk_filepath, 'w', encoding='utf-8') as f:
            f.write("# Generated translation properties file\n")
            f.write(f"# Group: {group_key}\n")
            f.write(f"# Chunk: {chunk_num} of {num_chunks}\n")
            f.write(f"# Keys in this chunk: {len(chunk_keys)} (range: {start_idx + 1}-{end_idx} of {total_keys})\n")
            f.write(f"# Locale: {locale}\n")
            f.write(f"# Generated: {os.popen('date').read().strip()}\n")
            f.write("\n")
            
            # Write key-value pairs
            for key, translated_text in chunk_keys:
                # Escape key if needed
                escaped_key = key.replace('\\', '\\\\').replace('=', '\\=').replace(':', '\\:')
                # Escape value and convert to Unicode escapes
                escaped_value = cyrillic_to_unicode_escape(translated_text)
                # Escape newlines only - Unicode escapes (\uXXXX) don't need backslash escaping
                escaped_value = escaped_value.replace('\n', '\\n')
                
                f.write(f"{escaped_key}={escaped_value}\n")
        
        file_size = chunk_filepath.stat().st_size
        chunk_files.append(chunk_filepath)
        print(f"Created: {chunk_filename} ({len(chunk_keys)} keys, {file_size:,} bytes)")
    
    print()
    print(f"✓ Successfully created {num_chunks} chunk files in {output_path}")
    
    return chunk_files


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Export group translations to Java properties files in chunks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export in chunks of 500 keys (default)
  python3 src/export_group_chunks.py --group linchpin-suite --output output/chunks
  
  # Export in chunks of 1000 keys with custom prefix
  python3 src/export_group_chunks.py --group linchpin-suite --output output/chunks --prefix linchpin_suite --chunk-size 1000
  
  # Export with different locale
  python3 src/export_group_chunks.py --group linchpin-suite --output output/chunks --locale en_US
        """
    )
    
    parser.add_argument('--group', required=True,
                       help='Group key to export (e.g., linchpin-suite)')
    parser.add_argument('--output', required=True,
                       help='Output directory for chunk files')
    parser.add_argument('--prefix', default=None,
                       help='Prefix for output files (e.g., linchpin_suite). Default: group_key with dashes replaced')
    parser.add_argument('--locale', default='ru_RU',
                       help='Locale code (default: ru_RU)')
    parser.add_argument('--chunk-size', type=int, default=500,
                       help='Number of keys per chunk (default: 500)')
    parser.add_argument('--all', action='store_true',
                       help='Export all keys, not just translated ones')
    parser.add_argument('--db', default='db/translations.db',
                       help='Database path (default: db/translations.db)')
    
    args = parser.parse_args()
    
    try:
        chunk_files = export_group_chunks(
            args.group,
            args.output,
            prefix=args.prefix,
            locale=args.locale,
            keys_per_chunk=args.chunk_size,
            db_path=args.db,
            only_translated=not args.all
        )
        
        if chunk_files:
            print(f"\nChunk files created:")
            for chunk_file in chunk_files:
                print(f"  - {chunk_file}")
        
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

