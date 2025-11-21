# BigPicture Russian Translation - Tampermonkey Scripts

Tampermonkey scripts to enable Russian translations in BigPicture Jira plugin.

## 📋 Available Scripts

### 1. Simple Version (`bigpicture_russian_translation.user.js`) ⭐ Recommended
- **Size**: 3.1 KB
- **Functionality**: Basic URL redirection (en-US → ru-RU)
- **Best for**: Most users, minimal overhead
- **Features**:
  - Intercepts `fetch()` API calls
  - Intercepts `XMLHttpRequest` (XHR)
  - Redirects translation requests automatically
  - Simple console logging

### 2. Advanced Version (`bigpicture_russian_translation_advanced.user.js`)
- **Size**: 4.7 KB
- **Functionality**: URL redirection + cache handling
- **Best for**: Users experiencing caching issues
- **Features**:
  - Everything from Simple version +
  - Cache-busting (adds `_nocache` parameter)
  - Clears cached responses automatically
  - Monitors dynamic script tags
  - More robust error handling

### 3. External Source Version (`bigpicture_russian_translation_external.user.js`)
- **Size**: ~7 KB
- **Functionality**: URL redirection OR external translation source
- **Best for**: Advanced users, centralized translation management
- **Features**:
  - Everything from Advanced version +
  - Load translations from external source (GitHub/CDN/server)
  - Hybrid mode (merge external + plugin translations)
  - Update translations without reinstalling JARs

## 🚀 Quick Installation

### Method 1: Direct Install from GitHub (Recommended)

1. **Install Tampermonkey browser extension** (if not already installed):
   - Chrome/Edge: [Tampermonkey for Chrome](https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo)
   - Firefox: [Tampermonkey for Firefox](https://addons.mozilla.org/en-US/firefox/addon/tampermonkey/)

2. **Click the installation link** for your preferred script:

   **Simple Version** (Recommended for most users):
   ```
   https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation.user.js
   ```
   
   **Advanced Version** (If you have caching issues):
   ```
   https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation_advanced.user.js
   ```
   
   **External Source Version** (For external translation management):
   ```
   https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation_external.user.js
   ```

3. **Tampermonkey will open** → Click "Install"

4. **Done!** Visit your BigPicture page to see Russian translations.

### Method 2: Manual Installation

1. **Install Tampermonkey** (see Method 1, step 1)

2. **Open Tampermonkey Dashboard**:
   - Click Tampermonkey icon in browser toolbar
   - Select "Dashboard"

3. **Create New Script**:
   - Click "Create a new script..." or "+" button
   - Delete the default template code

4. **Copy Script Content**:
   - Open the `.user.js` file you want to install
   - Copy all content (Ctrl+A, Ctrl+C)
   - Paste into Tampermonkey editor (Ctrl+V)

5. **Save Script**:
   - Press Ctrl+S or click "File" → "Save"
   - The script will be active immediately

6. **Verify Installation**:
   - Visit your BigPicture page
   - Open browser console (F12)
   - Look for: `[BigPicture Russian Translation] Script loaded`
   - Look for: `[BigPicture Russian Translation] Redirected en-US → ru-RU`

## 🔧 Configuration (External Source Version Only)

If using `bigpicture_russian_translation_external.user.js`, edit the `CONFIG` section:

```javascript
const CONFIG = {
    fromLocale: 'en-US',
    toLocale: 'ru-RU',
    
    // Option 1: Use external translation source
    useExternalSource: false,  // Set to true to use external translations
    
    // External translation URLs (update with your URLs)
    externalBackendUrl: 'https://raw.githubusercontent.com/your-org/repo/main/translations/message_ru-RU.json',
    externalFrontendUrl: 'https://raw.githubusercontent.com/your-org/repo/main/translations/bigpicture_ru-RU.json',
    
    // Option 2: Hybrid mode (merge external + plugin)
    useHybridMode: false,  // Set to true to merge translations
    
    // Option 3: Just redirect URL (current method)
    useUrlRedirect: true,  // Default: redirects en-US → ru-RU
    
    logRedirects: true
};
```

## ✅ Verification

After installation, verify the script is working:

1. **Open Browser Console** (F12)
2. **Navigate to BigPicture page**
3. **Check Console Messages**:
   - `[BigPicture Russian Translation] Script loaded`
   - `[BigPicture Russian Translation] Redirected en-US → ru-RU: /rest/.../ru-RU`
4. **Check Network Tab**:
   - Look for requests to `/system/l10n/ru-RU` instead of `/system/l10n/en-US`
5. **Check UI**:
   - BigPicture interface should display in Russian

## 🔄 Updating Scripts

### Automatic Updates (Recommended)

Scripts include version numbers. Tampermonkey can check for updates automatically:
- Open Tampermonkey Dashboard
- Click on the script
- Check "Update URL" is set to the GitHub raw URL
- Enable "Check for updates" (default: enabled)

### Manual Updates

1. Download updated script from GitHub
2. Open Tampermonkey Dashboard
3. Click on script to edit
4. Replace code with new version
5. Save (Ctrl+S)

## 📝 Requirements

- **Tampermonkey browser extension** installed
- **BigPicture Jira plugin** installed with Russian translations in JAR
- **JavaScript enabled** in browser

## 🐛 Troubleshooting

### Script not working?

1. **Check Tampermonkey is enabled**:
   - Click Tampermonkey icon → Ensure script is enabled (green checkmark)

2. **Check URL matches**:
   - Script matches: `https://*/rest/softwareplant-bigpicture/*`
   - Visit BigPicture page on your Jira instance

3. **Check console for errors**:
   - Open browser console (F12)
   - Look for any error messages
   - Verify script is loaded

4. **Check network requests**:
   - Open Network tab in DevTools
   - Look for `/system/l10n/ru-RU` requests
   - Verify responses contain Russian text

5. **Try Advanced version**:
   - If caching issues, use `bigpicture_russian_translation_advanced.user.js`
   - Clears caches automatically

### Still not working?

- Ensure BigPicture JAR has Russian translations installed
- Check Jira logs for plugin loading errors
- Verify user has permission to access BigPicture

## 📚 Additional Resources

- [Tampermonkey Documentation](https://www.tampermonkey.net/documentation.php)
- [GitHub Repository](https://github.com/astrateam-net/confluence-localization-toolkit)

## 🔗 Installation Links (for GitHub hosting)

Once scripts are hosted on GitHub, use these direct install links:

**Simple Version:**
```
https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation.user.js
```

**Advanced Version:**
```
https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation_advanced.user.js
```

**External Source Version:**
```
https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation_external.user.js
```

Users can click these links or paste them into Tampermonkey's "Install from URL" feature.

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-21  
**Maintained by**: AstraTeam

