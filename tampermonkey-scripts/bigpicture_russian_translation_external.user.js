// ==UserScript==
// @name         BigPicture Russian Translation (External Source)
// @namespace    http://tampermonkey.net/
// @version      2.0.0
// @description  Redirects BigPicture translation requests AND/OR loads translations from external source (GitHub, CDN, custom server)
// @author       AstraTeam
// @match        https://*/rest/softwareplant-bigpicture/*
// @match        https://*/download/resources/eu.softwareplant.bigpicture:static-pages/*
// @match        https://*/plugins/servlet/softwareplant-bigpicture/*
// @grant        none
// @run-at       document-start
// @updateURL    https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation_external.user.js
// @downloadURL  https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation_external.user.js
// ==/UserScript==

(function() {
    'use strict';

    console.log('[BigPicture Russian Translation] External source script loaded');

    // ============================================================================
    // CONFIGURATION - Customize these URLs
    // ============================================================================
    const CONFIG = {
        fromLocale: 'en-US',
        toLocale: 'ru-RU',
        
        // Option 1: Use external translation source instead of plugin
        useExternalSource: false,  // Set to true to use external translations
        
        // External translation sources (can use any of these):
        externalBackendUrl: 'https://raw.githubusercontent.com/your-org/repo/main/translations/message_ru-RU.json',
        externalFrontendUrl: 'https://raw.githubusercontent.com/your-org/repo/main/translations/bigpicture_ru-RU.json',
        
        // Alternative: Your own CDN/server
        // externalBackendUrl: 'https://your-cdn.com/translations/message_ru-RU.json',
        // externalFrontendUrl: 'https://your-cdn.com/translations/bigpicture_ru-RU.json',
        
        // Option 2: Hybrid mode - load plugin but override with external translations
        useHybridMode: false,  // Set to true to merge external translations with plugin
        
        // Option 3: Just redirect URL (current working method)
        useUrlRedirect: true,  // Redirects en-US → ru-RU in plugin
        
        logRedirects: true
    };

    function log(message) {
        if (CONFIG.logRedirects) {
            console.log(`[BigPicture Russian Translation] ${message}`);
        }
    }

    // ============================================================================
    // Fetch translations from external source (GitHub, CDN, custom server)
    // ============================================================================
    async function fetchExternalTranslations(backendUrl, frontendUrl) {
        try {
            log(`Fetching external translations from: ${backendUrl}`);
            
            const [backendResponse, frontendResponse] = await Promise.all([
                fetch(backendUrl, { cache: 'no-store' }).catch(() => null),
                fetch(frontendUrl, { cache: 'no-store' }).catch(() => null)
            ]);
            
            const translations = {
                backend: backendResponse?.ok ? await backendResponse.json() : null,
                frontend: frontendResponse?.ok ? await frontendResponse.json() : null
            };
            
            if (translations.backend || translations.frontend) {
                log('✓ External translations loaded successfully');
                return translations;
            }
            
            log('⚠️ External translations not available, falling back to plugin');
            return null;
        } catch (error) {
            log(`❌ Error loading external translations: ${error.message}`);
            return null;
        }
    }

    // ============================================================================
    // Merge external translations with plugin translations (hybrid mode)
    // ============================================================================
    function mergeTranslations(pluginData, externalData) {
        if (!externalData) return pluginData;
        
        const merged = JSON.parse(JSON.stringify(pluginData)); // Deep clone
        
        // Merge backend translations
        if (externalData.backend && merged.translation) {
            Object.assign(merged.translation, externalData.backend);
            log(`Merged ${Object.keys(externalData.backend).length} external backend translations`);
        }
        
        // Merge frontend translations
        if (externalData.frontend && merged.translation) {
            Object.assign(merged.translation, externalData.frontend);
            log(`Merged ${Object.keys(externalData.frontend).length} external frontend translations`);
        }
        
        merged.locale = CONFIG.toLocale;
        return merged;
    }

    // ============================================================================
    // Intercept fetch API and replace/modify responses
    // ============================================================================
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        let [resource, init] = args;
        let url = typeof resource === 'string' ? resource : resource.url;
        
        // Check if this is a BigPicture l10n request
        if (!url || !url.includes('/system/l10n/')) {
            return originalFetch.apply(this, args);
        }
        
        // Option 1: URL Redirect (current working method)
        if (CONFIG.useUrlRedirect && url.includes(`/system/l10n/${CONFIG.fromLocale}`)) {
            url = url.replace(`/system/l10n/${CONFIG.fromLocale}`, `/system/l10n/${CONFIG.toLocale}`);
            log(`Redirected ${CONFIG.fromLocale} → ${CONFIG.toLocale}: ${url}`);
            
            if (typeof resource === 'string') {
                args[0] = url;
            } else if (resource instanceof Request) {
                args[0] = new Request(url, resource);
            }
        }
        
        // Make the actual fetch request
        const response = await originalFetch.apply(this, args);
        
        // Option 2: Replace response with external translations
        if (CONFIG.useExternalSource && response.ok && url.includes('/system/l10n/')) {
            log('Intercepting response to replace with external translations...');
            
            const externalTranslations = await fetchExternalTranslations(
                CONFIG.externalBackendUrl,
                CONFIG.externalFrontendUrl
            );
            
            if (externalTranslations && externalTranslations.backend) {
                // Create new response with external translations
                const externalData = {
                    locale: CONFIG.toLocale,
                    translation: externalTranslations.backend
                };
                
                log(`✓ Replacing response with external translations (${Object.keys(externalTranslations.backend).length} keys)`);
                
                return new Response(
                    JSON.stringify(externalData),
                    {
                        status: response.status,
                        statusText: response.statusText,
                        headers: {
                            'Content-Type': 'application/json',
                            'Cache-Control': 'no-store'
                        }
                    }
                );
            }
        }
        
        // Option 3: Hybrid mode - merge external translations with plugin response
        if (CONFIG.useHybridMode && response.ok && url.includes('/system/l10n/')) {
            try {
                const pluginData = await response.clone().json();
                const externalTranslations = await fetchExternalTranslations(
                    CONFIG.externalBackendUrl,
                    CONFIG.externalFrontendUrl
                );
                
                if (externalTranslations) {
                    const mergedData = mergeTranslations(pluginData, externalTranslations);
                    log(`✓ Merged external translations with plugin translations`);
                    
                    return new Response(
                        JSON.stringify(mergedData),
                        {
                            status: response.status,
                            statusText: response.statusText,
                            headers: {
                                'Content-Type': 'application/json',
                                'Cache-Control': 'no-store'
                            }
                        }
                    );
                }
            } catch (error) {
                log(`⚠️ Error in hybrid mode: ${error.message}, using original response`);
            }
        }
        
        return response;
    };

    // Intercept XMLHttpRequest for legacy support
    const originalXHROpen = XMLHttpRequest.prototype.open;
    const originalXHRSend = XMLHttpRequest.prototype.send;
    
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        if (typeof url === 'string' && url.includes('/system/l10n/')) {
            if (CONFIG.useUrlRedirect && url.includes(`/system/l10n/${CONFIG.fromLocale}`)) {
                url = url.replace(`/system/l10n/${CONFIG.fromLocale}`, `/system/l10n/${CONFIG.toLocale}`);
                log(`XHR Redirected ${CONFIG.fromLocale} → ${CONFIG.toLocale}`);
            }
            this._url = url; // Store for later use
        }
        return originalXHROpen.apply(this, [method, url, ...rest]);
    };

    XMLHttpRequest.prototype.send = async function(...args) {
        if (this._url && this._url.includes('/system/l10n/')) {
            // Intercept response for external source/hybrid mode
            const originalOnReadyStateChange = this.onreadystatechange;
            
            this.onreadystatechange = async function() {
                if (this.readyState === 4 && this.status === 200) {
                    if (CONFIG.useExternalSource || CONFIG.useHybridMode) {
                        try {
                            const responseText = this.responseText;
                            const pluginData = JSON.parse(responseText);
                            
                            if (CONFIG.useExternalSource) {
                                const externalTranslations = await fetchExternalTranslations(
                                    CONFIG.externalBackendUrl,
                                    CONFIG.externalFrontendUrl
                                );
                                
                                if (externalTranslations && externalTranslations.backend) {
                                    Object.defineProperty(this, 'responseText', {
                                        value: JSON.stringify({
                                            locale: CONFIG.toLocale,
                                            translation: externalTranslations.backend
                                        }),
                                        writable: false
                                    });
                                }
                            } else if (CONFIG.useHybridMode) {
                                const externalTranslations = await fetchExternalTranslations(
                                    CONFIG.externalBackendUrl,
                                    CONFIG.externalFrontendUrl
                                );
                                
                                if (externalTranslations) {
                                    const mergedData = mergeTranslations(pluginData, externalTranslations);
                                    Object.defineProperty(this, 'responseText', {
                                        value: JSON.stringify(mergedData),
                                        writable: false
                                    });
                                }
                            }
                        } catch (error) {
                            log(`⚠️ Error processing XHR response: ${error.message}`);
                        }
                    }
                }
                
                if (originalOnReadyStateChange) {
                    originalOnReadyStateChange.apply(this, arguments);
                }
            };
        }
        
        return originalXHRSend.apply(this, args);
    };

    log('External source interceptors installed');
    log(`Mode: ${CONFIG.useExternalSource ? 'External Source' : CONFIG.useHybridMode ? 'Hybrid' : 'URL Redirect'}`);
})();

