# Justfile for Confluence Translations Project
# Run commands with: just <command>
# List all commands: just --list

# Default recipe - show available commands
default:
    @just --list

# Setup and installation
install:
    @echo "Installing dependencies..."
    pip install -r requirements.txt
    @echo "✓ Dependencies installed"

# Fetch translation keys from Confluence
fetch group *ARGS:
    @echo "Fetching translation keys for group: {{group}}"
    python src/fetch_confluence_keys.py --group {{group}} {{ARGS}}

fetch-plugin plugin *ARGS:
    @echo "Fetching keys for plugin: {{plugin}}"
    python src/fetch_confluence_keys.py --plugin {{plugin}} {{ARGS}}

fetch-all:
    @echo "Fetching all groups from config..."
    python src/fetch_confluence_keys.py --all-groups

# Import JSON files to database
import-group file group *ARGS:
    @echo "Importing group JSON file {{file}} for group: {{group}}"
    python src/import_group_json.py --file {{file}} --group {{group}} {{ARGS}}

# Import existing translations from JSON file (filters by target language)
import-translations file group *ARGS:
    @echo "Importing translations from {{file}} for group: {{group}}"
    python src/import_translations.py --file {{file}} --group {{group}} {{ARGS}}

# Alias for backward compatibility
import-russian file group *ARGS:
    @just import-translations {{file}} {{group}} {{ARGS}}

# Translate groups/plugins
translate group *ARGS:
    @echo "Translating group: {{group}}"
    python src/translate_group.py --group {{group}} {{ARGS}}


# Export translations
export group output *ARGS:
    @echo "Exporting group {{group}} to {{output}}"
    python src/export_group.py --group {{group}} --output {{output}} {{ARGS}}

# Export translations in chunks
export-chunks group output *ARGS:
    @echo "Exporting group {{group}} to chunks in {{output}}"
    python src/export_group_chunks.py --group {{group}} --output {{output}} {{ARGS}}

# Export translations (auto folder structure)
export-group group *ARGS:
    @echo "Exporting group {{group}} to output/{{group}}/"
    python src/export_group.py --group {{group}} --output {{group}}_ru_RU.properties {{ARGS}}

# Package as JAR (auto folder structure - uses group folder)
package-group group version *ARGS:
    @echo "Packaging {{group}} as JAR..."
    @python src/package_jar.py --properties output/{{group}}/{{group}}_ru_RU.properties --group {{group}} --output output/{{group}}/{{group}}-i18n-pack-{{version}}.jar --version {{version}} {{ARGS}}

# Package as JAR (manual paths)
package plugin properties version:
    @echo "Packaging {{plugin}} as JAR..."
    python src/package_jar.py --properties {{properties}} --plugin {{plugin}} --output output/{{plugin}}-i18n-pack-{{version}}.jar --version {{version}}

# Database operations
db-stats:
    @echo "Group statistics:"
    python -c "from src.db_group_manager import GroupDBManager; m = GroupDBManager(); groups = m.list_groups(); [print(f'{g[\"display_name\"]}: {m.get_statistics(g[\"group_key\"])[\"translated\"]}/{m.get_statistics(g[\"group_key\"])[\"total\"]} ({m.get_statistics(g[\"group_key\"])[\"percentage\"]:.1f}%)') for g in groups]"

db-list:
    @echo "Registered groups:"
    python -c "from src.db_group_manager import GroupDBManager; m = GroupDBManager(); [print(f'{g[\"display_name\"]} ({g[\"group_key\"]}) -> {g[\"table_name\"]}') for g in m.list_groups()]"

# Utilities
unicode-convert file mode:
    @echo "Converting {{file}} (mode: {{mode}})"
    python src/unicode_converter.py -f {{file}} --properties -m {{mode}}

# Complete workflow for a group (fetch, import, translate, export, package)
workflow-group group version *ARGS:
    @echo "Complete workflow for group: {{group}}"
    @echo "1. Fetching keys..."
    python src/fetch_confluence_keys.py --group {{group}} --yes
    @echo "2. Finding latest JSON file..."
    @ls -t raw_data/{{group}}_*.json 2>/dev/null | head -1 | xargs -I {} python src/import_group_json.py --file {} --group {{group}}
    @echo "3. Translating..."
    python src/translate_group.py --group {{group}} {{ARGS}}
    @echo "4. Exporting..."
    python src/export_group.py --group {{group}} --output {{group}}_ru_RU.properties
    @echo "5. Packaging..."
    @python src/package_jar.py --properties output/{{group}}/{{group}}_ru_RU.properties --group {{group}} --output output/{{group}}/{{group}}-i18n-pack-{{version}}.jar --version {{version}}
    @echo "✓ Workflow complete for {{group}}!"

# Complete workflow for all groups
workflow-all version *ARGS:
    @echo "Running complete workflow for all groups..."
    @python -c "import yaml, subprocess, sys; config = yaml.safe_load(open('config/plugins.yaml')); groups = list(config.get('groups', {}).keys()); [subprocess.run(['just', 'workflow-group', g, '{{version}}'] + '{{ARGS}}'.split(), check=False) or None for g in groups]"
    @echo "✓ All groups processed!"

# Linchpin Suite complete workflow (convenience alias)
workflow-linchpin:
    @echo "Complete workflow for Linchpin Suite:"
    @just workflow-group linchpin-suite 1.0.0

# Check environment
check-env:
    @echo "Checking environment..."
    @python -c "from dotenv import load_dotenv; from pathlib import Path; import os; load_dotenv('.env'); print('✓ .env loaded'); print(f'CONFLUENCE_URL: {\"SET\" if os.getenv(\"CONFLUENCE_URL\") else \"NOT SET\"}'); print(f'CONFLUENCE_BEARER_TOKEN: {\"SET\" if os.getenv(\"CONFLUENCE_BEARER_TOKEN\") else \"NOT SET\"}'); print(f'DEEPL_API_KEY: {\"SET\" if os.getenv(\"DEEPL_API_KEY\") else \"NOT SET\"}')"

