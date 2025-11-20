# Test Scripts

This folder contains utility scripts for testing translation API connections.

## Available Scripts

### `test_deepl_api.sh`

Test DeepL API connectivity and functionality from the command line.

**Usage:**
```bash
# From project root
./scripts/test_deepl_api.sh

# Or from scripts folder
cd scripts
./test_deepl_api.sh
```

**Requirements:**
- `DEEPL_API_KEY` in `.env` file or environment variable
- `curl` command available
- `dig` and `traceroute` for network diagnostics (optional)

**What it tests:**
- DNS resolution for DeepL API endpoints
- TCP connectivity
- API endpoint accessibility (paid and free)
- Translation functionality

### `test_google_translate.py`

Test Google Cloud Translation API connection and functionality.

**Usage:**
```bash
# From project root
python scripts/test_google_translate.py

# Or from scripts folder
cd scripts
python test_google_translate.py
```

**Requirements:**
- `GOOGLE_APPLICATION_CREDENTIALS` in `.env` file or environment variable
- Service account JSON file with Cloud Translation API access
- `google-cloud-translate` Python package installed

**What it tests:**
- Credentials validation
- Client initialization
- Language detection
- Basic translation
- HTML tag preservation
- Placeholder preservation

## When to Use

Use these scripts when:
- Setting up translation services for the first time
- Troubleshooting connection issues
- Verifying API credentials
- Testing network connectivity to translation APIs

