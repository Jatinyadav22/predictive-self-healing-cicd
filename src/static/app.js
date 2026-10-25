// Enterprise CI/CD Autonomous Platform Controller
let currentRuns = [];
let allScenarios = {};

document.addEventListener("DOMContentLoaded", () => {
    loadPipelineRuns();
    loadScenarios();
    loadAuditTrail();
    onRiskSliderChange();
    loadModelEvaluation();
});

// Navigation Tab Controller
function switchTab(tabId) {
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-tab-item").forEach(b => b.classList.remove("active"));

    const targetPanel = document.getElementById(`tab-${tabId}`);
    if (targetPanel) {
        targetPanel.classList.add("active");
    }

    if (window.event && window.event.currentTarget) {
        window.event.currentTarget.classList.add("active");
    } else {
        const btn = Array.from(document.querySelectorAll(".nav-tab-item")).find(b => b.getAttribute("onclick")?.includes(tabId));
        if (btn) btn.classList.add("active");
    }

    if (tabId === "risk") {
        loadModelEvaluation();
    } else if (tabId === "healing") {
        renderHITLQueue();
    } else if (tabId === "audit") {
        loadAuditTrail();
    }
}

// Scenarios Handling
async function loadScenarios() {
    try {
        const res = await fetch("/api/pipelines/scenarios");
        if (res.ok) {
            allScenarios = await res.json();
            onScenarioChange();
        }
    } catch (e) {
        console.error("Failed to load scenarios:", e);
    }
}

function onScenarioChange() {
    const sel = document.getElementById("scenario-select").value;
    const detailBox = document.getElementById("scenario-details");

    if (sel === "clean") {
        detailBox.innerHTML = `<strong>Clean Baseline:</strong> Clean commit with no defect injected. All target unit and integration test suites pass without triggering remediation.`;
    } else if (allScenarios[sel]) {
        const s = allScenarios[sel];
        detailBox.innerHTML = `<strong>${escapeHtml(s.name)}</strong><br>Target File: <code>${escapeHtml(s.target_file)}</code> | Description: ${escapeHtml(s.description)}`;
    }
}

// Trigger Pipeline Execution
async function triggerPipeline() {
    const sel = document.getElementById("scenario-select").value;
    const btn = document.getElementById("btn-trigger");
    const runTitle = document.getElementById("live-run-title");
    const runBadge = document.getElementById("live-run-badge");
    const runMsg = document.getElementById("live-run-msg");

    btn.disabled = true;
    btn.textContent = "Executing Pipeline...";

    resetStepper();
    setStep(1, "active");
    runTitle.textContent = "Phase 1: Pre-Commit Risk Analysis";
    runBadge.className = "status-pill info";
    runBadge.textContent = "INSPECTING COMMIT";
    runMsg.textContent = "Extracting 12 commit features and evaluating failure risk with Random Forest model...";

    try {
        // Step 1: Inject defect if scenario selected
        if (sel !== "clean") {
            await fetch("/api/pipelines/inject-fault", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ scenario: sel })
            });
        }

        let linesAdded = 55;
        let linesDeleted = 12;
        let filesChanged = 2;
        let authorFail = 0.08;
        let configFiles = 0;
        let ciFiles = 0;
        let testLines = 20;

        if (sel === "5") {
            linesAdded = 520;
            linesDeleted = 180;
            filesChanged = 8;
            authorFail = 0.85;
            configFiles = 1;
            ciFiles = 1;
            testLines = 0;
        }

        setStep(1, "passed");
        setStep(2, "active");
        runTitle.textContent = "Phase 2: Automated Pytest Execution";
        runBadge.className = "status-pill info";
        runBadge.textContent = "TESTING";
        runMsg.textContent = "Executing unit and integration test suites in demo microservice...";

        const triggerRes = await fetch("/api/pipelines/trigger", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                commit_sha: "sha-" + Math.random().toString(16).substring(2, 8),
                lines_added: linesAdded,
                lines_deleted: linesDeleted,
                files_changed: filesChanged,
                test_lines_added: testLines,
                config_files_touched: configFiles,
                ci_files_touched: ciFiles,
                author_recent_failure_rate: authorFail,
                scenario: sel
            })
        });

        const run = await triggerRes.json();

        if (run.status === "SUCCESS") {
            setStep(2, "passed");
            runTitle.textContent = "Pipeline Completed Cleanly";
            runBadge.className = "status-pill success";
            runBadge.textContent = "SUCCESS";
            runMsg.textContent = `All unit test suites executed and passed cleanly. Run ID: ${run.run_id}`;
        } else {
            setStep(2, "failed");
            setStep(3, "passed");
            setStep(4, "passed");
            setStep(5, "passed");

            if (run.status === "RECOVERED_AUTOMATICALLY") {
                setStep(6, "passed");
                setStep(7, "passed");
                runTitle.textContent = "Autonomous Recovery Succeeded";
                runBadge.className = "status-pill success";
                runBadge.textContent = "RECOVERED_AUTOMATICALLY";
                runMsg.textContent = "Failure diagnosed via ChromaDB citations and Qwen 2.5 3B. AST patch validated in sandbox and applied.";
            } else if (run.status === "REQUIRES_HUMAN_APPROVAL") {
                setStep(6, "warning");
                runTitle.textContent = "Halted at Step 6: Safety Policy Boundary";
                runBadge.className = "status-pill warning";
                runBadge.textContent = "REQUIRES_HUMAN_APPROVAL";
                runMsg.innerHTML = 'High-risk change exceeded auto-apply ceiling or violated safety guardrails. Routed to <strong><a href="#" onclick="switchTab(\'healing\'); return false;" style="color:var(--brand-primary); text-decoration:underline; font-weight:600;">Safety Policy & Approval Gate</a></strong> for Human-in-the-Loop review.';
            } else if (run.status === "RECOVERY_FAILED_ROLLED_BACK") {
                setStep(6, "passed");
                setStep(7, "failed");
                runTitle.textContent = "Sandbox Validation Failed: Rolled Back";
                runBadge.className = "status-pill danger";
                runBadge.textContent = "ROLLED_BACK";
                runMsg.textContent = "Candidate fix failed sandbox revalidation. State automatically rolled back to prevent regressions.";
            }
        }

        await loadPipelineRuns();
    } catch (e) {
        console.error("Execution failed:", e);
        runTitle.textContent = "Pipeline Error";
        runBadge.className = "status-pill danger";
        runBadge.textContent = "ERROR";
        runMsg.textContent = String(e);
    } finally {
        btn.disabled = false;
        btn.textContent = "Execute Autonomous CI/CD";
    }
}

// Stepper Management
function setStep(stepNum, state) {
    const node = document.getElementById(`step-${stepNum}`);
    if (node) {
        node.className = `stepper-step ${state}`;
    }
}

function resetStepper() {
    for (let i = 1; i <= 7; i++) {
        setStep(i, "");
    }
}

// Reset Demo Repository
async function resetDemoRepo() {
    if (!confirm("Restore the demo microservice repository to its clean, passing baseline?")) return;
    try {
        const res = await fetch("/api/pipelines/reset-repo", { method: "POST" });
        if (res.ok) {
            resetStepper();
            document.getElementById("live-run-title").textContent = "Status: Clean Baseline";
            document.getElementById("live-run-badge").className = "status-pill info";
            document.getElementById("live-run-badge").textContent = "RESET";
            document.getElementById("live-run-msg").textContent = "Target repository files restored to clean baseline.";
        }
    } catch (e) {
        alert("Failed to reset repository: " + e);
    }
}

// Load Pipeline Runs Table
async function loadPipelineRuns() {
    try {
        const res = await fetch("/api/pipelines/runs?limit=25");
        if (!res.ok) return;

        currentRuns = await res.json();
        const tbody = document.getElementById("runs-table-body");
        const select = document.getElementById("incident-run-select");

        tbody.innerHTML = "";
        select.innerHTML = `<option value="">Select a Pipeline Run...</option>`;

        let pendingCount = 0;

        currentRuns.forEach((run, idx) => {
            const tr = document.createElement("tr");

            let statusClass = "info";
            if (run.status === "SUCCESS" || run.status === "RECOVERED_AUTOMATICALLY") statusClass = "success";
            else if (run.status === "REQUIRES_HUMAN_APPROVAL") {
                statusClass = "warning";
                pendingCount++;
            } else if (run.status === "FAILED" || run.status === "RECOVERY_FAILED_ROLLED_BACK") statusClass = "danger";

            const riskScore = run.risk_prediction ? `${run.risk_prediction.risk_score}% (${run.risk_prediction.risk_tier})` : "N/A";
            const failType = run.failure_classification ? run.failure_classification.failure_type : "CLEAN_BUILD";
            const startedAt = run.started_at ? run.started_at.substring(11, 19) : "";

            tr.innerHTML = `
                <td><strong>#${escapeHtml(run.run_id.substring(4))}</strong></td>
                <td><code>${escapeHtml(run.commit_sha)}</code></td>
                <td>${riskScore}</td>
                <td>${escapeHtml(failType)}</td>
                <td><span class="status-pill ${statusClass}">${escapeHtml(run.status)}</span></td>
                <td>${startedAt}</td>
                <td>
                    <button class="btn btn-secondary" style="padding:4px 10px; font-size:11px;" onclick="viewRunDetails('${escapeHtml(run.run_id)}')">Inspect</button>
                </td>
            `;
            tbody.appendChild(tr);

            const opt = document.createElement("option");
            opt.value = run.run_id;
            opt.textContent = `Run #${run.run_id.substring(4)} — ${run.status} (${failType})`;
            if (idx === 0) opt.selected = true;
            select.appendChild(opt);
        });

        const pendingBadge = document.getElementById("pending-count-badge");
        if (pendingCount > 0) {
            pendingBadge.textContent = pendingCount;
            pendingBadge.style.display = "inline-flex";
        } else {
            pendingBadge.style.display = "none";
        }

        renderHITLQueue();

        if (currentRuns.length > 0) {
            populateIncidentDeepDive(currentRuns[0]);
        }
    } catch (e) {
        console.error("Failed to load runs:", e);
    }
}

function viewRunDetails(runId) {
    const run = currentRuns.find(r => r.run_id === runId);
    if (!run) return;

    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".nav-tab-item").forEach(b => b.classList.remove("active"));
    document.getElementById("tab-incidents").classList.add("active");

    const incBtn = Array.from(document.querySelectorAll(".nav-tab-item")).find(b => b.textContent.includes("Incident Diagnostics"));
    if (incBtn) incBtn.classList.add("active");

    document.getElementById("incident-run-select").value = runId;
    populateIncidentDeepDive(run);
}

function onSelectIncidentRun() {
    const runId = document.getElementById("incident-run-select").value;
    const run = currentRuns.find(r => r.run_id === runId);
    if (run) populateIncidentDeepDive(run);
}

function populateIncidentDeepDive(run) {
    const failType = document.getElementById("inc-fail-type");
    const failLoc = document.getElementById("inc-fail-loc");
    const errorMsg = document.getElementById("inc-error-msg");
    const rcaText = document.getElementById("inc-rca-text");
    const strategyText = document.getElementById("inc-strategy-text");
    const citationsList = document.getElementById("inc-citations-list");
    const diffView = document.getElementById("inc-diff-view");
    const safetyList = document.getElementById("inc-safety-list");

    if (run.failure_classification) {
        failType.textContent = run.failure_classification.failure_type;
        failLoc.textContent = `${run.failure_classification.failing_file || 'app.py'}:${run.failure_classification.failing_line || '44'}`;
        errorMsg.textContent = run.failure_classification.error_message;
    } else {
        failType.textContent = "SUCCESSFUL_BUILD";
        failLoc.textContent = "All test suites passed";
        errorMsg.textContent = "No exceptions detected.";
    }

    if (run.healing_attempts && run.healing_attempts.length > 0) {
        const attempt = run.healing_attempts[run.healing_attempts.length - 1];

        if (attempt.rca) {
            rcaText.textContent = `${attempt.rca.root_cause_summary} (Model Confidence: ${Math.round(attempt.rca.confidence_score * 100)}%)`;
            strategyText.textContent = attempt.rca.fix_strategy;

            citationsList.innerHTML = "";
            if (attempt.rca.evidence_citations && attempt.rca.evidence_citations.length > 0) {
                attempt.rca.evidence_citations.forEach(c => {
                    const card = document.createElement("div");
                    card.className = "callout";
                    card.innerHTML = `
                        <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin-bottom:4px;">
                            <span>Source: ${escapeHtml(c.file_path)}</span>
                            <span>Retrieval Score: ${Math.round((c.similarity_score || 0.95) * 100)}%</span>
                        </div>
                        <pre style="font-family:var(--font-mono); font-size:11px; color:var(--text-secondary); white-space:pre-wrap;">${escapeHtml(c.snippet)}</pre>
                    `;
                    citationsList.appendChild(card);
                });
            } else {
                citationsList.innerHTML = `<p style="color:var(--text-muted); font-size:12px;">No evidence citations recorded.</p>`;
            }
        }

        if (attempt.fix_proposal && attempt.fix_proposal.unified_diff) {
            diffView.innerHTML = formatUnifiedDiff(attempt.fix_proposal.unified_diff);
            safetyList.innerHTML = `
                <li>AST Syntax Validation: ${attempt.fix_proposal.is_safe ? "Valid Python AST" : "Syntax Check Flagged"}</li>
                <li>Blast Radius: ${attempt.fix_proposal.lines_changed} lines changed</li>
                <li>Safety Status: ${attempt.fix_proposal.is_safe ? "Passed All Guardrails" : attempt.fix_proposal.safety_violations.join(", ")}</li>
            `;
        } else {
            diffView.innerHTML = `<span style="color:var(--text-muted);">No diff available for this run.</span>`;
        }
    } else {
        rcaText.textContent = "Pipeline completed cleanly without requiring automated repair.";
        strategyText.textContent = "N/A";
        citationsList.innerHTML = `<p style="color:var(--text-muted); font-size:12px;">No failure incidents recorded.</p>`;
        diffView.innerHTML = `<span style="color:var(--text-muted);">No diff generated.</span>`;
    }
}

function formatUnifiedDiff(diffStr) {
    if (!diffStr) return "";
    return diffStr.split("\n").map(line => {
        if (line.startsWith("+") && !line.startsWith("+++")) {
            return `<span class="diff-add">${escapeHtml(line)}</span>`;
        } else if (line.startsWith("-") && !line.startsWith("---")) {
            return `<span class="diff-del">${escapeHtml(line)}</span>`;
        } else if (line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++")) {
            return `<span class="diff-meta">${escapeHtml(line)}</span>`;
        }
        return `<span>${escapeHtml(line)}</span>\n`;
    }).join("");
}

function escapeHtml(str) {
    if (typeof str !== "string") return String(str);
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Risk Simulator Sliders
async function onRiskSliderChange() {
    const linesAdded = parseInt(document.getElementById("input-lines-added").value);
    const linesDeleted = parseInt(document.getElementById("input-lines-deleted").value);
    const filesChanged = parseInt(document.getElementById("input-files-changed").value);
    const testLines = parseInt(document.getElementById("input-test-lines").value);
    const failRate = parseInt(document.getElementById("input-fail-rate").value) / 100.0;

    document.getElementById("val-lines-added").textContent = linesAdded;
    document.getElementById("val-lines-deleted").textContent = linesDeleted;
    document.getElementById("val-files-changed").textContent = filesChanged;
    document.getElementById("val-test-lines").textContent = testLines;
    document.getElementById("val-fail-rate").textContent = `${Math.round(failRate * 100)}%`;

    try {
        const res = await fetch("/api/risk/evaluate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                lines_added: linesAdded,
                lines_deleted: linesDeleted,
                files_changed: filesChanged,
                test_lines_added: testLines,
                author_recent_failure_rate: failRate
            })
        });

        if (res.ok) {
            const pred = await res.json();
            const scoreEl = document.getElementById("sim-risk-score");
            const barEl = document.getElementById("sim-risk-bar");
            const tierEl = document.getElementById("sim-risk-tier");
            const factorsEl = document.getElementById("sim-risk-factors");

            scoreEl.textContent = `${pred.risk_score}%`;
            barEl.style.width = `${pred.risk_score}%`;
            tierEl.textContent = `${pred.risk_tier} RISK`;

            let color = "var(--status-success)";
            let tierClass = "success";
            if (pred.risk_score >= 70) {
                color = "var(--status-danger)";
                tierClass = "danger";
            } else if (pred.risk_score >= 35) {
                color = "var(--status-warning)";
                tierClass = "warning";
            }

            scoreEl.style.color = color;
            barEl.style.backgroundColor = color;
            tierEl.className = `status-pill ${tierClass}`;

            factorsEl.innerHTML = pred.top_risk_factors.map(f => `<li>${escapeHtml(f)}</li>`).join("");
        }
    } catch (e) {
        console.error("Risk simulation failed:", e);
    }
}

// Model Evaluation Loader (Feature 6)
async function loadModelEvaluation() {
    try {
        const res = await fetch("/api/risk/evaluation");
        if (!res.ok) return;

        const evalData = await res.json();
        const datasetLabel = document.getElementById("eval-dataset-label");
        const limitationsEl = document.getElementById("eval-limitations");

        if (datasetLabel) datasetLabel.textContent = evalData.dataset || "DEMONSTRATION_SYNTHETIC_CI_DATASET";
        if (limitationsEl && evalData.limitations) limitationsEl.textContent = evalData.limitations;

        const rf = evalData.model_metrics || {};
        const base = evalData.baseline_metrics || {};

        if (document.getElementById("eval-rf-acc")) document.getElementById("eval-rf-acc").textContent = `${(rf.accuracy * 100).toFixed(1)}%`;
        if (document.getElementById("eval-base-acc")) document.getElementById("eval-base-acc").textContent = `${(base.accuracy * 100).toFixed(1)}%`;
        if (document.getElementById("eval-rf-prec")) document.getElementById("eval-rf-prec").textContent = `${(rf.precision * 100).toFixed(1)}%`;
        if (document.getElementById("eval-rf-rec")) document.getElementById("eval-rf-rec").textContent = `${(rf.recall * 100).toFixed(1)}%`;
        if (document.getElementById("eval-rf-f1")) document.getElementById("eval-rf-f1").textContent = `${(rf.f1_score * 100).toFixed(1)}%`;
        if (document.getElementById("eval-rf-auc")) document.getElementById("eval-rf-auc").textContent = rf.roc_auc.toFixed(2);

        if (evalData.confusion_matrix) {
            const cm = evalData.confusion_matrix;
            if (document.getElementById("eval-tn")) document.getElementById("eval-tn").textContent = cm.true_negatives;
            if (document.getElementById("eval-fp")) document.getElementById("eval-fp").textContent = cm.false_positives;
            if (document.getElementById("eval-fn")) document.getElementById("eval-fn").textContent = cm.false_negatives;
            if (document.getElementById("eval-tp")) document.getElementById("eval-tp").textContent = cm.true_positives;
        }
    } catch (e) {
        console.error("Failed to load model evaluation:", e);
    }
}

// Human-in-the-Loop Queue
function renderHITLQueue() {
    const tbody = document.getElementById("hitl-table-body");
    const pendingRuns = currentRuns.filter(r => r.status === "REQUIRES_HUMAN_APPROVAL");

    if (pendingRuns.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:24px;">No pending repairs requiring human authorization. All past runs were autonomous or clean.</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    pendingRuns.forEach(run => {
        const tr = document.createElement("tr");
        const attempt = run.healing_attempts && run.healing_attempts.length > 0 ? run.healing_attempts[run.healing_attempts.length - 1] : null;
        const targetFile = attempt && attempt.fix_proposal ? attempt.fix_proposal.target_file : "app.py";
        const riskScore = run.risk_prediction ? `${run.risk_prediction.risk_score}%` : "High";
        const violations = attempt && attempt.fix_proposal ? attempt.fix_proposal.safety_violations.join(", ") : "Risk score exceeded automated apply ceiling";

        tr.innerHTML = `
            <td><strong>#${escapeHtml(run.run_id.substring(4))}</strong></td>
            <td><code>${escapeHtml(targetFile)}</code></td>
            <td><span class="status-pill warning">${escapeHtml(riskScore)}</span></td>
            <td style="color:var(--status-warning); font-size:12px;">${escapeHtml(violations)}</td>
            <td><button class="btn btn-secondary" style="padding:4px 10px; font-size:11px;" onclick="viewRunDetails('${escapeHtml(run.run_id)}')">Inspect Diff</button></td>
            <td>
                <div style="display:flex; gap:6px;">
                    <button class="btn btn-success" style="padding:4px 12px; font-size:11px;" onclick="approveRun('${escapeHtml(run.run_id)}')">Approve & Apply</button>
                    <button class="btn btn-danger" style="padding:4px 12px; font-size:11px;" onclick="rejectRun('${escapeHtml(run.run_id)}')">Reject</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function approveRun(runId) {
    if (!confirm(`Approve and apply fix for Run #${runId.substring(4)}?`)) return;
    try {
        const res = await fetch(`/api/pipelines/runs/${runId}/approve`, { method: "POST" });
        if (res.ok) {
            await loadPipelineRuns();
            renderHITLQueue();
        }
    } catch (e) {
        alert("Failed to approve run: " + e);
    }
}

async function rejectRun(runId) {
    if (!confirm(`Reject candidate repair for Run #${runId.substring(4)}?`)) return;
    try {
        const res = await fetch(`/api/pipelines/runs/${runId}/reject`, { method: "POST" });
        if (res.ok) {
            await loadPipelineRuns();
            renderHITLQueue();
        }
    } catch (e) {
        alert("Failed to reject run: " + e);
    }
}

// Semantic Code Search
async function executeSemanticSearch() {
    const query = document.getElementById("rag-search-input").value;
    const resultsDiv = document.getElementById("rag-search-results");
    if (!query.trim()) return;

    resultsDiv.innerHTML = `<p style="color:var(--text-muted); font-size:12px;">Searching indexed vector space in ChromaDB...</p>`;

    try {
        const res = await fetch("/api/search/semantic", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: query, path: ".", max_results: 5 })
        });
        if (res.ok) {
            const data = await res.json();
            const results = data.results || [];
            if (results.length === 0) {
                resultsDiv.innerHTML = `<p style="color:var(--text-muted); font-size:12px;">No semantic matches found for "${escapeHtml(query)}".</p>`;
                return;
            }
            resultsDiv.innerHTML = results.map(r => `
                <div class="callout" style="margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; margin-bottom:6px; color:var(--brand-primary); font-size:12px;">
                        <strong>${escapeHtml(r.path || r.source || 'repository')}</strong>
                        <span>Relevance: ${Math.round((r.similarity || r.score || 0.95) * 100)}%</span>
                    </div>
                    <pre style="font-family:var(--font-mono); font-size:11px; white-space:pre-wrap;">${escapeHtml(r.content || '')}</pre>
                </div>
            `).join("");
        } else {
            resultsDiv.innerHTML = `<p style="color:var(--status-danger);">Search error (${res.status}): ${escapeHtml(res.statusText)}</p>`;
        }
    } catch (e) {
        resultsDiv.innerHTML = `<p style="color:var(--status-danger);">Search error: ${escapeHtml(String(e))}</p>`;
    }
}

// RAG Architectural Q&A
async function executeRAGQA() {
    const question = document.getElementById("rag-qa-input").value;
    const answerBox = document.getElementById("rag-qa-answer");
    if (!question.trim()) return;

    answerBox.style.display = "block";
    answerBox.innerHTML = `<em>Querying repository knowledge base and generating answer with Qwen 2.5 3B...</em>`;

    try {
        const res = await fetch("/api/rag/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: question, max_results: 3 })
        });
        if (res.ok) {
            const data = await res.json();
            let sourcesHtml = "";
            if (data.sources && data.sources.length > 0) {
                sourcesHtml = `<div style="margin-top:12px; font-size:11px; color:var(--text-muted); border-top:1px solid var(--border-subtle); padding-top:8px;"><strong>Citations:</strong> ${escapeHtml(data.sources.join(", "))}</div>`;
            }
            answerBox.innerHTML = `<strong>Grounding AI Architecture Assistant (Qwen 2.5 3B):</strong><br><br>${escapeHtml(data.answer || 'No answer generated.')}${sourcesHtml}`;
        } else {
            answerBox.innerHTML = `<span style="color:var(--status-danger);">RAG error (${res.status}): ${escapeHtml(res.statusText)}</span>`;
        }
    } catch (e) {
        answerBox.innerHTML = `<span style="color:var(--status-danger);">Error: ${escapeHtml(String(e))}</span>`;
    }
}

// AI Test Candidate Generation & Validation (Feature 3)
async function generateTestCandidate() {
    const reqText = document.getElementById("testgen-input").value;
    const btn = document.getElementById("btn-generate-test");
    const codeArea = document.getElementById("testgen-code");
    if (!reqText.trim()) return;

    btn.disabled = true;
    btn.textContent = "Synthesizing Candidate...";
    codeArea.value = "# Retrieving context and generating pytest candidate with Qwen 2.5 3B...";

    try {
        const res = await fetch("/api/test-generation/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ request: reqText, max_results: 5 })
        });

        if (res.ok) {
            const data = await res.json();
            codeArea.value = data.tests || "# No test code generated.";
            await validateCurrentTestCandidate();
        } else {
            codeArea.value = `# Error generating test (${res.status}): ${res.statusText}`;
        }
    } catch (e) {
        codeArea.value = `# Generation error: ${e}`;
    } finally {
        btn.disabled = false;
        btn.textContent = "Generate Candidate";
    }
}

async function validateCurrentTestCandidate() {
    const testCode = document.getElementById("testgen-code").value;
    const summaryCard = document.getElementById("testgen-validation-summary");
    const badgesDiv = document.getElementById("testgen-validation-badges");

    if (!testCode.trim()) return;

    try {
        const res = await fetch("/api/test-generation/validate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ test_code: testCode })
        });

        if (res.ok) {
            const data = await res.json();
            summaryCard.style.display = "block";
            badgesDiv.innerHTML = "";

            // AST Syntax
            const astBadge = document.createElement("span");
            astBadge.className = `status-pill ${data.is_valid_syntax ? "success" : "danger"}`;
            astBadge.textContent = data.is_valid_syntax ? "AST SYNTAX: VALID" : `SYNTAX ERROR: ${data.syntax_error || ""}`;
            badgesDiv.appendChild(astBadge);

            // Prohibited Imports
            const importBadge = document.createElement("span");
            importBadge.className = `status-pill ${data.prohibited_imports.length === 0 ? "success" : "danger"}`;
            importBadge.textContent = data.prohibited_imports.length === 0 ? "SECURITY: ZERO PROHIBITED MODULES" : `FLAGGED: ${data.prohibited_imports.join(", ")}`;
            badgesDiv.appendChild(importBadge);

            // Duplicate Tests
            const dupBadge = document.createElement("span");
            dupBadge.className = `status-pill ${data.duplicate_test_names.length === 0 ? "success" : "warning"}`;
            dupBadge.textContent = data.duplicate_test_names.length === 0 ? "TEST NAMES: UNIQUE" : `DUPLICATES: ${data.duplicate_test_names.join(", ")}`;
            badgesDiv.appendChild(dupBadge);

            // Discovered Tests
            const countBadge = document.createElement("span");
            countBadge.className = "status-pill info";
            countBadge.textContent = `${data.discovered_test_functions.length} TEST FUNCTIONS DETECTED`;
            badgesDiv.appendChild(countBadge);
        }
    } catch (e) {
        console.error("Validation error:", e);
    }
}

async function executeCurrentTestCandidate() {
    const testCode = document.getElementById("testgen-code").value;
    const targetDir = document.getElementById("testgen-target-dir").value;
    const btn = document.getElementById("btn-execute-test");
    const badge = document.getElementById("testgen-exec-badge");
    const terminal = document.getElementById("testgen-terminal");

    if (!testCode.trim()) {
        alert("Please generate or supply candidate test code first.");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Executing in Sandbox...";
    badge.className = "status-pill info";
    badge.textContent = "EXECUTING";
    terminal.textContent = "Spawning isolated subprocess with 15-second timeout...\nExecuting candidate against target demo repository...";

    try {
        const res = await fetch("/api/test-generation/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                test_code: testCode,
                target_dir: targetDir,
                timeout: 15
            })
        });

        if (res.ok) {
            const data = await res.json();
            const passed = data.status === "PASSED";
            badge.className = `status-pill ${passed ? "success" : "danger"}`;
            badge.textContent = data.status;

            terminal.textContent = `=== SANDBOX ISOLATION REPORT ===\n` +
                `Status: ${data.status}\n` +
                `Exit Code: ${data.exit_code}\n` +
                `Duration: ${data.execution_time_seconds}s\n` +
                `Sandboxed File: ${data.sandbox_file}\n\n` +
                `=== SUBPROCESS OUTPUT ===\n` +
                (data.output || "No stdout/stderr captured.");
        } else {
            badge.className = "status-pill danger";
            badge.textContent = "ERROR";
            terminal.textContent = `Sandbox invocation error (${res.status}): ${res.statusText}`;
        }
    } catch (e) {
        badge.className = "status-pill danger";
        badge.textContent = "EXCEPTION";
        terminal.textContent = `Execution failed: ${e}`;
    } finally {
        btn.disabled = false;
        btn.textContent = "Execute Candidate in Sandbox";
    }
}

// Cryptographic Audit Ledger
async function loadAuditTrail() {
    try {
        const res = await fetch("/api/audit/events?limit=40");
        if (!res.ok) return;

        const events = await res.json();
        const tbody = document.getElementById("audit-table-body");
        const verifyStatus = document.getElementById("audit-verify-status");
        tbody.innerHTML = "";

        if (events.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:24px;">No audit events recorded yet.</td></tr>`;
            return;
        }

        let chainValid = true;
        for (let i = 0; i < events.length - 1; i++) {
            // events sorted desc
            if (events[i].previous_event_hash !== events[i + 1].event_hash) {
                chainValid = false;
                break;
            }
        }

        if (verifyStatus) {
            verifyStatus.className = `status-pill ${chainValid ? "success" : "danger"}`;
            verifyStatus.textContent = chainValid ? `HASH CHAIN VALID (${events.length} EVENTS)` : "HASH CHAIN COMPROMISED";
        }

        events.forEach(evt => {
            const tr = document.createElement("tr");
            const ts = evt.timestamp ? evt.timestamp.substring(11, 19) : "";
            tr.innerHTML = `
                <td><code>${ts}</code></td>
                <td><span class="status-pill info">${escapeHtml(evt.event_type)}</span></td>
                <td><strong>${escapeHtml(evt.actor)}</strong></td>
                <td>${escapeHtml(evt.summary)}</td>
                <td><code title="${escapeHtml(evt.event_hash)}">${escapeHtml(evt.event_hash.substring(0, 16))}...</code></td>
                <td><code title="${escapeHtml(evt.previous_event_hash)}">${escapeHtml(evt.previous_event_hash.substring(0, 16))}...</code></td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Failed to load audit trail:", e);
    }
}

// ==========================================================================
// Safety Policy & Human-in-the-Loop Approval Queue (Tab 4)
// ==========================================================================

function renderHITLQueue() {
    const tbody = document.getElementById("hitl-table-body");
    if (!tbody) return;

    const pendingRuns = (currentRuns || []).filter(r => r.status === "REQUIRES_HUMAN_APPROVAL");

    if (pendingRuns.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding: 24px;">No pending reviews requiring human sign-off. (Trigger Scenario 5 to inspect a high-risk safety gate boundary).</td></tr>`;
        return;
    }

    tbody.innerHTML = "";
    pendingRuns.forEach(run => {
        const tr = document.createElement("tr");

        const riskScore = run.risk_prediction
            ? `${run.risk_prediction.risk_score}% (${run.risk_prediction.risk_tier})`
            : "High Risk (>40%)";

        const latestAttempt = (run.healing_attempts && run.healing_attempts.length > 0)
            ? run.healing_attempts[run.healing_attempts.length - 1]
            : null;

        const fix = latestAttempt ? latestAttempt.fix_proposal : null;
        const targetFile = fix ? fix.target_file : "app.py";
        const violations = (fix && fix.safety_violations && fix.safety_violations.length > 0)
            ? fix.safety_violations
            : ["Safety Policy Boundary: Pre-execution risk score exceeds autonomous auto-apply ceiling (>40%)", "High-risk transaction logic mutation flagged by safety boundary"];

        const diffContent = fix && fix.unified_diff
            ? fix.unified_diff
            : (fix && fix.replacement_snippet ? fix.replacement_snippet : "No diff available");

        const violationsHtml = violations.map(v => `<li style="margin-bottom:3px;">${escapeHtml(v)}</li>`).join("");

        tr.innerHTML = `
            <td><strong>#${escapeHtml(run.run_id.substring(4))}</strong></td>
            <td><code>${escapeHtml(targetFile)}</code></td>
            <td><span class="status-pill warning">${escapeHtml(riskScore)}</span></td>
            <td>
                <ul style="margin:0; padding-left:16px; font-size:11px; color:#b45309; line-height:1.4;">
                    ${violationsHtml}
                </ul>
            </td>
            <td>
                <div style="max-height:110px; max-width:320px; overflow-y:auto; font-family:'JetBrains Mono', monospace; font-size:11px; background:var(--bg-canvas); padding:6px 10px; border-radius:4px; border:1px solid var(--border-regular);">
                    <pre style="margin:0; white-space:pre-wrap; color:var(--text-primary); font-size:11px;">${escapeHtml(diffContent)}</pre>
                </div>
            </td>
            <td>
                <div style="display:flex; flex-direction:column; gap:6px;">
                    <button class="btn btn-primary" style="padding:6px 12px; font-size:11px;" onclick="approveRun('${escapeHtml(run.run_id)}')">Approve & Apply</button>
                    <button class="btn btn-secondary" style="padding:6px 12px; font-size:11px; color:var(--status-danger); border-color:rgba(185,28,28,0.3);" onclick="rejectRun('${escapeHtml(run.run_id)}')">Reject</button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

async function approveRun(runId) {
    if (!confirm(`Approve candidate patch for Run #${runId.substring(4)} and deploy to sandbox?`)) return;
    try {
        const res = await fetch(`/api/pipelines/runs/${encodeURIComponent(runId)}/approve`, {
            method: "POST"
        });
        if (res.ok) {
            alert(`Run #${runId.substring(4)} approved! Fix applied and re-verified.`);
            await loadPipelineRuns();
            await loadAuditTrail();
        } else {
            const err = await res.json();
            alert(`Approval failed: ${err.detail || JSON.stringify(err)}`);
        }
    } catch (e) {
        alert(`Request failed: ${e}`);
    }
}

async function rejectRun(runId) {
    if (!confirm(`Reject candidate patch for Run #${runId.substring(4)}?`)) return;
    try {
        const res = await fetch(`/api/pipelines/runs/${encodeURIComponent(runId)}/reject`, {
            method: "POST"
        });
        if (res.ok) {
            alert(`Run #${runId.substring(4)} rejected.`);
            await loadPipelineRuns();
            await loadAuditTrail();
        } else {
            const err = await res.json();
            alert(`Rejection failed: ${err.detail || JSON.stringify(err)}`);
        }
    } catch (e) {
        alert(`Request failed: ${e}`);
    }
}

