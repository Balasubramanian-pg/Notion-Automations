import requests
import json
import time

# --- Configuration ---

# FIX 1: Directly assign your API key here.
# Make sure your key starts with "secret_".
NOTION_API_KEY = "Nice try diddy" # <--- PASTE YOUR KEY HERE

# FIX 2: Make sure this is the ID of the DATABASE, not the page it's on.
# You can get it from the URL: notion.so/workspace/DATABASE_ID?v=...
DATABASE_ID = "Nice try diddy"        # Replace with your actual database ID

NOTION_API_URL = "https://api.notion.com/v1"

# --- Property Names (Update to match your database exactly) ---
# DOUBLE-CHECK these. They are case-sensitive and must be perfect.
STATUS_PROPERTY_NAME = "Application Status"        # The name of your 'Status' column
NEXT_ACTION_PROPERTY_NAME = "Next Action"   # The name of your 'Multi-select' column

# --- Automation Logic ---
# The keys ("Applied", etc.) must EXACTLY match the options in your "Application Status" column.
# The values (["Follow up...", etc.]) must EXACTLY match the options in your "Next Action" column.
STATUS_TO_ACTIONS = {
    "Application Done": ["Follow up with HR", "Check application portal"],
    "Interview Scheduled": ["Interview prep", "Research company", "Prepare questions"],
    "Offer": ["Review offer", "Negotiate terms"],
    "Rejected": ["Send thank you note", "Request feedback", "Update job tracker"],
    # Add more status-to-action mappings as needed
}

# --- API Setup ---
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def fetch_database_entries():
    """Fetch all entries from the Notion database."""
    url = f"{NOTION_API_URL}/databases/{DATABASE_ID}/query"
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching database entries: {e}")
        if e.response:
            # This is the most important line for debugging.
            print(f"   Notion API Response: {e.response.text}")
        return []

def update_page(page_id, payload):
    """Update a Notion page with the given payload."""
    url = f"{NOTION_API_URL}/pages/{page_id}"
    response = requests.patch(url, headers=headers, data=json.dumps(payload))
    response.raise_for_status()
    return response.json()

def main():
    print("Starting Notion automation script...")

    if "YOUR_REAL_API_KEY_HERE" in NOTION_API_KEY or len(DATABASE_ID) < 32:
        print("❌ CONFIGURATION ERROR: Please replace 'secret_YOUR_REAL_API_KEY_HERE' with your Notion API key and double-check your DATABASE_ID.")
        return

    pages = fetch_database_entries()

    if not pages:
        print("No pages found. This could be due to an error, or the database is empty.")
        return

    print(f"Found {len(pages)} pages to process.")
    for page in pages:
        page_id = page["id"]
        properties = page["properties"]

        status_property = properties.get(STATUS_PROPERTY_NAME)

        if not status_property:
            print(f"⚠️  Skipping page {page_id}: Property '{STATUS_PROPERTY_NAME}' not found. Check your spelling and case.")
            continue

        prop_type = status_property.get("type")
        current_status_obj = status_property.get(prop_type)

        if not current_status_obj or "name" not in current_status_obj:
            print(f"⏩ Skipping page {page_id}: The status is not set.")
            continue
            
        current_status = current_status_obj["name"]
        print(f"\nProcessing Page ID: {page_id}, Current Status: '{current_status}'")

        next_actions = STATUS_TO_ACTIONS.get(current_status)

        if not next_actions:
            print(f"⏩ No actions defined for status '{current_status}'. Skipping.")
            continue

        payload = {
            "properties": {
                NEXT_ACTION_PROPERTY_NAME: {
                    "multi_select": [{"name": action} for action in next_actions]
                }
            }
        }

        try:
            time.sleep(0.35)
            update_page(page_id, payload)
            print(f"✅ Successfully updated page {page_id}: Set actions to {next_actions}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to update page {page_id}: {e}")
            if e.response:
                # The error message from Notion is the key to solving other problems.
                print(f"   Notion API Error: {e.response.text}")

    print("\nScript finished.")

if __name__ == "__main__":
    main()
