from notion_client import Client
import pandas as pd

notion = Client(auth="nice try diddy")

all_databases = []
next_cursor = None

while True:
    res = notion.search(start_cursor=next_cursor, page_size=100)
    for r in res["results"]:
        if r["object"] == "database":
            title = r["title"][0]["plain_text"] if r.get("title") else "Untitled"
            all_databases.append({"Name": title, "Database ID": r["id"]})
    next_cursor = res.get("next_cursor")
    if not res.get("has_more"):
        break

pd.DataFrame(all_databases)