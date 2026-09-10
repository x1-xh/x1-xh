#!/usr/bin/env python3
"""
update_showcase.py
Fetches repositories tagged with a specific topic (default: 'showcase')
and updates the Showcase section in README.md.
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

USERNAME = os.getenv("GITHUB_ACTOR") or os.getenv("GITHUB_REPOSITORY_OWNER") or "x1-xh"
TARGET_TOPIC = os.getenv("SHOWCASE_TOPIC", "showcase").lower()
TARGET_FILE = sys.argv[1] if len(sys.argv) > 1 else "README.md"
GITHUB_TOKEN = os.getenv("PERSONAL_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")


def github_request(url: str):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "x1-xh-profile-showcase",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Warning: Failed to fetch {url}: {e}", file=sys.stderr)
        return None


def fetch_showcase_repos():
    repos_by_id = {}

    # 1. Fetch user's public repos
    user_repos_url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=pushed"
    data = github_request(user_repos_url)
    if isinstance(data, list):
        for repo in data:
            repos_by_id[repo["id"]] = repo

    # 2. If authenticated, fetch all accessible user repos (includes orgs / collaborator repos)
    if GITHUB_TOKEN:
        auth_url = "https://api.github.com/user/repos?per_page=100&affiliation=owner,collaborator,organization_member&sort=pushed"
        data = github_request(auth_url)
        if isinstance(data, list):
            for repo in data:
                repos_by_id[repo["id"]] = repo

    # 3. Search API query for repos with the specific topic
    query = f"user:{USERNAME} topic:{TARGET_TOPIC}"
    search_url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=updated"
    search_data = github_request(search_url)
    if isinstance(search_data, dict) and "items" in search_data:
        for repo in search_data["items"]:
            repos_by_id[repo["id"]] = repo

    # Filter repos that have the target topic
    matched_repos = []
    for repo in repos_by_id.values():
        topics = [t.lower() for t in repo.get("topics", [])]
        if TARGET_TOPIC in topics:
            matched_repos.append(repo)

    # Sort: highest stars first, then most recently updated
    matched_repos.sort(
        key=lambda r: (
            r.get("stargazers_count", 0),
            r.get("pushed_at", "") or r.get("updated_at", ""),
        ),
        reverse=True,
    )

    return matched_repos


def format_showcase_section(repos):
    if not repos:
        return ""

    lines = ["#### 🌟 Showcase\n"]
    for repo in repos:
        name = repo.get("name", "")
        url = repo.get("html_url", "")
        desc = (repo.get("description") or "").replace("\r\n", " ").replace("\n", " ").strip()
        stars = repo.get("stargazers_count", 0)

        star_badge = f" **({stars}⭐)**" if stars > 0 else ""
        desc_part = f" - _{desc}_" if desc else ""
        lines.append(f"- [`{name}`]({url}){desc_part}{star_badge}")

    return "\n".join(lines) + "\n"


def update_readme():
    if not os.path.exists(TARGET_FILE):
        print(f"Error: {TARGET_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    with open(TARGET_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"<!--\s*SHOWCASE_START\s*-->.*?<!--\s*SHOWCASE_END\s*-->"
    if not re.search(pattern, content, flags=re.DOTALL):
        print(f"Error: SHOWCASE_START and SHOWCASE_END comments not found in {TARGET_FILE}.", file=sys.stderr)
        sys.exit(1)

    repos = fetch_showcase_repos()
    print(f"Found {len(repos)} repository/repositories with topic '{TARGET_TOPIC}'.")

    section_body = format_showcase_section(repos)
    replacement = f"<!-- SHOWCASE_START -->\n{section_body}<!-- SHOWCASE_END -->"

    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open(TARGET_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Successfully updated {TARGET_FILE}.")


if __name__ == "__main__":
    update_readme()
