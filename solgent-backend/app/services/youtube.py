import re
import urllib.parse
from typing import Any

import requests


def youtube_search(q: str, max_results: int = 2) -> list[dict[str, Any]]:
    """Pulls visual reference media metadata from public search indexes without Google Dev console keys."""
    encoded_query = urllib.parse.quote(q)
    url = f"https://www.youtube.com/results?search_query={encoded_query}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return []

        video_ids = re.findall(r"\"videoId\":\"([^\"]+)\"", response.text)
        titles = re.findall(r"\"title\":{\"runs\":\[{\"text\":\"([^\"]+)\"}\]", response.text)

        results = []
        seen = set()
        for idx, v_id in enumerate(video_ids):
            if v_id in seen or len(results) >= max_results:
                continue
            seen.add(v_id)

            title = titles[idx] if idx < len(titles) else "Visual Workspace Tutorial"
            results.append(
                {
                    "title": title.encode().decode("unicode-escape", errors="ignore"),
                    "videoId": v_id,
                    "url": f"https://youtube.com/watch?v={v_id}",
                }
            )

        return results
    except Exception:
        return []
