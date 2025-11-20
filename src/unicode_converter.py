#!/usr/bin/env python3
"""
Unicode to Cyrillic converter for translation files.
Converts between Unicode escape sequences (\u0413) and readable Cyrillic text.
"""

import sys
import re
import argparse
import json


def unicode_to_cyrillic(text):
    """Convert Unicode escape sequences to Cyrillic characters."""
    def replace_unicode(match):
        code_point = int(match.group(1), 16)
        return chr(code_point)
    
    # Replace \uXXXX patterns
    result = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
    return result


def cyrillic_to_unicode(text):
    """Convert Cyrillic characters to Unicode escape sequences."""
    result = []
    for char in text:
        code = ord(char)
        if code > 127:  # Non-ASCII character
            result.append(f'\\u{code:04X}')
        else:
            result.append(char)
    return ''.join(result)


def process_file(input_file, output_file=None, mode='to_cyrillic', encoding='utf-8'):
    """Process a file and convert Unicode escapes."""
    try:
        with open(input_file, 'r', encoding=encoding) as f:
            content = f.read()
        
        if mode == 'to_cyrillic':
            converted = unicode_to_cyrillic(content)
        else:  # to_unicode
            converted = cyrillic_to_unicode(content)
        
        if output_file:
            with open(output_file, 'w', encoding=encoding) as f:
                f.write(converted)
            print(f"Converted file saved to: {output_file}")
        else:
            print(converted)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def process_properties_file(input_file, output_file=None, mode='to_cyrillic'):
    """Process Java properties file, converting values only."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        converted_lines = []
        for line in lines:
            if '=' in line and not line.strip().startswith('#'):
                key, value = line.split('=', 1)
                # Process only the value part
                if mode == 'to_cyrillic':
                    converted_value = unicode_to_cyrillic(value)
                else:
                    converted_value = cyrillic_to_unicode(value)
                converted_lines.append(f"{key}={converted_value}")
            else:
                converted_lines.append(line)
        
        result = ''.join(converted_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"Converted properties file saved to: {output_file}")
        else:
            print(result)
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Convert between Unicode escapes and Cyrillic text',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert Unicode escapes to Cyrillic (readable)
  python3 unicode_converter.py -f file.properties -m to_cyrillic
  
  # Convert Cyrillic to Unicode escapes (for properties file)
  python3 unicode_converter.py -f file.properties -m to_unicode -o output.properties
  
  # Process properties file (values only)
  python3 unicode_converter.py -f i18n_ru_RU.properties -m to_cyrillic --properties
  
  # Interactive mode
  python3 unicode_converter.py -i
        """
    )
    
    parser.add_argument('-f', '--file', help='Input file to process')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    parser.add_argument('-m', '--mode', choices=['to_cyrillic', 'to_unicode'], 
                       default='to_cyrillic',
                       help='Conversion mode: to_cyrillic (readable) or to_unicode (escapes)')
    parser.add_argument('-i', '--interactive', action='store_true',
                       help='Interactive mode')
    parser.add_argument('--properties', action='store_true',
                       help='Process as Java properties file (convert values only)')
    parser.add_argument('--encoding', default='utf-8',
                       help='File encoding (default: utf-8)')
    
    args = parser.parse_args()
    
    if args.interactive:
        print("Unicode ↔ Cyrillic Converter (Interactive Mode)")
        print("Type 'exit' to quit, 'help' for examples\n")
        
        while True:
            try:
                text = input("Enter text: ").strip()
                if text.lower() == 'exit':
                    break
                if text.lower() == 'help':
                    print("\nExamples:")
                    print("  Input: \\u0413\\u043B\\u043E\\u0431\\u0430\\u043B\\u044C\\u043D\\u044B\\u0435")
                    print("  Output: Глобальные")
                    print("  Input: Глобальные")
                    print("  Output: \\u0413\\u043B\\u043E\\u0431\\u0430\\u043B\\u044C\\u043D\\u044B\\u0435\n")
                    continue
                
                if not text:
                    continue
                
                # Auto-detect: if contains \u, convert to Cyrillic, else to Unicode
                if '\\u' in text:
                    result = unicode_to_cyrillic(text)
                    print(f"Cyrillic: {result}\n")
                else:
                    result = cyrillic_to_unicode(text)
                    print(f"Unicode: {result}\n")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}\n")
    
    elif args.file:
        if args.properties:
            process_properties_file(args.file, args.output, args.mode)
        else:
            process_file(args.file, args.output, args.mode, args.encoding)
    else:
        # Read from stdin
        try:
            text = sys.stdin.read()
            if args.mode == 'to_cyrillic':
                print(unicode_to_cyrillic(text))
            else:
                print(cyrillic_to_unicode(text))
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()

