async function checkHealth() {
    const status = document.getElementById("health-status");

    try {
        const response = await fetch("/api/health");
        const data = await response.json();

        if (response.ok && data.status === "healthy") {
            status.textContent = "● System Healthy";
            status.style.background = "#166534";
        } else {
            status.textContent = "● System Error";
        }
    } catch (error) {
        status.textContent = "● System Offline";
        status.style.background = "#991b1b";
    }
}


async function semanticSearch() {
    const query = document.getElementById("search-query").value.trim();
    const resultsContainer = document.getElementById("search-results");

    if (!query) {
        resultsContainer.innerHTML = "<p class='loading'>Enter a search question.</p>";
        return;
    }

    resultsContainer.innerHTML = "<p class='loading'>Searching repository...</p>";

    try {
        const response = await fetch("/api/search/semantic", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query: query,
                path: ".",
                max_results: 5
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Search failed");
        }

        if (!data.results.length) {
            resultsContainer.innerHTML = "<p class='loading'>No matching files found.</p>";
            return;
        }

        resultsContainer.innerHTML = data.results.map(result => `
            <div class="result">
                <strong>${escapeHtml(result.path)}</strong>
                <span class="score">${result.score}</span>
                <br>
                <small>Semantic score: ${result.semantic_score}</small>
            </div>
        `).join("");

    } catch (error) {
        resultsContainer.innerHTML =
            `<p class="loading">Error: ${escapeHtml(error.message)}</p>`;
    }
}


async function askQuestion() {
    const question = document.getElementById("qa-question").value.trim();
    const resultsContainer = document.getElementById("qa-results");

    if (!question) {
        resultsContainer.innerHTML = "<p class='loading'>Enter a question.</p>";
        return;
    }

    resultsContainer.innerHTML =
        "<p class='loading'>Retrieving code and generating AI explanation...</p>";

    try {
        const response = await fetch("/api/qa", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                path: ".",
                max_results: 3
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Q&A request failed");
        }

        const sources = data.results.map(result => `
            <div class="result">
                <strong>${escapeHtml(result.path)}</strong>
                <span class="score">${result.score}</span>
            </div>
        `).join("");

        resultsContainer.innerHTML = `
            <div class="answer">
                ${escapeHtml(data.answer)}
            </div>

            <h3 style="margin-top: 20px;">Retrieved Evidence</h3>
            ${sources}
        `;

    } catch (error) {
        resultsContainer.innerHTML =
            `<p class="loading">Error: ${escapeHtml(error.message)}</p>`;
    }
}


function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


checkHealth();
