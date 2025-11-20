#!/usr/bin/env python3
"""
Import translation keys from a group JSON file into a single group-based database table.
All keys from plugins in a group are stored together in one table (e.g., "Linchpin Suite").
"""

import json
import sys
import argparse
from pathlib import Path
from typing import Dict
from db_group_manager import GroupDBManager

# Try to import YAML for config
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


def load_plugin_config(config_path: str = "config/plugins.yaml") -> Dict:
    """Load plugin configuration from YAML file."""
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def import_group_json(json_file: str, group_name: str, config_path: str = "config/plugins.yaml", 
                      db_path: str = "db/translations.db"):
    """
    Import a group JSON file into a single group-based database table.
    All keys from all plugins in the group are stored together in one table.
    
    Args:
        json_file: Path to JSON file with translation keys
        group_name: Group name from config (e.g., 'linchpin-suite')
        config_path: Path to plugins.yaml config file
        db_path: Database path
    """
    json_path = Path(json_file)
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_file}")
    
    # Load group info from config
    config = load_plugin_config(config_path)
    groups = config.get('groups', {})
    
    if group_name not in groups:
        raise ValueError(f"Group '{group_name}' not found in config. Available groups: {list(groups.keys())}")
    
    group_info = groups[group_name]
    display_name = group_info.get('name', group_name.replace('-', ' ').title())
    description = group_info.get('description', '')
    plugin_keys = group_info.get('plugins', [])
    
    print(f"Group: {display_name}")
    print(f"Description: {description}")
    print(f"Plugins in group: {len(plugin_keys)}")
    
    # Load JSON data
    print(f"\nLoading JSON file: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain a dictionary (key -> value), got {type(data)}")
    
    print(f"Total keys in JSON: {len(data)}")
    
    # Import all keys to group table
    manager = GroupDBManager(db_path)
    print(f"\nImporting all keys to group table: {group_name}")
    
    imported, updated, protected = manager.import_json_to_group_table(
        data, group_name, display_name, description
    )
    
    stats = manager.get_statistics(group_name)
    
    print(f"\n{'='*60}")
    print(f"✓ Import completed:")
    print(f"  New keys imported: {imported}")
    print(f"  Existing keys updated: {updated}")
    print(f"  Translations protected (not overwritten): {protected}")
    print(f"  Total keys in database: {stats['total']}")
    print(f"\n  Statistics:")
    print(f"    Total: {stats['total']}")
    print(f"    Translated: {stats['translated']}")
    print(f"    Pending: {stats['pending']}")
    print(f"    Progress: {stats['percentage']:.1f}%")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Import group JSON file into a single group-based database table',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import group JSON using group name from config
  python3 src/import_group_json.py --file raw_data/linchpin_group.json --group linchpin-suite
        """
    )
    
    parser.add_argument('--file', required=True,
                       help='JSON file with translation keys from a group fetch')
    parser.add_argument('--group', required=True,
                       help='Group name from config/plugins.yaml (e.g., linchpin-suite)')
    parser.add_argument('--config', default='config/plugins.yaml',
                       help='Config file path (default: config/plugins.yaml)')
    parser.add_argument('--db', default='db/translations.db',
                       help='Database path (default: db/translations.db)')
    
    args = parser.parse_args()
    
    try:
        import_group_json(
            args.file,
            group_name=args.group,
            config_path=args.config,
            db_path=args.db
        )
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
