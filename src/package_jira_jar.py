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

try:
    from locale_utils import locale_to_jira_format
except ImportError:
    def locale_to_jira_format(locale: str = None) -> str:
        """Fallback: convert locale format from ru_RU to ru-RU."""
        if locale is None:
            locale = os.getenv('TARGET_LANGUAGE', 'ru_RU').strip()
        return locale.replace('_', '-')

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


def package_jira_jar(original_jar: str, russian_properties: str, output_jar: str = None, 
                     admin_properties: str = None):
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
    
    # Verify properties filename format and convert to Jira format if needed
    props_filename = properties_path.name
    if not props_filename.startswith('message_') or not props_filename.endswith('.properties'):
        print(f"Warning: Properties filename '{props_filename}' doesn't match expected format 'message_XX_XX.properties'")
    
    # Convert locale format to Jira format (ru_RU -> ru-RU)
    # Jira uses hyphens in locale filenames (e.g., message_en-US.properties)
    if '_' in props_filename and props_filename.startswith('message_'):
        # Extract locale part (e.g., "ru_RU" from "message_ru_RU.properties")
        parts = props_filename.replace('message_', '').replace('.properties', '')
        if '_' in parts:
            # Convert to Jira format (hyphen)
            locale_part = parts.split('_')
            if len(locale_part) >= 2:
                jira_locale = '-'.join(locale_part)
                props_filename = f"message_{jira_locale}.properties"
                print(f"Converting locale format to Jira format: {properties_path.name} -> {props_filename}")
    
    # Handle admin panel properties file (frontend translations)
    admin_path = None
    admin_filename = None
    if admin_properties:
        admin_path = Path(admin_properties)
        if not admin_path.exists():
            print(f"Warning: Admin properties file not found: {admin_properties}")
            admin_path = None
        else:
            admin_filename = admin_path.name
            # Admin panel uses underscore format (bigpicture_ru_RU.properties)
            # Keep as-is, no conversion needed
            print(f"Admin panel properties file: {admin_filename}")
    
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
            
            # Also add underscore format (ru_RU) for Java locale compatibility
            # Jira might detect Russian locale as ru_RU (Java format) instead of ru-RU (file format)
            if 'ru-RU' in props_filename:
                # Add underscore version (ru_RU) for Java locale format
                underscore_filename = props_filename.replace('ru-RU', 'ru_RU')
                underscore_path = l10n_dir / underscore_filename
                if underscore_path != target_path:  # Only copy if different
                    shutil.copy2(properties_path, underscore_path)
                    print(f"Added Russian properties (Java locale format): {underscore_path.relative_to(extract_dir)}")
        
        # Add admin panel frontend translation file if provided
        admin_target_path = None
        if admin_path and admin_filename:
            admin_i18n_dir = extract_dir / 'application' / 'dist' / 'util' / 'assets' / 'i18n' / 'bigpicture'
            if not admin_i18n_dir.exists():
                admin_i18n_dir.mkdir(parents=True, exist_ok=True)
                print(f"Created admin i18n directory: {admin_i18n_dir.relative_to(extract_dir)}")
            
            # Add underscore format (ru_RU) - current format
            admin_target_path = admin_i18n_dir / admin_filename
            shutil.copy2(admin_path, admin_target_path)
            print(f"Added admin panel Russian properties: {admin_target_path.relative_to(extract_dir)}")
            
            # Also add hyphen format (ru-RU) for Jira locale compatibility
            # Jira uses ru-RU (hyphen) in script URLs, so JavaScript may request hyphen format
            if 'ru_RU' in admin_filename:
                hyphen_filename = admin_filename.replace('ru_RU', 'ru-RU')
                hyphen_path = admin_i18n_dir / hyphen_filename
                if hyphen_path != admin_target_path:  # Only copy if different
                    shutil.copy2(admin_path, hyphen_path)
                    print(f"Added admin panel Russian properties (hyphen format): {hyphen_path.relative_to(extract_dir)}")
        
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
            if admin_target_path:
                print(f"  Added admin panel: {admin_filename}")
                print(f"  Admin panel location: {admin_target_path.relative_to(extract_dir)}")
            print(f"  Note: Original plugin unchanged, only translation files added")
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
    parser.add_argument('--admin-properties', '-a', default=None,
                       help='Path to admin panel Russian properties file (bigpicture_ru_RU.properties) - optional')
    parser.add_argument('--output', '-out', default=None,
                       help='Path to output JAR file (optional, auto-generated from plugin version if not provided)')
    
    args = parser.parse_args()
    
    try:
        package_jira_jar(args.original, args.properties, args.output, args.admin_properties)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()



