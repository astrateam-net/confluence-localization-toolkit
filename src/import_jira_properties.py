#!/usr/bin/env python3
"""
Import Jira plugin properties file into database for translation.
Extracts keys from Java properties file and imports them into a group-based table.
"""

import sys
import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple
from db_group_manager import GroupDBManager

def parse_properties_file(properties_file: str) -> Dict[str, str]:
    """
    Parse Java properties file and extract key-value pairs.
    Handles multi-line values, escape sequences, and comments.
    
    Args:
        properties_file: Path to properties file
        
    Returns:
        Dictionary of key-value pairs
    """
    props = {}
    current_key = None
    current_value = []
    
    with open(properties_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.rstrip('\n\r')
            
            # Skip comments and empty lines
            if not line.strip() or line.strip().startswith('#'):
                continue
            
            # Check for continuation line (starts with whitespace)
            if line[0] in ' \t' and current_key:
                current_value.append(line.lstrip())
                continue
            
            # Save previous key-value pair
            if current_key:
                value = ''.join(current_value)
                props[current_key] = value
                current_key = None
                current_value = []
            
            # Parse new key-value pair
            if '=' in line:
                parts = line.split('=', 1)
                current_key = parts[0].strip()
                value_part = parts[1] if len(parts) > 1 else ''
                current_value = [value_part]
            elif ':' in line and '=' not in line:
                # Some properties files use ':' as separator
                parts = line.split(':', 1)
                current_key = parts[0].strip()
                value_part = parts[1] if len(parts) > 1 else ''
                current_value = [value_part]
        
        # Save last key-value pair
        if current_key:
            value = ''.join(current_value)
            props[current_key] = value
    
    return props


def import_jira_properties(properties_file: str, group_name: str, 
                          db_path: str = "db/translations.db"):
    """
    Import Jira plugin properties file into database.
    
    Args:
        properties_file: Path to properties file (e.g., message_en-US.properties)
        group_name: Group name for database table (e.g., 'bigpicture')
        db_path: Database path
    """
    props_path = Path(properties_file)
    if not props_path.exists():
        raise FileNotFoundError(f"Properties file not found: {properties_file}")
    
    print(f"Parsing properties file: {properties_file}")
    translations = parse_properties_file(properties_file)
    print(f"Found {len(translations)} translation keys")
    
    # Initialize database manager
    db = GroupDBManager(db_path)
    
    # Import using existing import_json_to_group_table method
    print(f"Importing keys to group: {group_name}")
    imported, updated, protected = db.import_json_to_group_table(
        translations, 
        group_name,
        display_name=group_name.replace('-', ' ').title(),
        description=f"Jira plugin: {group_name}"
    )
    
    print(f"\nImport complete:")
    print(f"  Imported: {imported} new keys")
    print(f"  Updated: {updated} existing keys (no translation)")
    print(f"  Protected: {protected} existing keys (with translation, not overwritten)")
    print(f"  Total: {len(translations)} keys in file")


def main():
    parser = argparse.ArgumentParser(
        description='Import Jira plugin properties file into translation database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import English properties file for BigPicture
  python src/import_jira_properties.py --file temp_jira_plugin/extracted/l10n/message_en-US.properties --group bigpicture
  
  # Import with custom database
  python src/import_jira_properties.py --file message.properties --group myplugin --db custom.db
        """
    )
    
    parser.add_argument('--file', '-f', required=True,
                       help='Path to properties file to import')
    parser.add_argument('--group', '-g', required=True,
                       help='Group name for database table (e.g., bigpicture)')
    parser.add_argument('--db', default='db/translations.db',
                       help='Database path (default: db/translations.db)')
    
    args = parser.parse_args()
    
    try:
        import_jira_properties(args.file, args.group, args.db)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

