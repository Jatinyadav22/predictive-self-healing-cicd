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

async function openSourcegraph() {
    const input = document.getElementById("sourcegraph-query");
    const query = input.value.trim();
    const resultsContainer = document.getElementById("sourcegraph-results");

    if (!query) {
        resultsContainer.innerHTML =
            "<p>Please enter a Sourcegraph search query.</p>";
        return;
    }

    resultsContainer.innerHTML = "<p>Searching Sourcegraph...</p>";

    try {
        const response = await fetch("/api/search/sourcegraph", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                query: query,
                max_results: 10
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Sourcegraph search failed");
        }

        if (!data.results || data.results.length === 0) {
            resultsContainer.innerHTML =
                "<p class='sourcegraph-empty'>No matching results found.</p>";
            return;
        }

        resultsContainer.innerHTML = data.results.map((result, index) => `
            <div class="sourcegraph-result">
                <div class="sourcegraph-result-path">
                    ${escapeHtml(result.path)}
                    <span>Line ${escapeHtml(result.line_number)}</span>
                </div>
                <div class="sourcegraph-result-preview">
                    ${escapeHtml(result.preview)}
                </div>
                <button
                    class="explain-sourcegraph-button"
                    onclick="explainSourcegraphResult(${index})"
                >
                    Explain with AI
                </button>
                <div
                    id="sourcegraph-explanation-${index}"
                    class="sourcegraph-explanation"
                ></div>
            </div>
        `).join("");

        window.sourcegraphResults = data.results;

    } catch (error) {
        resultsContainer.innerHTML =
            `<p class="sourcegraph-error">Error: ${error.message}</p>`;
    }
}


async function explainSourcegraphResult(index) {
    const result = window.sourcegraphResults?.[index];
    const explanationContainer = document.getElementById(
        `sourcegraph-explanation-${index}`
    );

    if (!result || !explanationContainer) {
        return;
    }

    explanationContainer.innerHTML =
        "<p class='loading'>Generating AI explanation...</p>";

    try {
        const response = await fetch("/api/search/sourcegraph/explain", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                repository: result.repository,
                path: result.path,
                line_number: result.line_number,
                preview: result.preview
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "AI explanation failed");
        }

        explanationContainer.innerHTML = `
            <div class="sourcegraph-explanation-content">
                <strong>AI Explanation</strong>
                <p>${escapeHtml(data.explanation)}</p>
            </div>
        `;

    } catch (error) {
        explanationContainer.innerHTML =
            `<p class="sourcegraph-error">Error: ${escapeHtml(error.message)}</p>`;
    }
}

async function askRAG() {
    const question = document.getElementById("rag-question").value.trim();
    const resultsContainer = document.getElementById("rag-results");

    if (!question) {
        resultsContainer.innerHTML =
            "<p class='loading'>Enter a repository question.</p>";
        return;
    }

    resultsContainer.innerHTML =
        "<p class='loading'>Retrieving repository context and generating RAG answer...</p>";

    try {
        const response = await fetch("/api/rag/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                question: question,
                max_results: 3
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "RAG request failed");
        }

        const sources = (data.sources || []).map(source => `
            <div class="rag-source">
                <div class="rag-source-header">
                    <strong>${escapeHtml(source.source)}</strong>
                    <span class="rag-score">
                        Chroma distance: ${escapeHtml(source.score)}
                    </span>
                </div>

                <div class="rag-source-meta">
                    ${escapeHtml(source.file_type || "unknown")}
                </div>

                <pre class="rag-source-content">${escapeHtml(source.content)}</pre>
            </div>
        `).join("");

        resultsContainer.innerHTML = `
            <div class="rag-answer">
                <strong>RAG Answer</strong>
                <p>${escapeHtml(data.answer)}</p>
            </div>

            <h3 class="rag-evidence-title">Retrieved Evidence</h3>

            ${sources || "<p class='loading'>No repository evidence was retrieved.</p>"}
        `;

    } catch (error) {
        resultsContainer.innerHTML =
            `<p class="sourcegraph-error">Error: ${escapeHtml(error.message)}</p>`;
    }
}
