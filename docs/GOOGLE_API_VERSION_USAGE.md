# Google Cloud Translation API Version Selection

You can now choose between **v2 (Basic)** and **v3 (Advanced)** when launching translation.

## Quick Comparison

| Feature | v2 (Basic) | v3 (Advanced) |
|---------|------------|---------------|
| **Pricing** | $20/1M chars | $20/1M chars ✅ Same |
| **Rate Limits** | 300k req/min | 6k req/min ⚠️ Lower |
| **Free Tier** | 500k chars/month | 500k chars/month ✅ Same |
| **Features** | Standard NMT | Standard + Advanced features |
| **Recommendation** | Good for simple use | ✅ **Recommended for new projects** |

## How to Choose Version

### Option 1: Command Line Argument

```bash
# Use v3 (Advanced) - recommended for new projects
just translate linchpin-suite --google-api-version v3

# Use v2 (Basic) - simpler, higher rate limits
just translate linchpin-suite --google-api-version v2
```

### Option 2: Environment Variable

Add to your `.env` file:

```bash
# Use v3 (Advanced) - recommended
GOOGLE_TRANSLATE_API_VERSION=v3

# OR use v2 (Basic)
GOOGLE_TRANSLATE_API_VERSION=v2
```

### Option 3: Auto-Detection (Default)

If not specified:
- **Defaults to v3** if available
- Falls back to v2 if v3 not available

## Recommendation for Your Project

Since you're starting a new project with $300 trial credits:

**✅ Use v3 (Advanced):**
- Same price as v2 for standard translation
- Google recommends it for new projects
- Access to advanced features if needed later (glossaries, document translation)
- Future-proof

**Command:**
```bash
just translate linchpin-suite --google-api-version v3
```

Or set in `.env`:
```bash
GOOGLE_TRANSLATE_API_VERSION=v3
```

## Rate Limit Note

⚠️ **Important:** v3 has lower rate limits (6,000 req/min vs 300,000 for v2), but this is still sufficient for your current usage (~20 req/sec = 1,200 req/min).

If you expect to translate very large batches quickly, you might prefer v2 for higher rate limits.

## Current Configuration

With your current `.env`:
- `TRANSLATION_SERVICE=google` - Uses Google Cloud Translation
- Default version: **v3** (since it's new project recommendation)

To explicitly use v2:
```bash
GOOGLE_TRANSLATE_API_VERSION=v2
```

