from typing import Any

import httpx2

USER_AGENT = "OSRSAccountOptimizer/1.0 (https://github.com/NJKimb/OSRS_Optimizer) Discord: JJoner"
WIKI_API_ENDPOINT = "https://oldschool.runescape.wiki/api.php"


def fetch_wiki_page_content(page_title: str, prop: str) -> Any:
    """
    Fetches wikitext or parsed HTML from the OSRS Wiki API.
    """
    params = {"action": "parse", "page": page_title, "prop": prop, "format": "json"}
    response = httpx2.get(
        WIKI_API_ENDPOINT,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if response.status_code == 200:
        data = response.json()
        if "error" in data:
            raise RuntimeError(
                f"OSRS Wiki API error for '{page_title}': {data['error'].get('info')}"
            )
        return data["parse"][prop]["*"]
    else:
        raise RuntimeError(
            f"OSRS Wiki API request failed with status {response.status_code}"
        )


def fetch_quest_bucket():
    query_string = "bucket('quest').select('page_name', 'official_difficulty', 'official_length', 'requirements').run()"
    params = {"action": "bucket", "format": "json", "query": query_string}
    response = httpx2.get(
        WIKI_API_ENDPOINT,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise RuntimeError(
            f"OSRS Wiki Bucket API request failed with status {response.status_code}"
        )
