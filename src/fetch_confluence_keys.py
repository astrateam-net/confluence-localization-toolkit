#!/usr/bin/env python3
"""
Fetch translation keys from Confluence REST API.
Supports fetching keys for multiple plugins via API calls.
Stores raw API responses in raw_data/ folder.
"""

import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, will use environment variables or command-line args
    pass

# YAML support for config file
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("Warning: PyYAML not installed. Install with: pip install pyyaml", file=sys.stderr)


class ConfluenceKeyFetcher:
    """Fetches translation keys from Confluence REST API."""
    
    def __init__(self, base_url: str = None, bearer_token: str = None):
        """
        Initialize fetcher with Confluence connection details.
        
        Args:
            base_url: Confluence base URL (e.g., https://yourdomain.com)
            bearer_token: Bearer token for API authentication
        """
        # Get URL from parameter, environment variable, or error
        self.base_url = base_url or os.getenv('CONFLUENCE_URL')
        if not self.base_url:
            raise ValueError(
                "Confluence URL required. Set CONFLUENCE_URL in .env file, "
                "export CONFLUENCE_URL environment variable, or use --url parameter."
            )
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip('/')
        
        # Get token from parameter, environment variable, or error
        self.bearer_token = bearer_token or os.getenv('CONFLUENCE_BEARER_TOKEN')
        if not self.bearer_token:
            raise ValueError(
                "Confluence Bearer token required. Set CONFLUENCE_BEARER_TOKEN in .env file, "
                "export CONFLUENCE_BEARER_TOKEN environment variable, or use --token parameter."
            )
        
        # Raw data directory
        self.raw_data_dir = Path(__file__).parent.parent / 'raw_data'
        self.raw_data_dir.mkdir(exist_ok=True)
    
    def fetch_keys(self, plugin_keys: List[str], output_filename: str = None, group_name: str = None) -> Dict:
        """
        Fetch translation keys for given plugin keys.
        
        Args:
            plugin_keys: List of plugin keys to fetch (e.g., ['net.seibertmedia.confluence.linchpin-suite'])
            output_filename: Optional filename to save response. If None, auto-generates based on group name or plugin keys.
            group_name: Optional group name to use for filename (if provided, uses this instead of plugin keys).
        
        Returns:
            Dictionary containing API response with translation keys
        """
        # Build API URL with plugin keys
        api_url = f"{self.base_url}/rest/prototype/1/i18n.json"
        params = [f"pluginKeys={urllib.parse.quote(key)}" for key in plugin_keys]
        full_url = f"{api_url}?{'&'.join(params)}"
        
        print(f"Fetching keys from: {full_url[:100]}...")
        print(f"Plugin keys: {', '.join(plugin_keys)}")
        
        # Create request with bearer token
        req = urllib.request.Request(full_url)
        req.add_header('Authorization', f'Bearer {self.bearer_token}')
        req.add_header('Accept', 'application/json')
        req.add_header('User-Agent', 'Confluence-Translation-Fetcher/1.0')
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status != 200:
                    raise ValueError(f"API returned status {response.status}: {response.read().decode()}")
                
                data = json.loads(response.read().decode('utf-8'))
                
                # Save raw response
                if output_filename is None:
                    # Use group name if provided, otherwise generate from plugin keys
                    if group_name:
                        safe_name = group_name.replace(' ', '_').replace('.', '_')
                    else:
                        # Fallback: Generate filename from plugin keys
                        safe_name = '_'.join(plugin_keys[:3]).replace('.', '_')
                        if len(plugin_keys) > 3:
                            safe_name += f"_and_{len(plugin_keys) - 3}_more"
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_filename = f"{safe_name}_{timestamp}.json"
                
                output_path = self.raw_data_dir / output_filename
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"✓ Saved API response to: {output_path}")
                print(f"✓ Fetched {len(data)} translation keys")
                
                return data
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else "No error details"
            raise ValueError(f"HTTP Error {e.code}: {error_body}")
        except urllib.error.URLError as e:
            raise ValueError(f"URL Error: {e.reason}")
        except Exception as e:
            raise ValueError(f"Error fetching keys: {str(e)}")
    
    def fetch_single_plugin(self, plugin_key: str, output_filename: str = None) -> Dict:
        """Fetch keys for a single plugin."""
        return self.fetch_keys([plugin_key], output_filename)
    
    def fetch_multiple_plugins(self, plugin_keys: List[str], output_filename: str = None) -> Dict:
        """Fetch keys for multiple plugins in a single API call."""
        return self.fetch_keys(plugin_keys, output_filename)


def load_plugin_config(config_file: str = None) -> Dict:
    """
    Load plugin configuration from YAML file.
    
    Args:
        config_file: Path to config file (default: config/plugins.yaml)
    
    Returns:
        Dictionary with groups and plugins configuration
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML required for config file. Install with: pip install pyyaml")
    
    if config_file is None:
        config_file = Path(__file__).parent.parent / 'config' / 'plugins.yaml'
    else:
        config_file = Path(config_file)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def get_plugins_from_group(config: Dict, group_name: str) -> List[str]:
    """
    Get plugin keys from a named group.
    
    Args:
        config: Configuration dictionary
        group_name: Group name (e.g., 'linchpin-suite')
    
    Returns:
        List of plugin keys
    """
    groups = config.get('groups', {})
    if group_name not in groups:
        raise ValueError(f"Group '{group_name}' not found in config. Available groups: {list(groups.keys())}")
    
    return groups[group_name].get('plugins', [])


def get_all_plugins_from_groups(config: Dict) -> List[str]:
    """Get all plugin keys from all groups."""
    plugins = []
    groups = config.get('groups', {})
    for group_name, group_data in groups.items():
        plugins.extend(group_data.get('plugins', []))
    # Remove duplicates while preserving order
    seen = set()
    return [p for p in plugins if not (p in seen or seen.add(p))]


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch translation keys from Confluence REST API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch keys for a plugin group from config
  python3 src/fetch_confluence_keys.py --group linchpin-suite
  
  # Fetch keys for a single plugin
  python3 src/fetch_confluence_keys.py --plugin com.atlassian.confluence.plugins.confluence-wiki-editor
  
  # Fetch keys for multiple plugins
  python3 src/fetch_confluence_keys.py --plugins net.seibertmedia.confluence.linchpin-suite com.comalatech.workflows
  
  # Fetch all plugins from config groups
  python3 src/fetch_confluence_keys.py --all-groups
  
  # Specify output filename
  python3 src/fetch_confluence_keys.py --group linchpin-suite --output linchpin_keys.json
  
  # Use custom config file
  python3 src/fetch_confluence_keys.py --group linchpin-suite --config custom_plugins.yaml
  
  # Use .env file for URL and token:
  # CONFLUENCE_URL=https://yourdomain.com
  # CONFLUENCE_BEARER_TOKEN=your_token_here
        """
    )
    
    parser.add_argument('--url', help='Confluence base URL (default: from CONFLUENCE_URL env var)')
    parser.add_argument('--token', help='Bearer token (default: from CONFLUENCE_BEARER_TOKEN env var)')
    parser.add_argument('--plugin', help='Single plugin key to fetch')
    parser.add_argument('--plugins', nargs='+', help='Multiple plugin keys to fetch')
    parser.add_argument('--group', help='Plugin group name from config file (e.g., linchpin-suite)')
    parser.add_argument('--all-groups', action='store_true',
                       help='Fetch all plugins from all groups in config file')
    parser.add_argument('--config', help='Config file path (default: config/plugins.yaml)')
    parser.add_argument('--output', help='Output filename (default: auto-generated)')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Skip confirmation prompt and proceed automatically')
    
    args = parser.parse_args()
    
    # Determine which plugins to fetch
    plugin_keys = []
    
    # Track group name for filename generation
    group_name_for_file = None
    
    if args.all_groups:
        # Load all plugins from all groups
        config = load_plugin_config(args.config)
        plugin_keys = get_all_plugins_from_groups(config)
        if not plugin_keys:
            parser.error("No plugins found in config groups")
        print(f"Loading {len(plugin_keys)} plugins from all groups...")
        # For all groups, use "all_groups" as filename
        group_name_for_file = "all_groups"
    
    elif args.group:
        # Load plugins from specific group
        config = load_plugin_config(args.config)
        plugin_keys = get_plugins_from_group(config, args.group)
        group_info = config.get('groups', {}).get(args.group, {})
        print(f"Group: {group_info.get('name', args.group)}")
        print(f"Description: {group_info.get('description', 'N/A')}")
        print(f"Loading {len(plugin_keys)} plugins from group '{args.group}'...")
        # Use group name for filename
        group_name_for_file = args.group
    
    elif args.plugin:
        plugin_keys = [args.plugin]
    
    elif args.plugins:
        plugin_keys = args.plugins
    
    else:
        parser.error("Must specify one of: --plugin, --plugins, --group, or --all-groups")
    
    if not plugin_keys:
        parser.error("No plugins to fetch")
    
    try:
        fetcher = ConfluenceKeyFetcher(base_url=args.url, bearer_token=args.token)
        
        # For large groups, suggest splitting
        if len(plugin_keys) > 10:
            print(f"\nWarning: Fetching {len(plugin_keys)} plugins in one API call.")
            print("This may take a while or hit URL length limits.")
            if not args.yes:
                response = input("Continue? (y/n): ")
                if response.lower() != 'y':
                    print("Aborted.")
                    sys.exit(0)
            else:
                print("Proceeding automatically (--yes flag set)...")
        
        # Pass group name for filename generation
        data = fetcher.fetch_keys(plugin_keys, args.output, group_name=group_name_for_file)
        
        print(f"\n✓ Successfully fetched {len(data)} translation keys")
        print(f"  Raw data saved to: {fetcher.raw_data_dir}")
        
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

