import requests
import datetime

# ---------------------------
# CONFIG
# ---------------------------
NOTION_TOKEN = "nicetrydiddy"
SOURCE_DB_ID = "nicetrydiddy"  # main database
ARCHIVE_DB_ID = "nicetrydiddy"  # archive database

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# ---------------------------
# HELPERS
# ---------------------------

def query_old_pages():
    # 30 days ago timestamp
    thirty_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)).isoformat()

    url = f"https://api.notion.com/v1/databases/{SOURCE_DB_ID}/query"
    payload = {
        "filter": {
            "timestamp": "created_time",
            "created_time": {
                "before": thirty_days_ago
            }
        }
    }
    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    return res.json()["results"]


def copy_page_to_archive(page):
    name_val = ""
    date_val = None
    related_val = None

    # Get Name
    if page["properties"].get("Name") and page["properties"]["Name"]["title"]:
        name_val = page["properties"]["Name"]["title"][0]["text"]["content"]

    # Get Date
    if page["properties"].get("Date") and page["properties"]["Date"]["date"]:
        date_val = page["properties"]["Date"]["date"]["start"]

    # Get Related To (relation)
    if page["properties"].get("Related To") and page["properties"]["Related To"]["relation"]:
        related_val = page["properties"]["Related To"]["relation"]

    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": ARCHIVE_DB_ID},
        "properties": {
            "Name": {
                "title": [
                    {"text": {"content": name_val}}
                ]
            },
            "Why did you kill it": {
                "select": {"name": "Auto Archived"}
            },
            "When did it die": {
                "date": {"start": date_val} if date_val else None
            },
            "Related To": {
                "relation": related_val
            } if related_val else None
        }
    }

    # Remove None keys
    payload["properties"] = {k: v for k, v in payload["properties"].items() if v is not None}

    res = requests.post(url, headers=headers, json=payload)
    res.raise_for_status()
    return res.json()


def delete_page(page_id):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {"archived": True}
    res = requests.patch(url, headers=headers, json=payload)
    res.raise_for_status()


# ---------------------------
# MAIN FLOW
# ---------------------------
if __name__ == "__main__":
    old_pages = query_old_pages()
    print(f"Found {len(old_pages)} pages older than 30 days.")

    for page in old_pages:
        copy_page_to_archive(page)
        delete_page(page["id"])
        print(f"Moved page {page['id']} to archive.")
