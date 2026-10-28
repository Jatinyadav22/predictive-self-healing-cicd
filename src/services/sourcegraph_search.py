import os
from dotenv import load_dotenv

load_dotenv()
import requests


def get_sourcegraph_url() -> str:
    return os.getenv("SOURCEGRAPH_URL", "http://localhost:7080").rstrip("/")


def get_sourcegraph_token() -> str:
    token = os.getenv("SG_TOKEN") or os.getenv("SOURCEGRAPH_TOKEN")
    if not token:
        try:
            from src.config.settings import settings
            token = getattr(settings, "SOURCEGRAPH_TOKEN", "")
        except Exception:
            token = ""
    return token or ""


def check_sourcegraph_status() -> dict:
    """Checks if the Sourcegraph Docker instance is reachable and authenticated."""
    url = get_sourcegraph_url()
    token = get_sourcegraph_token()

    reachable = False
    status_code = None
    try:
        r = requests.get(f"{url}/healthz", timeout=3)
        status_code = r.status_code
        reachable = r.status_code in (200, 302, 401)
    except Exception:
        # Fallback to localhost if 172.17.0.1 or vice versa
        alt_url = "http://localhost:7080" if "172." in url else "http://172.17.0.1:7080"
        try:
            r = requests.get(f"{alt_url}/healthz", timeout=3)
            status_code = r.status_code
            reachable = r.status_code in (200, 302, 401)
            if reachable:
                url = alt_url
        except Exception:
            pass

    return {
        "reachable": reachable,
        "url": url,
        "token_configured": bool(token and len(token) > 5),
        "status": "ONLINE" if reachable else "OFFLINE",
        "repository": "github.com/Jatinyadav22/predictive-self-healing-cicd",
        "status_code": status_code
    }


def sourcegraph_search(query: str, max_results: int = 10):
    """Search the project repository through Sourcegraph's GraphQL API."""
    graphql_query = """
    query Search($query: String!) {
        search(query: $query) {
            results {
                results {
                    ... on FileMatch {
                        repository {
                            name
                        }
                        file {
                            path
                        }
                        lineMatches {
                            preview
                            lineNumber
                        }
                    }
                }
            }
        }
    }
    """

    token = get_sourcegraph_token()
    url = get_sourcegraph_url()

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"token {token}"

    search_query = query.strip()
    if not any(k in search_query for k in ["repo:", "file:", "context:"]):
        search_query = f"context:global repo:predictive-self-healing-cicd {search_query}"

    try:
        response = requests.post(
            f"{url}/.api/graphql",
            headers=headers,
            json={
                "query": graphql_query,
                "variables": {"query": search_query},
            },
            timeout=10,
        )
    except Exception:
        # Try alternate URL (e.g. 172.17.0.1 or localhost)
        alt_url = "http://localhost:7080" if "172." in url else "http://172.17.0.1:7080"
        try:
            response = requests.post(
                f"{alt_url}/.api/graphql",
                headers=headers,
                json={
                    "query": graphql_query,
                    "variables": {"query": query},
                },
                timeout=10,
            )
        except Exception as e:
            raise RuntimeError(f"Could not connect to Sourcegraph at {url} or {alt_url}: {e}")

    if response.status_code != 200:
        raise RuntimeError(f"Sourcegraph returned HTTP {response.status_code}: {response.text[:200]}")

    data = response.json()

    if "errors" in data and not data.get("data"):
        raise RuntimeError(str(data["errors"]))

    results = []
    items = data.get("data", {}).get("search", {}).get("results", {}).get("results", [])
    for item in items:
        repo_name = item.get("repository", {}).get("name", "github.com/Jatinyadav22/predictive-self-healing-cicd")
        file_path = item.get("file", {}).get("path", "")
        for match in item.get("lineMatches", []):
            results.append({
                "repository": repo_name,
                "path": file_path,
                "line_number": match.get("lineNumber"),
                "preview": match.get("preview", "").strip(),
            })

            if len(results) >= max_results:
                return results

    return results
