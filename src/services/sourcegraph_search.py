import os
from dotenv import load_dotenv

load_dotenv()
import requests


SOURCEGRAPH_URL = os.getenv("SOURCEGRAPH_URL", "http://172.17.0.1:7080")


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

    token = os.getenv("SG_TOKEN")
    if not token:
        raise RuntimeError("SG_TOKEN is not set")

    response = requests.post(
        f"{SOURCEGRAPH_URL}/.api/graphql",
        headers={
            "Authorization": f"token {token}",
            "Content-Type": "application/json",
        },
        json={
            "query": graphql_query,
            "variables": {"query": query},
        },
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(str(data["errors"]))

    results = []

    for item in data.get("data", {}).get("search", {}).get("results", {}).get("results", []):
        for match in item.get("lineMatches", []):
            results.append({
                "repository": item.get("repository", {}).get("name"),
                "path": item.get("file", {}).get("path"),
                "line_number": match.get("lineNumber"),
                "preview": match.get("preview"),
            })

            if len(results) >= max_results:
                return results

    return results
