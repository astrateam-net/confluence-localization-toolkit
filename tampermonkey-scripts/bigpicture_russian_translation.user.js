// ==UserScript==
// @name         BigPicture Russian Translation Redirect
// @namespace    http://tampermonkey.net/
// @version      1.0.0
// @description  Redirects BigPicture translation requests from en-US to ru-RU to show Russian translations
// @author       AstraTeam
// @match        https://*/rest/softwareplant-bigpicture/*
// @match        https://*/download/resources/eu.softwareplant.bigpicture:static-pages/*
// @match        https://*/plugins/servlet/softwareplant-bigpicture/*
// @grant        none
// @run-at       document-start
// @updateURL    https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation.user.js
// @downloadURL  https://raw.githubusercontent.com/astrateam-net/confluence-localization-toolkit/main/tampermonkey-scripts/bigpicture_russian_translation.user.js
// ==/UserScript==

(function() {
    'use strict';

    console.log('[BigPicture Russian Translation] Script loaded');

    // Intercept fetch API calls
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        let url = args[0];
        
        // Check if this is a BigPicture l10n request with en-US
        if (typeof url === 'string' && url.includes('/system/l10n/en-US')) {
            // Rewrite en-US to ru-RU
            url = url.replace('/system/l10n/en-US', '/system/l10n/ru-RU');
            console.log('[BigPicture Russian Translation] Redirected en-US → ru-RU:', url);
            args[0] = url;
        }
        
        // Also check URL objects
        if (url instanceof Request) {
            const requestUrl = url.url;
            if (requestUrl.includes('/system/l10n/en-US')) {
                const newUrl = requestUrl.replace('/system/l10n/en-US', '/system/l10n/ru-RU');
                console.log('[BigPicture Russian Translation] Redirected Request en-US → ru-RU:', newUrl);
                // Create new Request with modified URL
                args[0] = new Request(newUrl, url);
            }
        }
        
        return originalFetch.apply(this, args);
    };

    // Intercept XMLHttpRequest (for older code that might use it)
    const originalXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        if (typeof url === 'string' && url.includes('/system/l10n/en-US')) {
            url = url.replace('/system/l10n/en-US', '/system/l10n/ru-RU');
            console.log('[BigPicture Russian Translation] XHR Redirected en-US → ru-RU:', url);
        }
        return originalXHROpen.apply(this, [method, url, ...rest]);
    };

    // Also handle case where frontend might construct URL differently
    // Intercept before request is sent
    const originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(...args) {
        if (this.readyState === XMLHttpRequest.OPENED) {
            const url = this.responseURL || this._url;
            if (url && url.includes('/system/l10n/en-US')) {
                const newUrl = url.replace('/system/l10n/en-US', '/system/l10n/ru-RU');
                console.log('[BigPicture Russian Translation] XHR Send Redirected en-US → ru-RU');
                // Can't modify responseURL after open, but we've already intercepted in open()
            }
        }
        return originalSend.apply(this, args);
    };

    console.log('[BigPicture Russian Translation] Interceptors installed');
})();

