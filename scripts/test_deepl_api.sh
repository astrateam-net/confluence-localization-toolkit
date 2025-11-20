#!/bin/bash
# Test DeepL API connectivity from your host
# Usage: ./test_deepl_api.sh

# Load API key from .env file if available
if [ -f .env ]; then
    source .env 2>/dev/null
    echo "✓ Loaded API key from .env"
else
    echo "⚠ .env file not found. Set DEEPL_API_KEY environment variable."
fi

if [ -z "$DEEPL_API_KEY" ]; then
    echo "❌ Error: DEEPL_API_KEY not set"
    echo "   Either set it in .env file or export it:"
    echo "   export DEEPL_API_KEY=your_key_here"
    exit 1
fi

echo ""
echo "=========================================="
echo "Testing DeepL API Connectivity"
echo "=========================================="
echo ""

# Test 1: Check connectivity to paid endpoint (DNS and TCP)
echo "Test 1: DNS and TCP connectivity to api.deepl.com"
echo "---------------------------------------------------"
timeout 5 ping -c 2 api.deepl.com 2>&1 | head -5
echo ""

# Test 2: Test HTTPS connection to paid endpoint
echo "Test 2: HTTPS connection to paid endpoint (api.deepl.com)"
echo "---------------------------------------------------"
curl -v \
  --connect-timeout 10 \
  --max-time 15 \
  -X POST "https://api.deepl.com/v2/translate" \
  --header "Content-Type: application/json" \
  --header "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
  --data '{"text": ["Hello world!"], "target_lang": "RU"}' \
  2>&1 | head -40
echo ""
echo ""

# Test 3: Test HTTPS connection to free endpoint
echo "Test 3: HTTPS connection to free endpoint (api-free.deepl.com)"
echo "---------------------------------------------------"
curl -v \
  --connect-timeout 10 \
  --max-time 15 \
  -X POST "https://api-free.deepl.com/v2/translate" \
  --header "Content-Type: application/json" \
  --header "Authorization: DeepL-Auth-Key $DEEPL_API_KEY" \
  --data '{"text": ["Hello world!"], "target_lang": "RU"}' \
  2>&1 | head -40
echo ""
echo ""

# Test 4: Simple GET to check status (languages endpoint - doesn't require valid key for connection test)
echo "Test 4: Languages endpoint (tests basic connection)"
echo "---------------------------------------------------"
curl -v \
  --connect-timeout 10 \
  --max-time 15 \
  "https://api.deepl.com/v2/languages?type=target" \
  2>&1 | head -30
echo ""

echo "=========================================="
echo "Test Summary:"
echo "=========================================="
echo "If you see 'SSL connection timeout' or 'Connection timeout' above,"
echo "your IP may be blocked by DeepL or there's a network connectivity issue."
echo ""
echo "If you see HTTP responses (200, 401, 403), the connection works."
echo "401 = Invalid API key (connection OK)"
echo "403 = Forbidden/Blocked (IP may be blocked)"
echo ""

