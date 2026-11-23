// AutoHeal CI/CD — Extension Background Service Worker (Manifest V3)
// Bypasses Chrome Mixed Content & CORS restrictions when on https://github.com

const DEFAULT_SERVER_URL = "http://3.7.74.195:8000";

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "FETCH_TELEMETRY") {
        const url = request.url || DEFAULT_SERVER_URL;

        Promise.allSettled([
            fetch(`${url}/api/pipelines/latest-webhook`).then(r => r.ok ? r.json() : null),
            fetch(`${url}/api/pipelines/runs?limit=10`).then(r => r.ok ? r.json() : [])
        ]).then(([webhookRes, runsRes]) => {
            const latestWebhook = webhookRes.status === "fulfilled" ? webhookRes.value : null;
            const runs = runsRes.status === "fulfilled" ? runsRes.value : [];
            sendResponse({ success: true, latestWebhook, runs });
        }).catch(err => {
            sendResponse({ success: false, error: err.toString() });
        });

        return true; // Keep message channel open for async response
    }

    if (request.action === "APPLY_HEAL") {
        const url = request.url || DEFAULT_SERVER_URL;
        fetch(`${url}/api/simulate-push`, { method: "POST" })
            .then(r => r.ok ? r.json() : null)
            .then(data => sendResponse({ success: true, data }))
            .catch(err => sendResponse({ success: false, error: err.toString() }));

        return true;
    }
});
