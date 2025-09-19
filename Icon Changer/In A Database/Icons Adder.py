import time
from notion_client import Client, APIResponseError

# --- CONFIGURATION ---
# ⬇️ PASTE YOUR KEYS HERE ⬇️

NOTION_API_KEY = "nicetrydiddy"  # Replace with your actual Notion API Key
DATABASE_ID = "nicetrydiddy"                      # Replace with your actual Database ID

# --- Do not edit below this line unless you know what you are doing ---

# The icon URL you provided
ICON_URL = "https://cdn.simpleicons.org/netflix/white"# API rate limit delay (Notion allows ~3 requests/second). 0.4 is a safe buffer.
RATE_LIMIT_DELAY = 0.4

# --- SCRIPT ---

def get_all_pages_from_database(notion_client, db_id):
    """
    Fetches all pages from a Notion database, handling pagination.
    """
    all_pages = []
    has_more = True
    start_cursor = None
    
    print(f"Fetching all pages from database ID: {db_id}...")
    
    while has_more:
        try:
            response = notion_client.databases.query(
                database_id=db_id,
                start_cursor=start_cursor,
                page_size=100  # Max page size
            )
            all_pages.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
            print(f"  > Fetched {len(all_pages)} pages so far...")
            time.sleep(RATE_LIMIT_DELAY) # Be kind to the API
        except APIResponseError as e:
            print(f"Error fetching pages: {e}")
            return None
            
    print(f"\nTotal pages found: {len(all_pages)}\n")
    return all_pages

def get_page_title(page):
    """Safely extracts the title from a page object."""
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            title_list = prop.get("title", [])
            if title_list:
                return title_list[0].get("plain_text", "Untitled")
    return "Untitled"

def main():
    """Main function to run the script."""
    # Check if placeholders have been replaced
    if "YOUR_NOTION_INTEGRATION_TOKEN" in NOTION_API_KEY or "YOUR_DATABASE_ID" in DATABASE_ID:
        print("Error: Please replace the placeholder values for NOTION_API_KEY and DATABASE_ID in the script.")
        return

    # Initialize the Notion client
    notion = Client(auth=NOTION_API_KEY)
    
    # 1. Fetch all pages
    pages_to_update = get_all_pages_from_database(notion, DATABASE_ID)
    
    if pages_to_update is None:
        print("Could not retrieve pages. Check your API Key and Database ID. Exiting.")
        return
        
    if not pages_to_update:
        print("No pages found in the database. Nothing to do.")
        return

    # 2. Iterate and update each page
    print("--- Starting Icon Update Process ---")
    updated_count = 0
    failed_count = 0
    
    for i, page in enumerate(pages_to_update):
        page_id = page["id"]
        page_title = get_page_title(page)
        
        print(f"Updating page {i+1}/{len(pages_to_update)}: '{page_title}' ({page_id})")
        
        try:
            # The payload for updating an external icon
            icon_payload = {
                "type": "external",
                "external": {"url": ICON_URL}
            }
            
            notion.pages.update(
                page_id=page_id,
                icon=icon_payload
            )
            updated_count += 1
            print("  > Success!")
            
        except APIResponseError as e:
            failed_count += 1
            print(f"  > FAILED to update page {page_id}: {e}")
            
        # Add a delay to respect Notion's API rate limits
        time.sleep(RATE_LIMIT_DELAY)

    print("\n--- Update Complete ---")
    print(f"Successfully updated: {updated_count} pages")
    print(f"Failed to update:   {failed_count} pages")

if __name__ == "__main__":
    main()
