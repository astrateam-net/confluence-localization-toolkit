// ==UserScript==
// @name         BigPicture Russian Translation (Advanced)
// @namespace    http://tampermonkey.net/
// @version      1.1.0
// @description  Advanced version: Redirects BigPicture translation requests and also handles cached responses
// @author       AstraTeam
// @match        https://*/rest/softwareplant-bigpicture/*
// @match        https://*/download/resources/eu.softwareplant.bigpicture:static-pages/*
// @match        https://*/plugins/servlet/softwareplant-bigpicture/*
// @grant        none
// @run-at       document-start
// @updateURL    https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation_advanced.user.js
// @downloadURL  https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation_advanced.user.js
// ==/UserScript==

(function() {
    'use strict';

    console.log('[BigPicture Russian Translation] Advanced script loaded');

    // Configuration
    const CONFIG = {
        fromLocale: 'en-US',
        toLocale: 'ru-RU',
        logRedirects: true
    };

    function log(message) {
        if (CONFIG.logRedirects) {
            console.log(`[BigPicture Russian Translation] ${message}`);
        }
    }

    function rewriteUrl(url) {
        if (typeof url === 'string') {
            const regex = new RegExp(`/system/l10n/${CONFIG.fromLocale}`, 'g');
            if (regex.test(url)) {
                const newUrl = url.replace(regex, `/system/l10n/${CONFIG.toLocale}`);
                log(`Redirected ${CONFIG.fromLocale} → ${CONFIG.toLocale}: ${newUrl}`);
                return newUrl;
            }
        }
        return url;
    }

    // Intercept fetch API (modern approach)
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        let [resource, init] = args;
        
        // Handle string URLs
        if (typeof resource === 'string') {
            resource = rewriteUrl(resource);
            args[0] = resource;
        }
        
        // Handle Request objects
        if (resource instanceof Request) {
            const url = rewriteUrl(resource.url);
            if (url !== resource.url) {
                // Create new Request with modified URL
                const newRequest = new Request(url, resource);
                args[0] = newRequest;
            }
        }
        
        // Ensure cache-busting for translation requests
        if (typeof resource === 'string' && resource.includes('/system/l10n/')) {
            const urlObj = new URL(resource, window.location.origin);
            urlObj.searchParams.set('_nocache', Date.now());
            args[0] = urlObj.toString();
            log(`Added cache-busting to: ${args[0]}`);
            
            // Force no-cache in fetch options
            if (!init) init = {};
            if (!init.headers) init.headers = {};
            init.cache = 'no-store';
        }
        
        return originalFetch.apply(this, args);
    };

    // Intercept XMLHttpRequest (legacy support)
    const originalXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        if (typeof url === 'string') {
            const newUrl = rewriteUrl(url);
            if (newUrl !== url) {
                // Add cache-busting parameter
                const urlObj = new URL(newUrl, window.location.origin);
                urlObj.searchParams.set('_nocache', Date.now());
                url = urlObj.toString();
            }
        }
        return originalXHROpen.apply(this, [method, url, ...rest]);
    };

    // Clear any cached responses when page loads
    if (window.caches) {
        window.caches.keys().then(keys => {
            keys.forEach(key => {
                if (key.includes('bigpicture') || key.includes('softwareplant')) {
                    window.caches.delete(key).then(() => {
                        log(`Cleared cache: ${key}`);
                    });
                }
            });
        });
    }

    // Monitor for any dynamic script tags that might load translation bundles
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.tagName === 'SCRIPT' && node.src) {
                    const src = rewriteUrl(node.src);
                    if (src !== node.src) {
                        node.src = src;
                        log(`Redirected script src: ${src}`);
                    }
                }
            });
        });
    });

    // Start observing when DOM is ready
    if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
    } else {
        document.addEventListener('DOMContentLoaded', () => {
            observer.observe(document.body, { childList: true, subtree: true });
        });
    }

    log('All interceptors installed and ready');
})();

