"""Fetch the canonical transcript from Notion's API, fail closed on unknown blocks.

No raw transcript is printed or uploaded. Requires NOTION_TOKEN in the runner.
"""
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SOURCE_ID = "4168c067-daa4-8111-bda6-ef07325583ed"


def request_json(path, token):
    req = Request("https://api.notion.com/v1/" + path, headers={
        "Authorization": "Bearer " + token,
        "Notion-Version": "2022-06-28",
        "Accept": "application/json",
    })
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def rich_text(block):
    kind = block["type"]
    return "".join(item.get("plain_text", "") for item in block[kind].get("rich_text", []))


def fetch_canonical(token, *, api=request_json):
    if not token:
        raise ValueError("Notion API credential unavailable")
    page = api("pages/" + SOURCE_ID, token)
    if page.get("id", "").replace("-", "") != SOURCE_ID.replace("-", ""):
        raise ValueError("wrong Notion page")
    revision = page.get("last_edited_time")
    if not revision:
        raise ValueError("Notion revision unavailable")
    blocks = []
    cursor = None
    while True:
        query = urlencode({"page_size": 100, **({"start_cursor": cursor} if cursor else {})})
        data = api("blocks/" + SOURCE_ID + "/children?" + query, token)
        if not isinstance(data.get("results"), list):
            raise ValueError("Notion blocks response incomplete")
        blocks.extend(data["results"])
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            raise ValueError("Notion pagination cursor missing")
    lines = []
    for block in blocks:
        kind = block.get("type")
        if block.get("has_children"):
            raise ValueError("nested Notion content requires explicit handling")
        if kind == "heading_2":
            lines.append("## " + rich_text(block))
        elif kind == "code":
            language = block["code"].get("language")
            if language not in ("plain text", "text", "json"):
                raise ValueError("unsupported code block language")
            fence = "json" if language == "json" else "txt"
            lines.append("```" + fence + "\n" + rich_text(block) + "\n```")
        elif kind in ("paragraph", "heading_1", "heading_3"):
            lines.append(rich_text(block))
        elif kind == "divider":
            lines.append("---")
        else:
            raise ValueError("unsupported Notion block type: " + str(kind))
    return "\n\n".join(lines), {
        "source_id": SOURCE_ID, "source_revision": revision,
        "truncated": False, "unknown_block_count": 0,
    }


def main():
    token = os.environ.get("NOTION_TOKEN", "")
    markdown, metadata = fetch_canonical(token)
    output = Path(os.environ.get("SOURCE_DIR", "source-private"))
    output.mkdir(parents=True, exist_ok=True)
    (output / "notion.md").write_text(markdown, encoding="utf-8")
    (output / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    print("Notion page fetched; raw source retained only in temporary runner workspace")


if __name__ == "__main__":
    main()
