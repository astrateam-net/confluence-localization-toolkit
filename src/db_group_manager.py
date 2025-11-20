#!/usr/bin/env python3
"""
Group-based database manager.
Creates and manages separate tables for each translation group (e.g., "Linchpin Suite").
All keys from plugins in a group are stored in the same table.
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager
from pathlib import Path


class GroupDBManager:
    """Manages group-based translation tables in SQLite database."""
    
    def __init__(self, db_path: str = "db/translations.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """Initialize database with group registry table."""
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Group registry table - tracks which groups have their own tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS group_registry (
                    group_key TEXT PRIMARY KEY,
                    table_name TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_table_name(self, group_key: str) -> str:
        """
        Get or create table name for a group.
        Converts group key to safe table name.
        """
        # Convert group key to table name (e.g., linchpin-suite -> linchpin_suite)
        table_name = group_key.replace('-', '_').replace('.', '_')
        
        # Ensure it's registered
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT display_name FROM group_registry WHERE group_key = ?
            """, (group_key,))
            row = cursor.fetchone()
            if not row:
                # Default display name from group_key
                display_name = group_key.replace('-', ' ').replace('_', ' ').title()
                cursor.execute("""
                    INSERT OR IGNORE INTO group_registry (group_key, table_name, display_name)
                    VALUES (?, ?, ?)
                """, (group_key, table_name, display_name))
        
        return table_name
    
    def create_group_table(self, group_key: str, display_name: str = None, description: str = None):
        """
        Create a translation table for a specific group.
        
        Args:
            group_key: Group key (e.g., 'linchpin-suite')
            display_name: Optional display name (e.g., 'Linchpin Suite')
            description: Optional description
        """
        table_name = self.get_table_name(group_key)
        
        if not display_name:
            display_name = group_key.replace('-', ' ').replace('_', ' ').title()
        
        with self.connection() as conn:
            cursor = conn.cursor()
            
            # Create group-specific table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    key TEXT PRIMARY KEY,
                    original_text TEXT NOT NULL,
                    translated_text TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    translation_method TEXT,
                    plugin_key TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Create indexes
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_status 
                ON {table_name}(status)
            """)
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_plugin 
                ON {table_name}(plugin_key)
            """)
            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_updated 
                ON {table_name}(updated_at)
            """)
            
            # Register group
            cursor.execute("""
                INSERT OR REPLACE INTO group_registry 
                (group_key, table_name, display_name, description, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (group_key, table_name, display_name, description, datetime.now().isoformat()))
            
            conn.commit()
        
        return table_name
    
    def import_json_to_group_table(self, json_data: Dict, group_key: str, display_name: str = None, description: str = None):
        """
        Import translation keys from JSON into group-specific table.
        
        Args:
            json_data: Dictionary with translation keys (key -> value)
            group_key: Group key to identify the table
            display_name: Optional display name for the group
            description: Optional description
        """
        table_name = self.create_group_table(group_key, display_name, description)
        
        imported = 0
        updated = 0
        protected = 0  # Count of existing translations that were protected (not overwritten)
        
        with self.connection() as conn:
            cursor = conn.cursor()
            
            for key, original_text in json_data.items():
                # Try to extract plugin key from translation key
                plugin_key = None
                if '.' in key:
                    # Try to match common plugin key patterns
                    parts = key.split('.')
                    # Common pattern: net.seibertmedia.confluence.plugin-name.key
                    if len(parts) >= 4 and parts[0] == 'net' and parts[1] == 'seibertmedia':
                        plugin_key = '.'.join(parts[:4])
                    # Fallback: first 3-4 parts
                    elif len(parts) >= 3:
                        plugin_key = '.'.join(parts[:3])
                
                # Check if key already exists and if it has a Russian translation
                cursor.execute(f"""
                    SELECT key, translated_text FROM {table_name} 
                    WHERE key = ?
                """, (key,))
                existing_row = cursor.fetchone()
                
                if existing_row:
                    # Key exists - check if it has a Russian translation
                    has_translation = existing_row['translated_text'] is not None and existing_row['translated_text'].strip() != ''
                    
                    if has_translation:
                        # Skip this row - already has Russian translation, don't overwrite
                        protected += 1
                        continue
                    else:
                        # Update existing row that has no translation yet
                        # Only update original_text and plugin_key, preserve status and other fields
                        cursor.execute(f"""
                            UPDATE {table_name} 
                            SET original_text = ?, plugin_key = COALESCE(?, plugin_key), updated_at = ?
                            WHERE key = ?
                        """, (original_text, plugin_key, datetime.now().isoformat(), key))
                        updated += 1
                else:
                    # Insert new row
                    cursor.execute(f"""
                        INSERT INTO {table_name} 
                        (key, original_text, plugin_key, status, created_at, updated_at)
                        VALUES (?, ?, ?, 'pending', ?, ?)
                    """, (key, original_text, plugin_key, datetime.now().isoformat(), datetime.now().isoformat()))
                    imported += 1
        
        return imported, updated, protected
    
    def get_pending_translations(self, group_key: str, limit: int = None) -> List[Dict]:
        """Get pending and error translations for a group (keys that need translation)."""
        table_name = self.get_table_name(group_key)
        
        with self.connection() as conn:
            cursor = conn.cursor()
            # Get both 'pending' (not yet translated) and 'error' (failed translation) keys
            query = f"SELECT * FROM {table_name} WHERE status IN ('pending', 'error') ORDER BY key"
            if limit:
                query += f" LIMIT {limit}"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_translation(self, group_key: str, key: str, translated_text: str,
                          translation_method: str = None, status: str = 'translated'):
        """Update translation for a key in group table."""
        table_name = self.get_table_name(group_key)
        
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE {table_name} 
                SET translated_text = ?, translation_method = ?, status = ?, updated_at = ?
                WHERE key = ?
            """, (translated_text, translation_method, status, datetime.now().isoformat(), key))
    
    def get_statistics(self, group_key: str) -> Dict:
        """Get translation statistics for a group."""
        table_name = self.get_table_name(group_key)
        
        with self.connection() as conn:
            cursor = conn.cursor()
            
            try:
                total = cursor.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                translated = cursor.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE status = 'translated'"
                ).fetchone()[0]
                pending = cursor.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE status IN ('pending', 'error')"
                ).fetchone()[0]
                error_count = cursor.execute(
                    f"SELECT COUNT(*) FROM {table_name} WHERE status = 'error'"
                ).fetchone()[0]
                
                return {
                    'group_key': group_key,
                    'total': total,
                    'translated': translated,
                    'pending': pending,
                    'error': error_count,
                    'percentage': (translated / total * 100) if total > 0 else 0
                }
            except sqlite3.OperationalError:
                # Table doesn't exist
                return {
                    'group_key': group_key,
                    'total': 0,
                    'translated': 0,
                    'pending': 0,
                    'percentage': 0
                }
    
    def list_groups(self) -> List[Dict]:
        """List all registered groups."""
        with self.connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT group_key, table_name, display_name, description, created_at
                FROM group_registry
                ORDER BY display_name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def export_group_translations(self, group_key: str, output_file: str, 
                                  only_translated: bool = True):
        """Export group translations to JSON format."""
        table_name = self.get_table_name(group_key)
        
        with self.connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT key, translated_text FROM {table_name} WHERE translated_text IS NOT NULL"
            if only_translated:
                query += " AND status = 'translated'"
            cursor.execute(query)
            
            translations = {row['key']: row['translated_text'] for row in cursor.fetchall()}
            
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(translations, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    # Example usage
    manager = GroupDBManager()
    groups = manager.list_groups()
    print("Registered groups:")
    for group in groups:
        stats = manager.get_statistics(group['group_key'])
        print(f"  {group['display_name']}: {stats['translated']}/{stats['total']} "
              f"({stats['percentage']:.1f}%)")

