# Translation Service Alternatives

This project supports multiple translation services. Here are the available options:

## 1. **Google Cloud Translation API** ⭐ Recommended

**Pros:**
- Reliable and fast
- Good translation quality
- Supports HTML/XML tag preservation
- Handles placeholders well
- Generous free tier (500,000 characters/month)

**Cons:**
- Requires Google Cloud account
- Paid after free tier

**Setup:**
```bash
pip install google-cloud-translate
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

**Cost:** $20 per 1 million characters

---

## 2. **Microsoft Azure Translator** ⭐ Good Alternative

**Pros:**
- Good translation quality
- Free tier (2 million characters/month)
- Supports HTML/XML
- Good API documentation

**Cons:**
- Requires Azure account

**Setup:**
```bash
pip install azure-ai-translation-text
```

**Cost:** Free tier, then $10 per 1 million characters

---

## 3. **AWS Translate**

**Pros:**
- Reliable infrastructure
- Good for AWS users

**Cons:**
- More expensive than alternatives
- Requires AWS account

**Cost:** $15 per 1 million characters

---

## 4. **LibreTranslate** (Self-Hosted) ⭐ Free & Open Source

**Pros:**
- Completely free (self-hosted)
- No API limits
- Open source
- No cloud dependency

**Cons:**
- Requires self-hosting (Docker)
- Lower translation quality than commercial services
- Requires server resources

**Setup:**
```bash
# Self-host with Docker
docker run -ti --rm -p 5000:5000 libretranslate/libretranslate
```

**Cost:** Free (self-hosted)

**API:** Simple REST API
```bash
curl -X POST "http://localhost:5000/translate" \
  -H "Content-Type: application/json" \
  -d '{"q": "Hello", "source": "en", "target": "ru"}'
```

---

## 5. **MyMemory Translation API**

**Pros:**
- Free tier (10,000 characters/day)
- Simple REST API
- No account required for free tier

**Cons:**
- Lower translation quality
- Limited free tier
- Basic API

**Cost:** Free (limited), then paid plans

---

## 6. **OpenAI GPT (for translation)**

**Pros:**
- High quality contextual translation
- Good at preserving formatting

**Cons:**
- More expensive
- Overkill for translation

**Cost:** ~$0.03 per 1 million characters

---

## Quick Comparison

| Service | Quality | Free Tier | Cost/1M chars | Setup Difficulty |
|---------|---------|-----------|---------------|------------------|
| **DeepL** | ⭐⭐⭐⭐⭐ | 500k/month | $20 | Easy |
| **Google Translate** | ⭐⭐⭐⭐⭐ | 500k/month | $20 | Medium |
| **Azure Translator** | ⭐⭐⭐⭐ | 2M/month | $10 | Medium |
| **AWS Translate** | ⭐⭐⭐⭐ | None | $15 | Medium |
| **LibreTranslate** | ⭐⭐⭐ | Unlimited | Free | Easy (if self-hosting) |
| **MyMemory** | ⭐⭐⭐ | 10k/day | Variable | Very Easy |

---

## Recommendation

1. **Best overall:** Google Cloud Translation API (if you can set it up)
2. **Best free tier:** Microsoft Azure Translator (2M/month free)
3. **Best for privacy/self-hosting:** LibreTranslate (if you can self-host)
4. **Quickest to test:** MyMemory (no account needed)

---

## Next Steps

I can help you integrate any of these services. Which one would you like to use?

1. Modify the code to support multiple providers
2. Add configuration to switch between services
3. Implement fallback (try DeepL first, fallback to another if fails)

