# Google Cloud Translation API Setup

## Step 1: Download Service Account Key

After creating credentials in Google Cloud Console:
1. You downloaded a JSON file (e.g., `project-name-12345-abcdef.json`)
2. Save this file in the `credentials/` directory

## Step 2: Add to .env File

Open your `.env` file and add:

```bash
# Google Cloud Translation API
GOOGLE_APPLICATION_CREDENTIALS=./credentials/your-key-file.json
TRANSLATION_SERVICE=google
```

**Important:** Use a **relative path** from the project root (recommended) or an absolute path to your JSON file.

### Example:

If your JSON file is named `translation-service-abc123.json` and you placed it in `credentials/`:

```bash
# Relative path (recommended)
GOOGLE_APPLICATION_CREDENTIALS=./credentials/translation-service-abc123.json

# Or absolute path
GOOGLE_APPLICATION_CREDENTIALS=/path/to/project/credentials/translation-service-abc123.json

TRANSLATION_SERVICE=google
```

## Step 3: Install Dependencies

```bash
pip install google-cloud-translate
```

Or if using `just`:

```bash
just install
```

## Step 4: Test

```bash
just translate linchpin-suite
```

The system will automatically use Google Cloud Translation API instead of DeepL.

## Notes

- **Never commit** the JSON credentials file to Git (already in .gitignore)
- The JSON file contains sensitive credentials - keep it secure
- You can use `TRANSLATION_SERVICE=auto` to auto-detect (uses Google if GOOGLE_APPLICATION_CREDENTIALS is set)
- Or set `TRANSLATION_SERVICE=deepl` to force DeepL even if Google credentials exist

