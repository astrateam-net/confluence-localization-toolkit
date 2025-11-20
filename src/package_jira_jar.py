#!/usr/bin/env python3
"""
Package Jira plugin JAR with Russian translation.
Rebuilds JAR by extracting original, adding Russian properties file,
and keeping everything else unchanged (no vendor changes, no XML modifications).
"""

import sys
import os
import shutil
import zipfile
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
import argparse

def get_plugin_version(extract_dir: Path) -> str:
    """
    Extract plugin version from atlassian-plugin.xml.
    
    Args:
        extract_dir: Path to extracted JAR directory
        
    Returns:
        Plugin version string (e.g., "8.58.2")
    """
    plugin_xml = extract_dir / 'atlassian-plugin.xml'
    if not plugin_xml.exists():
        return "1.0.0"  # Default fallback
    
    try:
        tree = ET.parse(plugin_xml)
        root = tree.getroot()
        # Find version in plugin-info/version
        plugin_info = root.find('.//plugin-info')
        if plugin_info is not None:
            version_elem = plugin_info.find('version')
            if version_elem is not None and version_elem.text:
                return version_elem.text.strip()
    except Exception as e:
        print(f"Warning: Could not parse version from atlassian-plugin.xml: {e}", file=sys.stderr)
    
    return "1.0.0"  # Default fallback


def package_jira_jar(original_jar: str, russian_properties: str, output_jar: str = None):
    """
    Rebuild Jira plugin JAR with Russian translation.
    
    This method:
    1. Extracts the original JAR to a temporary directory
    2. Adds the Russian properties file to l10n/ folder
    3. Repackages everything back into a new JAR
    4. Does NOT modify atlassian-plugin.xml or any other files
    5. Preserves all original plugin metadata (vendor, version, etc.)
    
    Unlike Confluence plugins (which create separate language pack JARs),
    this rebuilds the original plugin JAR with the new translation file.
    
    Args:
        original_jar: Path to original JAR file
        russian_properties: Path to Russian properties file (message_ru_RU.properties)
        output_jar: Path to output JAR file (optional, auto-generated if not provided)
    """
    original_path = Path(original_jar)
    properties_path = Path(russian_properties)
    
    if not original_path.exists():
        raise FileNotFoundError(f"Original JAR not found: {original_jar}")
    
    if not properties_path.exists():
        raise FileNotFoundError(f"Russian properties file not found: {russian_properties}")
    
    # Verify properties filename format
    props_filename = properties_path.name
    if not props_filename.startswith('message_') or not props_filename.endswith('.properties'):
        print(f"Warning: Properties filename '{props_filename}' doesn't match expected format 'message_XX_XX.properties'")
    
    # Create temporary directory for extraction
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        extract_dir = temp_path / 'extracted'
        extract_dir.mkdir()
        
        print(f"Extracting original JAR: {original_jar}")
        # Extract original JAR
        with zipfile.ZipFile(original_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Get plugin version from atlassian-plugin.xml
        plugin_version = get_plugin_version(extract_dir)
        
        # Generate output filename if not provided
        if output_jar is None:
            original_name = original_path.stem  # e.g., "plugin" or "bigpicture-enterprise"
            output_jar = f"{original_name}-ru-{plugin_version}.jar"
        
        output_path = Path(output_jar)
        
        # Determine properties file location in JAR
        # Check if l10n directory exists
        l10n_dir = extract_dir / 'l10n'
        if not l10n_dir.exists():
            # Try to find where message_XX_XX.properties files are located
            for props_file in extract_dir.rglob('message_*.properties'):
                props_dir = props_file.parent
                print(f"Found existing properties file: {props_file.relative_to(extract_dir)}")
                # Copy Russian file to same location
                target_path = props_dir / props_filename
                shutil.copy2(properties_path, target_path)
                print(f"Added Russian properties: {target_path.relative_to(extract_dir)}")
                break
            else:
                # If no existing message_*.properties found, create l10n directory
                l10n_dir.mkdir()
                target_path = l10n_dir / props_filename
                shutil.copy2(properties_path, target_path)
                print(f"Created l10n directory and added Russian properties: {target_path.relative_to(extract_dir)}")
        else:
            # l10n directory exists, add Russian file there
            target_path = l10n_dir / props_filename
            shutil.copy2(properties_path, target_path)
            print(f"Added Russian properties: {target_path.relative_to(extract_dir)}")
        
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create new JAR with all extracted files (including new Russian properties)
        print(f"Creating new JAR: {output_jar}")
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for file_path in extract_dir.rglob('*'):
                if file_path.is_file():
                    arc_name = file_path.relative_to(extract_dir)
                    zip_out.write(file_path, arc_name)
        
        # Verify JAR was created
        if output_path.exists():
            size_kb = output_path.stat().st_size / 1024
            print(f"✓ Successfully created JAR: {output_jar}")
            print(f"  Plugin version: {plugin_version}")
            print(f"  Size: {size_kb:.1f} KB")
            print(f"  Added: {props_filename}")
            print(f"  Location in JAR: {target_path.relative_to(extract_dir)}")
            print(f"  Note: Original plugin unchanged, only translation file added")
        else:
            raise RuntimeError(f"Failed to create JAR: {output_jar}")
    
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description='Rebuild Jira plugin JAR with Russian translation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rebuild BigPicture JAR with Russian translation
  python src/package_jira_jar.py \\
    --original temp_jira_plugin/plugin.jar \\
    --properties output/bigpicture/message_ru_RU.properties \\
    --output output/bigpicture/bigpicture-ru-i18n-pack.jar
  
Notes:
  - Original JAR is not modified
  - Only adds Russian properties file (l10n/message_ru_RU.properties)
  - Does NOT modify atlassian-plugin.xml (no vendor changes, no language tags)
  - Keeps all other files unchanged
        """
    )
    
    parser.add_argument('--original', '-o', required=True,
                       help='Path to original JAR file')
    parser.add_argument('--properties', '-p', required=True,
                       help='Path to Russian properties file (message_ru_RU.properties)')
    parser.add_argument('--output', '-out', default=None,
                       help='Path to output JAR file (optional, auto-generated from plugin version if not provided)')
    
    args = parser.parse_args()
    
    try:
        package_jira_jar(args.original, args.properties, args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()



