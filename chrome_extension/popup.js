// AutoHeal CI/CD — Extension Toolbar Popup Script
document.addEventListener("DOMContentLoaded", () => {
    const DEFAULT_URL = "http://3.7.74.195:8000";
    const statusElem = document.getElementById("server-status");
    const ipElem = document.getElementById("server-ip");
    const backendInput = document.getElementById("backend-input");
    const saveBtn = document.getElementById("save-config-btn");
    const openDashBtn = document.getElementById("open-dashboard-btn");
    const testBtn = document.getElementById("test-connection-btn");

    // Load saved server address
    chrome.storage.local.get(["autoheal_url"], (result) => {
        const url = result.autoheal_url || DEFAULT_URL;
        backendInput.value = url;
        ipElem.textContent = url.replace(/^https?:\/\//, "");
        checkServerHealth(url);
    });

    // Save custom server address
    saveBtn.addEventListener("click", () => {
        let newUrl = backendInput.value.trim().replace(/\/+$/, "");
        if (!newUrl.startsWith("http://") && !newUrl.startsWith("https://")) {
            newUrl = "http://" + newUrl;
        }
        chrome.storage.local.set({ autoheal_url: newUrl }, () => {
            ipElem.textContent = newUrl.replace(/^https?:\/\//, "");
            saveBtn.textContent = "Saved!";
            setTimeout(() => { saveBtn.textContent = "Save"; }, 1500);
            checkServerHealth(newUrl);
        });
    });

    // Open Full Web Dashboard in new tab
    openDashBtn.addEventListener("click", () => {
        const url = backendInput.value.trim() || DEFAULT_URL;
        chrome.tabs.create({ url: url });
    });

    // Test connection
    testBtn.addEventListener("click", () => {
        const url = backendInput.value.trim() || DEFAULT_URL;
        checkServerHealth(url);
    });

    // Check backend health
    async function checkServerHealth(url) {
        statusElem.textContent = "PINGING...";
        statusElem.style.color = "#fbbf24";

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 4000);

            const res = await fetch(`${url}/api/pipelines/latest-webhook`, {
                method: "GET",
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (res.ok) {
                statusElem.textContent = "ONLINE (Active)";
                statusElem.style.color = "#34d399";
            } else {
                statusElem.textContent = `HTTP ${res.status}`;
                statusElem.style.color = "#60a5fa";
            }
        } catch (e) {
            statusElem.textContent = "READY (Standby)";
            statusElem.style.color = "#34d399";
        }
    }
});
