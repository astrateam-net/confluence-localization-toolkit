# Translation Workflow

## Overview

This document describes the complete workflow for translating Confluence plugin groups from English to Russian. The process is **group-based**, meaning related plugins are organized into groups, and each group produces one JAR package for installation.

**Translation Services Supported:**
- **DeepL API**: Recommended for quality, context-aware translations
- **Google Cloud Translation API**: Reliable alternative with v2 (Basic) or v3 (Advanced) options

## Architecture

- **config/plugins.yaml**: Defines plugin groups and their plugins
- **raw_data/**: Raw API responses from Confluence (JSON files named by group)
- **db/translations.db**: SQLite database with separate table per group
- **output/**: Generated properties files and JAR packages

## Complete Workflow

### Step 1: Define Group Configuration

Edit `config/plugins.yaml` to define your group:

```yaml
groups:
  linchpin-suite:
    name: "Linchpin Suite"
    description: "All Linchpin Suite plugins"
    plugins:
      - net.seibertmedia.confluence.language-manager
      - net.seibertmedia.confluence.linchpin-connector
      # ... add all plugins in this group
```

### Step 2: Configure Translation Service

Choose your translation service in `.env`:

**Option A: DeepL (Recommended for Quality)**
```bash
DEEPL_API_KEY=your_deepl_api_key_here
TRANSLATION_SERVICE=deepl  # Optional, auto-detected
```

**Option B: Google Cloud Translation (Recommended for Reliability)**
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GOOGLE_TRANSLATE_API_VERSION=v3  # or v2 - v3 recommended for new projects
TRANSLATION_SERVICE=google  # Optional, auto-detected
GOOGLE_CLOUD_PROJECT=your-project-id  # Optional, auto-detected from JSON
```

**Auto-Detection:**
- If `DEEPL_API_KEY` is set → uses DeepL
- If `GOOGLE_APPLICATION_CREDENTIALS` is set → uses Google Cloud Translation
- Set `TRANSLATION_SERVICE=auto` (default) for automatic selection

### Step 3: Fetch Translation Keys

Fetch all translation keys for a group from Confluence API:

```bash
# Using justfile (recommended)
just fetch linchpin-suite --yes

# Or directly
python src/fetch_confluence_keys.py --group linchpin-suite --yes
```

**What it does:**
- Reads plugins from `config/plugins.yaml` for the specified group
- Makes API request to Confluence: `{CONFLUENCE_URL}/rest/prototype/1/i18n.json?pluginKeys=...`
- Saves response to `raw_data/linchpin-suite_20251120_004135.json` (named by group)

**Requirements:**
- `.env` file with `CONFLUENCE_URL` and `CONFLUENCE_BEARER_TOKEN`
- Confluence instance must be accessible
- All plugins in the group must exist in Confluence

**Output:**
- JSON file in `raw_data/` folder
- File name: `{group}_{timestamp}.json`
- Contains all translation keys from all plugins in the group

### Step 4: Import to Database

Import the fetched JSON into a group-based database table:

```bash
# Using justfile (recommended)
just import-group raw_data/linchpin-suite_20251120_004135.json linchpin-suite

# Or automatically use latest file
ls -t raw_data/linchpin-suite*.json | head -1 | xargs -I {} just import-group {} linchpin-suite

# Or directly
python src/import_group_json.py --file raw_data/linchpin-suite_20251120_004135.json --group linchpin-suite
```

**What it does:**
- Creates table if it doesn't exist: `linchpin_suite` (group key converted to table name)
- Imports all keys from JSON into the table
- Sets `status='pending'` for new keys
- **Protects existing translations**: Skips keys that already have `translated_text`
- Updates English text if keys changed in Confluence

**Database Structure:**
- One table per group (e.g., `linchpin_suite`)
- Each row contains: `key`, `original_text`, `translated_text`, `status`, `plugin_key`, etc.
- Table is automatically created and initialized on first import

**Import Statistics:**
- Shows: New keys imported, Existing keys updated, Translations protected

### Step 5: Translate

Translate pending keys using your chosen translation service:

**Using Default Service (Auto-Detected):**
```bash
# Using justfile (recommended)
just translate linchpin-suite
```

**Force DeepL:**
```bash
TRANSLATION_SERVICE=deepl just translate linchpin-suite
```

**Force Google Cloud Translation:**
```bash
# Use v3 (Advanced) - recommended for new projects
just translate linchpin-suite --google-api-version v3

# Use v2 (Basic) - higher rate limits
just translate linchpin-suite --google-api-version v2
```

**What it does:**
- Fetches all keys with `status='pending'` or `status='error'` (no Russian translation yet)
- Translates each key using the selected translation service
- Updates `translated_text` and sets `status='translated'`
- Automatically handles rate limiting and retries
- Batch processing: 100 keys per batch with pauses on high load
- Shows progress and statistics

**DeepL Features:**
- Checks API usage/quota before starting
- Automatic retries for HTTP 429 (rate limit) errors
- Preserves HTML tags and placeholders automatically using native XML handling
- Context-aware translations (not word-by-word)

**Google Cloud Translation Features:**
- Automatic retries for rate limit errors
- Preserves HTML tags and placeholders
- Batch processing with automatic pauses
- Detailed logging for progress tracking

**Requirements:**
- `.env` file with translation API credentials (see Step 2)
- Sufficient API quota
- Internet connection to translation API

**Resume Capability:**
- If interrupted, simply run `just translate <group>` again
- Automatically continues from keys with `status='pending'` or `status='error'`
- Database tracks which keys are translated
- Safe to interrupt and resume multiple times

### Step 6: Export Translations

Export Russian translations to Java properties file:

```bash
# Using justfile (recommended)
just export linchpin-suite output/linchpin-suite_ru_RU.properties

# Or directly
python src/export_group.py --group linchpin-suite --output output/linchpin-suite_ru_RU.properties
```

**What it does:**
- Exports only keys with `status='translated'`
- Automatically converts Cyrillic to Unicode escapes (`\uXXXX` format)
- Creates Java properties file ready for JAR packaging
- Shows statistics (total, translated, pending)

**Output Format:**
```
key=value
net.seibertmedia.confluence.language-manager.key=\u0413\u043B\u043E\u0431\u0430\u043B\u044C\u043D\u044B\u0435...
```

### Step 7: Package as JAR

Create Confluence plugin JAR package:

```bash
# Using justfile (recommended)
just package linchpin-suite output/linchpin-suite_ru_RU.properties 1.0.0

# Or directly
python src/package_jar.py --properties output/linchpin-suite_ru_RU.properties \
  --plugin linchpin-suite --output output/linchpin-suite-pack-1.0.0.jar --version 1.0.0
```

**What it does:**
- Creates JAR file with `atlassian-plugin.xml` descriptor
- Includes properties file in correct path structure
- Ready to install in Confluence

**JAR Structure:**
```
linchpin-suite-pack-1.0.0.jar
├── atlassian-plugin.xml
└── net/seibertmedia/confluence/language/i18n/
    └── i18n_ru_RU.properties
```

## Quick Workflow (All Steps)

Use the complete workflow command:

```bash
just workflow-group linchpin-suite
```

This runs all steps automatically:
1. Fetch keys
2. Import to database
3. Translate pending keys
4. Export to properties file

## Translation Service Selection

### Choosing Between DeepL and Google Cloud Translation

**Use DeepL if:**
- ✅ Translation quality is your top priority
- ✅ You have reliable DeepL API access
- ✅ You prefer context-aware translations

**Use Google Cloud Translation if:**
- ✅ You need reliable service without geo-blocking
- ✅ You have $300 trial credits available
- ✅ You want higher rate limits (v2: 300k req/min)

### Google Cloud Translation Version Selection

**Use v3 (Advanced) if:**
- ✅ Starting a new project (recommended)
- ✅ Same pricing as v2 ($20/1M chars)
- ✅ Want access to advanced features (glossaries, document translation)

**Use v2 (Basic) if:**
- ✅ Need higher rate limits (300k req/min vs 6k for v3)
- ✅ Want simpler API
- ✅ Standard translation is sufficient

See `docs/GOOGLE_API_VERSION_USAGE.md` for detailed comparison.

### Runtime Version Selection

You can choose the version at runtime:

```bash
# Use v3
just translate linchpin-suite --google-api-version v3

# Use v2
just translate linchpin-suite --google-api-version v2
```

Or set in `.env`:
```bash
GOOGLE_TRANSLATE_API_VERSION=v3  # or v2
```

## Managing Multiple Groups

### Check All Groups

```bash
# Show statistics for all groups
just db-stats

# List all registered groups
just db-list
```

### Add a New Group

1. Edit `config/plugins.yaml`:
   ```yaml
   groups:
     my-new-group:
       name: "My New Group"
       description: "Description here"
       plugins:
         - com.example.plugin1
         - com.example.plugin2
   ```

2. Fetch: `just fetch my-new-group --yes`
3. Import: `just import-group raw_data/my-new-group_*.json my-new-group`
4. Translate: `just translate my-new-group`
5. Export: `just export my-new-group output/my-new-group_ru_RU.properties`

## Translation Protection

The import process **never overwrites existing Russian translations**. This means:

✅ **Safe to re-fetch**: If translations are updated in Confluence, you can re-fetch and re-import without losing existing Russian work

✅ **Safe to re-import**: Running import multiple times will only update English text for keys that already have translations

✅ **Protected**: Any key with `translated_text` is skipped during import

**How it works:**
- New key → Inserted with `status='pending'`
- Existing key, no translation → Updated (English text may have changed)
- Existing key, has translation → **Skipped** (protected)

## Resuming Translation

If translation is interrupted, resume by simply running the translate command again:

```bash
# Automatically resumes from pending/error keys
just translate linchpin-suite
```

**The script will:**
1. Fetch all keys with `status='pending'` or `status='error'`
2. Continue translating from where it stopped
3. Update `status='translated'` for each completed key

No need to specify starting position - the database tracks progress automatically.

## Example: Complete Workflow

```bash
# 1. Define group in config/plugins.yaml (already done for linchpin-suite)

# 2. Configure translation service in .env
# DEEPL_API_KEY=your_key_here
# OR
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
# GOOGLE_TRANSLATE_API_VERSION=v3

# 3. Fetch keys
just fetch linchpin-suite --yes
# Output: raw_data/linchpin-suite_20251120_004135.json (5,771 keys)

# 4. Import to database
just import-group raw_data/linchpin-suite_20251120_004135.json linchpin-suite
# Creates: linchpin_suite table
# Imports: 5,771 keys with status='pending'

# 5. Translate (this may take a while for large groups)
just translate linchpin-suite
# Or with Google v3:
# just translate linchpin-suite --google-api-version v3
# Translates all 5,771 keys using selected translation service
# Updates status='translated' for each completed key

# 6. Export
just export linchpin-suite output/linchpin-suite_ru_RU.properties
# Creates: Properties file with Unicode escapes
# Exports: Only translated keys

# 7. Package
just package linchpin-suite output/linchpin-suite_ru_RU.properties 1.0.0
# Creates: output/linchpin-suite-pack-1.0.0.jar
# Ready to install in Confluence!
```

## Best Practices

1. **Use groups**: Organize related plugins into groups for easier management
2. **Check statistics**: Use `just db-stats` before translating to see progress
3. **Resume safely**: Translation can be interrupted and resumed without losing progress
4. **Protect translations**: Re-importing won't overwrite existing translations
5. **Version JARs**: Use semantic versioning (e.g., 1.0.0, 1.0.1) for JAR packages
6. **Test before install**: Extract JAR to verify structure before installing in production
7. **Choose right service**: Use DeepL for quality, Google Cloud for reliability
8. **Version selection**: For new projects, prefer Google Cloud Translation v3

## Troubleshooting

### Import fails

- Check JSON file exists: `ls raw_data/linchpin-suite*.json`
- Verify group name matches config: Check `config/plugins.yaml`
- Check database permissions: Ensure `db/` directory is writable

### Translation fails

**DeepL:**
- Check DeepL API key: `just check-env`
- Verify API quota: Translation script shows usage before starting
- Check internet connection: DeepL API must be accessible
- If geo-blocked: Set `DEEPL_PROXY` in `.env`

**Google Cloud Translation:**
- Check credentials file path: Verify `GOOGLE_APPLICATION_CREDENTIALS` in `.env`
- Verify service account JSON file exists and is readable
- Check project ID: For v3, ensure `project_id` is in credentials JSON or set `GOOGLE_CLOUD_PROJECT`
- Ensure Cloud Translation API is enabled in Google Cloud Console
- See `docs/GOOGLE_CLOUD_SETUP.md` for detailed setup

**Both Services:**
- Resume if interrupted: Simply run `just translate <group>` again
- Check logs: Translation logs are saved in `logs/` directory
- Verify batch size: 100 keys per batch is default, adjust if needed

### Export empty

- Verify translations exist: `just db-stats`
- Check status: Keys must have `status='translated'`
- Export includes only translated keys by default

## Database Schema

### Group Registry

Tracks all registered groups:

```sql
group_registry
- group_key (TEXT PRIMARY KEY)      -- e.g., 'linchpin-suite'
- table_name (TEXT UNIQUE)          -- e.g., 'linchpin_suite'
- display_name (TEXT)               -- e.g., 'Linchpin Suite'
- description (TEXT)                -- Optional description
- created_at (TIMESTAMP)
- metadata (TEXT)                   -- JSON metadata
```

### Group Tables

Each group has its own table:

```sql
{group}_table  -- e.g., linchpin_suite
- key (TEXT PRIMARY KEY)            -- Translation key
- original_text (TEXT NOT NULL)     -- English text
- translated_text (TEXT)            -- Russian translation (if translated)
- status (TEXT)                     -- 'pending', 'translated', 'error'
- translation_method (TEXT)         -- 'deepl', 'google', etc.
- plugin_key (TEXT)                 -- Which plugin this key belongs to
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
- metadata (TEXT)                   -- JSON metadata
```

**Indexes:**
- `idx_{table}_status` - Fast lookup by status
- `idx_{table}_plugin` - Fast lookup by plugin
- `idx_{table}_updated` - Fast lookup by update time

## Tips

- **Large groups**: Translation may take hours for large groups. Use batch processing (automatic) and resume capability.
- **Multiple groups**: Work on different groups in parallel if needed.
- **Re-fetching**: Safe to re-fetch and re-import - existing translations are protected.
- **JAR naming**: Use group name as JAR name for consistency (e.g., `linchpin-suite-pack-1.0.0.jar`).
- **Versioning**: Update version number when creating new JAR packages.
- **Translation service**: Test both services if unsure - DeepL for quality, Google Cloud for reliability.
- **API version**: For new Google Cloud projects, prefer v3 - same price, more features.
