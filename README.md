# Confluence Translation Project

## Overview

This project translates Confluence plugin user interface elements from English to Russian using **DeepL API** or **Google Cloud Translation API**. The translations are packaged as Confluence plugin JAR files that can be installed to localize plugin interfaces.

The project uses a **group-based** approach where related plugins are organized into groups (e.g., "Linchpin Suite"). Each group gets its own database table and produces a single JAR package for installation.

## Features

- **Multiple Translation Services**: Support for DeepL and Google Cloud Translation (v2 or v3)
- **Group-Based Organization**: Organize plugins into logical groups for easier management
- **Translation Protection**: Existing Russian translations are never overwritten
- **Resumable Translation**: Interrupt and resume translation at any time
- **Batch Processing**: Efficient batch translation with rate limit handling
- **Unicode Escaping**: Automatic Cyrillic to Unicode conversion for properties files
- **JAR Packaging**: Automatic JAR package creation for Confluence installation

## Project Structure

```
confluence_translations/
├── src/                          # Python scripts
│   ├── fetch_confluence_keys.py  # Fetch keys from Confluence API
│   ├── import_group_json.py      # Import group JSON to database
│   ├── db_group_manager.py       # Group-based database manager
│   ├── translate_group.py        # Translate group tables
│   ├── export_group.py           # Export translations with Unicode conversion
│   ├── package_jar.py            # Create JAR packages
│   ├── translation_processor.py  # TranslationProcessor class (multi-language support)
│   └── unicode_converter.py      # Unicode ↔ Cyrillic converter utility
├── config/                       # Configuration files
│   └── plugins.yaml              # Plugin groups configuration
├── raw_data/                     # Raw API responses (JSON files)
│   └── {group}_{timestamp}.json  # Fetched translation keys
├── db/                           # Database files (SQLite)
│   └── translations.db           # Group-based translation database
├── output/                       # Generated files
│   ├── *.properties             # Generated properties files
│   └── *.jar                    # Generated JAR packages
├── docs/                         # Documentation
│   ├── GOOGLE_API_VERSION_USAGE.md
│   ├── GOOGLE_CLOUD_SETUP.md
│   ├── TRANSLATION_ALTERNATIVES.md
│   └── ...
├── scripts/                      # Utility scripts
│   ├── test_deepl_api.sh        # Test DeepL API connectivity
│   ├── test_google_translate.py # Test Google Cloud Translation API
│   └── README.md                # Scripts documentation
├── Justfile                      # Command runner (just commands)
├── mise.toml                     # Tool version management
└── requirements.txt              # Python dependencies
```

## Key Concepts

### Groups

Plugins are organized into **groups** defined in `config/plugins.yaml`. A group represents a collection of related plugins that will be packaged together. For example:

- **linchpin-suite**: Contains all 25 Linchpin Suite plugins
- Each group gets its own database table (e.g., `linchpin_suite`)
- Each group produces one JAR package (e.g., `linchpin-suite-pack-1.0.0.jar`)

### Database Tables

- **group_registry**: Tracks all registered groups
- **{group}_table**: One table per group containing all translation keys from all plugins in that group

Each row in a group table contains:
- `key`: Translation key
- `original_text`: English text
- `translated_text`: Russian translation (if translated)
- `status`: 'pending', 'translated', or 'error'
- `plugin_key`: Which plugin this key belongs to (for reference)

### Translation Protection

When importing keys, **existing Russian translations are never overwritten**. If a key already has a `translated_text`, it is skipped during import. This allows you to:

- Re-fetch keys when translations are updated in Confluence
- Update English text without losing existing Russian translations
- Safely re-import without worrying about losing work

## Setup

### Prerequisites

1. **Python 3.8+**
2. **mise**: Tool version manager (installs Python and just)
3. **Translation API**: Choose one:
   - **DeepL API**: Get one at https://www.deepl.com/pro-api (recommended for quality)
   - **Google Cloud Translation API**: Set up at https://console.cloud.google.com/apis/library/translate.googleapis.com
     - Create a service account and download JSON key file
     - Choose "Application data" when creating credentials
     - Supports **v2 (Basic)** or **v3 (Advanced)** - same pricing, v3 recommended for new projects
4. **Confluence Access**: Bearer token for fetching translation keys

### Installation

```bash
# Clone/navigate to project
cd confluence_translations

# Trust mise configuration
mise trust

# Install Python and tools (via mise)
mise install

# Install Python dependencies
just install

# Or manually:
# source venv/bin/activate
# pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```bash
# Translation API Configuration - Choose ONE:

# Option 1: DeepL API (default, recommended for quality)
DEEPL_API_KEY=your_deepl_api_key_here

# Option 2: Google Cloud Translation API (alternative)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your-service-account-key.json
GOOGLE_TRANSLATE_API_VERSION=v3  # 'v2' (Basic) or 'v3' (Advanced). Default: v3 (recommended)
TRANSLATION_SERVICE=google  # Optional: force Google, or 'auto' to auto-detect
GOOGLE_CLOUD_PROJECT=your-project-id  # Optional: for v3, auto-detected from credentials JSON

# Optional: Proxy configuration (if your IP is blocked)
# Format: http://user:pass@host:port or http://host:port
# DEEPL_PROXY=http://proxy.example.com:8080
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=http://proxy.example.com:8080

# Confluence API Configuration
CONFLUENCE_URL=https://yourdomain.com
CONFLUENCE_BEARER_TOKEN=your_bearer_token_here

# Target Language (optional, defaults to Russian)
TARGET_LANGUAGE=ru_RU  # Examples: ru_RU, de_DE, fr_FR, es_ES, it_IT, etc.
```

**Translation Service Selection:**
- Set `TRANSLATION_SERVICE=deepl` to force DeepL
- Set `TRANSLATION_SERVICE=google` to force Google Cloud Translation
- Set `TRANSLATION_SERVICE=auto` (default) to auto-detect based on available credentials

**Target Language:**
- Set `TARGET_LANGUAGE=ru_RU` for Russian (default)
- Set `TARGET_LANGUAGE=de_DE` for German
- Set `TARGET_LANGUAGE=fr_FR` for French
- Supports any locale code: `es_ES`, `it_IT`, `pt_BR`, `ja_JP`, `ko_KR`, `zh_CN`, `zh_TW`, `pl_PL`, `nl_NL`, `sv_SE`, `fi_FI`, `uk_UA`, etc.

**Google Cloud Translation API Version:**
- **v3 (Advanced)**: Recommended for new projects. Same price as v2, access to advanced features.
- **v2 (Basic)**: Simpler, higher rate limits (300k req/min vs 6k for v3).
- Set via `GOOGLE_TRANSLATE_API_VERSION=v2` or `v3` in `.env`
- Or use command-line: `just translate linchpin-suite --google-api-version v3`

See `docs/GOOGLE_API_VERSION_USAGE.md` for detailed comparison.

## Quick Start

### Complete Workflow for a Group

```bash
# Complete workflow for linchpin-suite group
just workflow-group linchpin-suite

# Or step by step:
# 1. Fetch keys
just fetch linchpin-suite --yes

# 2. Import to database (automatically finds latest JSON)
just import-group "raw_data/linchpin-suite_*.json" linchpin-suite

# 3. Translate pending keys
just translate linchpin-suite

# With Google Cloud Translation v3:
just translate linchpin-suite --google-api-version v3

# 4. Export translations
just export linchpin-suite output/linchpin-suite_ru_RU.properties

# 5. Package as JAR (optional)
just package linchpin-suite output/linchpin-suite_ru_RU.properties 1.0.0
```

## Workflow Details

### 1. Fetch Translation Keys

Fetch all translation keys for a group from Confluence API:

```bash
just fetch <group-name>
# Example: just fetch linchpin-suite --yes
```

- Reads plugin list from `config/plugins.yaml`
- Makes API request to Confluence
- Saves JSON to `raw_data/{group}_{timestamp}.json`
- File is named after the group, not individual plugins

**Configuration**: Set `CONFLUENCE_URL` and `CONFLUENCE_BEARER_TOKEN` in `.env`

### 2. Import to Database

Import fetched JSON into a group-based database table:

```bash
just import-group <json-file> <group-name>
# Example: just import-group raw_data/linchpin-suite_20251120_004135.json linchpin-suite
```

- Creates table if it doesn't exist (e.g., `linchpin_suite`)
- Imports all keys from all plugins in the group
- **Protects existing translations**: Won't overwrite rows that already have Russian text
- Updates English text if keys changed in Confluence

### 3. Translate

Translate pending keys using DeepL or Google Cloud Translation API:

```bash
# Using default service (auto-detected)
just translate <group-name>

# Force DeepL
TRANSLATION_SERVICE=deepl just translate <group-name>

# Force Google Cloud Translation v3
just translate <group-name> --google-api-version v3

# Force Google Cloud Translation v2
just translate <group-name> --google-api-version v2
```

- Translates only keys with `status='pending'` (no Russian translation yet)
- Automatically handles rate limiting and retries
- Batch processing (100 keys per batch) with pauses on high load
- Can be interrupted and resumed

**Configuration**: Set translation API credentials in `.env` (see Setup section)

### 4. Export Translations

Export translated keys to Java properties file:

```bash
just export-group <group-name>
# Example: just export-group linchpin-suite
```

- Only exports keys with `status='translated'`
- Automatically converts Cyrillic to Unicode escapes (`\uXXXX` format) for Cyrillic languages
- Output file: `output/{group-name}/{group-name}_{TARGET_LANGUAGE}.properties`
- Uses `TARGET_LANGUAGE` environment variable (defaults to `ru_RU`)

**Manual export** (specify custom output file):
```bash
just export <group-name> <output-file>
# Example: just export linchpin-suite output/linchpin-suite_ru_RU.properties
```

### 5. Package as JAR

Create Confluence plugin JAR package:

```bash
just package-group <group-name> <version>
# Example: just package-group linchpin-suite 1.0.0
```

- Automatically finds properties file: `output/{group-name}/{group-name}_{TARGET_LANGUAGE}.properties`
- Output JAR: `output/{group-name}/{group-name}-i18n-pack-{version}.jar`

**Manual package** (specify custom paths):
```bash
just package <group-name> <properties-file> <version>
# Example: just package linchpin-suite output/linchpin-suite_ru_RU.properties 1.0.0
```

**JAR Contents:**
- `atlassian-plugin.xml` (plugin descriptor)
- Properties file in correct path structure: `net/seibertmedia/confluence/language/i18n/i18n_{locale}.properties`

## Configuration

### Plugin Groups (`config/plugins.yaml`)

Define groups and their plugins:

```yaml
groups:
  linchpin-suite:
    name: "Linchpin Suite"
    description: "All Linchpin Suite plugins"
    plugins:
      - net.seibertmedia.confluence.language-manager
      - net.seibertmedia.confluence.linchpin-connector
      # ... more plugins
```

### Adding a New Group

1. Edit `config/plugins.yaml`
2. Add a new group with its plugins
3. Fetch: `just fetch <new-group>`
4. Import: `just import-group <file> <new-group>`
5. Translate: `just translate <new-group>`

## Available Commands

```bash
# Fetch keys
just fetch <group>              # Fetch keys for a group
just fetch-all                  # Fetch all groups from config

# Import to database
just import-group <file> <group>  # Import JSON to group table

# Translate
just translate <group>          # Translate pending keys
just translate <group> --google-api-version v3  # Use Google v3
just translate <group> --google-api-version v2  # Use Google v2

# Export
just export-group <group>       # Export to properties file (auto path)
just export <group> <output>    # Export to custom output file

# Package
just package-group <group> <version>  # Create JAR (auto path)
just package <group> <properties> <version>  # Create JAR (manual path)

# Database operations
just db-stats                   # Show group statistics
just db-list                    # List registered groups

# Utilities
just check-env                  # Check environment variables
just unicode-convert <file> <mode>  # Convert Unicode

# Complete workflow
just workflow-group <group> <version>  # Complete workflow for a group
```

## Examples

### Complete Workflow for a New Group

```bash
# 1. Fetch translation keys from Confluence
just fetch linchpin-suite --yes

# 2. Import JSON to database (find latest file)
ls -t raw_data/linchpin-suite_*.json | head -1 | xargs -I {} just import-group {} linchpin-suite

# 3. Translate pending keys
just translate linchpin-suite --google-api-version v3

# 4. Export translated keys to properties file
just export-group linchpin-suite

# 5. Package as JAR
just package-group linchpin-suite 1.0.0

# Or use the complete workflow command (does all steps above)
just workflow-group linchpin-suite 1.0.0 --google-api-version v3
```

### Fetch and Import

```bash
# Fetch keys for a specific group
just fetch scroll-k15t --yes

# Fetch keys for a single plugin (alternative)
just fetch-plugin com.k15t.scroll.scroll-viewport

# Import latest JSON file for a group
just import-group raw_data/scroll-k15t_20251120_071851.json scroll-k15t

# Or automatically find and import latest file
ls -t raw_data/scroll-k15t_*.json | head -1 | xargs -I {} just import-group {} scroll-k15t
```

### Translation Examples

```bash
# Translate using auto-detected service (DeepL or Google)
just translate linchpin-suite

# Force Google Cloud Translation v3
just translate linchpin-suite --google-api-version v3

# Force Google Cloud Translation v2
just translate linchpin-suite --google-api-version v2

# Force DeepL (set environment variable)
TRANSLATION_SERVICE=deepl just translate linchpin-suite

# Translate with custom target language
TARGET_LANGUAGE=de_DE just translate linchpin-suite --google-api-version v3
```

### Export and Package

```bash
# Export to auto-generated path (uses TARGET_LANGUAGE)
just export-group linchpin-suite
# Creates: output/linchpin-suite/linchpin-suite_ru_RU.properties

# Export to custom path
just export linchpin-suite output/custom/custom-linchpin.properties

# Package with auto-generated paths
just package-group linchpin-suite 1.0.0
# Creates: output/linchpin-suite/linchpin-suite-i18n-pack-1.0.0.jar

# Package with custom paths
just package linchpin-suite output/linchpin-suite/linchpin-suite_ru_RU.properties 2.0.0
```

### Database Operations

```bash
# Check statistics for all groups
just db-stats

# Check statistics for a specific group
python src/db_group_manager.py --stats linchpin-suite

# List all registered groups
just db-list

# View pending translations count
python src/db_group_manager.py --stats linchpin-suite | grep pending
```

### Multi-Language Examples

```bash
# Set target language for German
export TARGET_LANGUAGE=de_DE

# Complete workflow for German translations
just workflow-group linchpin-suite 1.0.0 --google-api-version v3
# Exports: output/linchpin-suite/linchpin-suite_de_DE.properties
# Creates: output/linchpin-suite/linchpin-suite-i18n-pack-1.0.0.jar

# Set target language for French
export TARGET_LANGUAGE=fr_FR
just translate linchpin-suite --google-api-version v3
just export-group linchpin-suite
just package-group linchpin-suite 1.0.0
```

### Common Workflows

**Quick retranslate and repackage:**
```bash
# If translations exist but need updating
just translate linchpin-suite --google-api-version v3
just export-group linchpin-suite
just package-group linchpin-suite 1.1.0
```

**Check translation progress:**
```bash
# See how many keys are translated
python src/db_group_manager.py --stats linchpin-suite

# Then translate pending keys
just translate linchpin-suite --google-api-version v3
```

**Import existing translations:**
```bash
# Import from existing JSON file (filters by target language)
just import-translations raw_data/linchpin-suite_20251120_004135.json linchpin-suite
# Automatically filters and imports only Russian (or TARGET_LANGUAGE) translations
```

## Database Operations

### Check Statistics

```bash
just db-stats
# Shows: Group Name: translated/total (percentage%)
```

### List Registered Groups

```bash
just db-list
# Shows: Display Name (group-key) -> table_name
```

## Translation Services

### DeepL API

**Pros:**
- ✅ Highest translation quality
- ✅ Context-aware translations
- ✅ Native HTML/placeholder preservation
- ✅ Free tier available

**Cons:**
- ⚠️ Geo-blocking possible (use proxy if needed)
- ⚠️ Lower rate limits on free tier

**Configuration:**
```bash
DEEPL_API_KEY=your_key_here
TRANSLATION_SERVICE=deepl  # Optional, auto-detected if DEEPL_API_KEY is set
```

### Google Cloud Translation API

**Pros:**
- ✅ Reliable, no geo-blocking
- ✅ Higher rate limits (v2: 300k req/min, v3: 6k req/min)
- ✅ $300 trial credits available
- ✅ Same pricing for v2 and v3

**Cons:**
- ⚠️ Requires Google Cloud setup
- ⚠️ v3 has lower rate limits than v2

**Configuration:**
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_TRANSLATE_API_VERSION=v3  # or v2
TRANSLATION_SERVICE=google
```

**Version Selection:**
- **v3 (Advanced)**: Recommended for new projects. Same price, access to advanced features.
- **v2 (Basic)**: Higher rate limits, simpler API.

See `docs/GOOGLE_API_VERSION_USAGE.md` for detailed comparison.

## Technical Details

### Placeholder Preservation

- **DeepL**: Native XML/HTML tag handling preserves HTML tags automatically. Placeholders (`{0}`, `{1}`) converted to XML tags (`<ph id="0"/>`) before translation.
- **Google Cloud**: HTML format preserves HTML tags automatically. Placeholders protected via XML conversion.

### Unicode Escaping

- Cyrillic characters automatically converted to `\uXXXX` format
- Required for Java properties files
- Example: `Глобальные` → `\u0413\u043B\u043E\u0431\u0430\u043B\u044C\u043D\u044B\u0435`

### Rate Limiting & Batch Processing

- Batch processing: 100 keys per batch
- Automatic pauses on high load (HTTP 429 errors)
- Exponential backoff for retries
- Detailed logging for progress tracking

### Database Schema

**Group Registry Table:**
```sql
group_registry
- group_key (TEXT PRIMARY KEY)
- table_name (TEXT UNIQUE)
- display_name (TEXT)
- description (TEXT)
- created_at (TIMESTAMP)
```

**Group Table (e.g., `linchpin_suite`):**
```sql
{group}_table
- key (TEXT PRIMARY KEY)
- original_text (TEXT NOT NULL)
- translated_text (TEXT)
- status (TEXT) -- 'pending', 'translated', 'error'
- translation_method (TEXT) -- 'deepl', 'google', etc.
- plugin_key (TEXT)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
- metadata (TEXT)
```

## Troubleshooting

### Check Environment Variables

```bash
just check-env
# Verifies: CONFLUENCE_URL, CONFLUENCE_BEARER_TOKEN, translation API keys
```

### Verify Database

```bash
just db-stats
# Shows statistics for all groups
```

### Translation Service Issues

**DeepL:**
- If geo-blocked, use `DEEPL_PROXY` in `.env`
- Check API key validity
- Verify internet connection

**Google Cloud:**
- Verify service account JSON file path
- Check project ID is set (for v3)
- Ensure Cloud Translation API is enabled
- See `docs/GOOGLE_CLOUD_SETUP.md` for detailed setup

### Resume Translation

If translation was interrupted:

```bash
# Translation automatically resumes from pending/error keys
just translate linchpin-suite
```

## Documentation

- **WORKFLOW.md**: Detailed step-by-step workflow guide
- **docs/GOOGLE_API_VERSION_USAGE.md**: Google Cloud Translation API version selection guide
- **docs/GOOGLE_CLOUD_SETUP.md**: Google Cloud Translation API setup instructions
- **docs/TRANSLATION_ALTERNATIVES.md**: Comparison of translation services

## References

- [DeepL API Documentation](https://developers.deepl.com/docs)
- [Google Cloud Translation API](https://cloud.google.com/translate/docs)
- [Confluence i18n API](https://developer.atlassian.com/server/confluence/internationalization-i18n/)
- [Linchpin Translations Documentation](https://info.seibert.group/spaces/KB/pages/46891532/How+can+I+get+the+key+to+translate+apps+with+Linchpin+Translations)

## Notes

- Translation process is resumable - progress saved in database
- Properties files only include translated keys
- JAR files can be installed directly in Confluence
- Groups can contain plugins from different vendors (just organize logically)
- File names use group names for consistency and clarity
- Existing translations are protected during re-import
