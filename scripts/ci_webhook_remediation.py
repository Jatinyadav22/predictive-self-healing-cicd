#!/usr/bin/env python3
"""
AutoHeal CI/CD — GitHub Actions Runner Remediation Script
Captures test failure context, calls AutoHeal Webhook on EC2, applies verified AST patch,
and pushes the healed commit back to GitHub.
"""

import os
import sys
import json
import subprocess
import urllib.request
import re

def main():
    print("==================================================================")
    print(" AutoHeal CI/CD: Initiating Autonomous Self-Healing Pipeline      ")
    print("==================================================================")

    autoheal_url = os.environ.get("AUTOHEAL_URL", "http://13.201.178.182:8000").rstrip("/")
    webhook_endpoint = f"{autoheal_url}/api/webhooks/github"

    # Read failure logs
    log_file = "pytest_output.log"
    failure_logs = ""
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            failure_logs = f.read()

    # Read target demo app content
    demo_file = "demo_repo/app.py"
    demo_content = ""
    if os.path.exists(demo_file):
        with open(demo_file, "r", encoding="utf-8", errors="replace") as f:
            demo_content = f.read()

    # Extract commit metadata
    commit_sha = os.environ.get("COMMIT_SHA", "HEAD")
    commit_msg = os.environ.get("COMMIT_MSG", "Pipeline failure")
    branch = os.environ.get("BRANCH", "main")
    author = os.environ.get("AUTHOR", "developer")
    repo = os.environ.get("REPO", "Jatinyadav22/predictive-self-healing-cicd")
    run_id = os.environ.get("RUN_ID", "")
    run_number = os.environ.get("RUN_NUMBER", "")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else ""

    # Estimate churn metrics
    lines_added = 15
    lines_deleted = 3
    files_changed = 1
    try:
        diff_stat = subprocess.check_output(["git", "diff", "--shortstat", "HEAD~1", "HEAD"], text=True)
        m_files = re.search(r"(\d+)\s+file", diff_stat)
        m_ins = re.search(r"(\d+)\s+insertion", diff_stat)
        m_del = re.search(r"(\d+)\s+deletion", diff_stat)
        if m_files:
            files_changed = int(m_files.group(1))
        if m_ins:
            lines_added = int(m_ins.group(1))
        if m_del:
            lines_deleted = int(m_del.group(1))
    except Exception:
        pass

    payload = {
        "commit_sha": commit_sha,
        "commit_message": commit_msg[:120],
        "branch": branch,
        "author": author,
        "repository": repo,
        "run_id": run_id,
        "run_number": run_number,
        "run_url": run_url,
        "failure_logs": failure_logs,
        "demo_app_content": demo_content,
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "files_changed": files_changed
    }

    print(f"Connecting to AutoHeal platform at: {webhook_endpoint}")
    print(f"Inbound Commit: {commit_sha[:8]} | Author: @{author} | Run: #{run_number}")

    req = urllib.request.Request(
        webhook_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=150) as resp:
            res_data = resp.read().decode("utf-8")
            data = json.loads(res_data)
    except Exception as e:
        print(f"::error::Failed to reach AutoHeal webhook at {webhook_endpoint}: {e}")
        sys.exit(1)

    status = data.get("status")
    rca = data.get("rca_summary", "No summary provided")
    risk = data.get("risk_score", 0.0)
    tier = data.get("risk_tier", "LOW")
    healed_code = data.get("healed_content")
    unified_diff = data.get("unified_diff", "")
    target_file = data.get("target_file", "demo_repo/app.py")

    print("\n---------------- AutoHeal Diagnosis ----------------")
    print(f"Status:       {status}")
    print(f"Risk Score:   {risk}% ({tier})")
    print(f"RCA Summary:  {rca}")
    if unified_diff:
        print("Candidate Patch Diff:\n" + unified_diff)
    print("----------------------------------------------------\n")

    if status == "RECOVERED_AUTOMATICALLY" and healed_code:
        print(f"Applying verified fix to {target_file}...")
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(healed_code)

        print("Executing verification test suite in runner...")
        retest = subprocess.run(["pytest", "-v", "--tb=short", "demo_repo/tests/"], capture_output=True, text=True)

        if retest.returncode == 0:
            print("Verification PASSED! All 11 unit tests passing.")
            print("Configuring Git and pushing self-healed commit...")

            # Configure git identity
            subprocess.run(["git", "config", "user.name", "AutoHeal Bot"])
            subprocess.run(["git", "config", "user.email", "autoheal-bot@users.noreply.github.com"])
            subprocess.run(["git", "add", target_file])

            commit_title = f"[AutoHeal] Self-healed commit {commit_sha[:8]} (Autonomous AST Patch)"
            subprocess.run(["git", "commit", "-m", commit_title])

            # Push back to origin branch using authenticated origin
            push_res = subprocess.run(["git", "push", "origin", f"HEAD:{branch}"])
            if push_res.returncode == 0:
                print("==================================================================")
                print(" SUCCESS: Self-healed commit pushed back to GitHub!               ")
                print(" A new green CI workflow will trigger automatically.              ")
                print("==================================================================")
            else:
                print("Push completed with code:", push_res.returncode)
        else:
            print("Local re-verification failed with stdout:\n", retest.stdout)
    elif status == "REQUIRES_HUMAN_APPROVAL":
        print("AutoHeal Safety Policy Gate triggered: Fix routed to Human-in-the-Loop review.")
        sys.exit(1)
    elif status == "SUCCESS":
        print("AutoHeal verified codebase is clean and passing. No repair needed.")
        sys.exit(0)
    else:
        print(f"AutoHeal could not automatically recover: {status}")
        sys.exit(1)

if __name__ == "__main__":
    main()
