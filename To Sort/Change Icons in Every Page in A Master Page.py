import time
from notion_client import Client, APIResponseError

# --- CONFIGURATION ---
# ⬇️ PASTE YOUR KEYS AND THE MASTER PAGE ID HERE ⬇️

NOTION_API_KEY = "diddy" # Replace with your actual Notion API Key
MASTER_PAGE_ID = "23483b71d8f381fcb60fe57d15043399"                 # Replace with the ID of the page containing your databases

# NEW: Direct public URL for the Wolfram Language icon.
ICON_URL = "https://cdn.simpleicons.org/anaconda/white"

# API rate limit delay. 0.4 is a safe buffer.
RATE_LIMIT_DELAY = 0.4

# --- SCRIPT ---

# Initialize the Notion client
notion = Client(auth=NOTION_API_KEY)

def find_databases_on_page(page_id):
    """
    Scans a page's content to find all child database blocks.
    Returns a list of their database IDs.
    """
    database_ids = []
    print(f"Searching for databases on page: {page_id}...")
    try:
        # The API call to get all blocks on the page
        response = notion.blocks.children.list(block_id=page_id)
        blocks = response.get("results", [])
        
        for block in blocks:
            # We are looking for blocks of type 'child_database'
            if block["type"] == "child_database":
                db_id = block["id"]
                db_title = block.get("child_database", {}).get("title", "Untitled Database")
                print(f"  > Found Database: '{db_title}' ({db_id})")
                database_ids.append(db_id)
                
    except APIResponseError as e:
        print(f"Error fetching blocks from page {page_id}: {e}")
        return []
        
    return database_ids

def update_pages_in_database(database_id):
    """
    Fetches all pages from a single database and updates their icons.
    """
    print(f"\n--- Processing Database ID: {database_id} ---")
    all_pages = []
    has_more = True
    start_cursor = None

    # 1. Fetch all pages from this database
    while has_more:
        try:
            response = notion.databases.query(
                database_id=database_id,
                start_cursor=start_cursor,
                page_size=100
            )
            all_pages.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
            time.sleep(RATE_LIMIT_DELAY)
        except APIResponseError as e:
            print(f"  > Error fetching pages from this database: {e}")
            return 0, 1 # Return 0 success, 1 failure for this db

    if not all_pages:
        print("  > No pages found in this database. Skipping.")
        return 0, 0

    print(f"  > Found {len(all_pages)} pages to update.")
    
    # 2. Iterate and update each page
    updated_count = 0
    failed_count = 0
    for page in all_pages:
        page_id = page["id"]
        try:
            icon_payload = {"type": "external", "external": {"url": ICON_URL}}
            notion.pages.update(page_id=page_id, icon=icon_payload)
            updated_count += 1
        except APIResponseError as e:
            print(f"    > FAILED to update page {page_id}: {e}")
            failed_count += 1
        time.sleep(RATE_LIMIT_DELAY)
        
    print(f"  > Finished. Success: {updated_count}, Failed: {failed_count}")
    return updated_count, failed_count

def main():
    """Main function to find all databases and update them."""
    if "YOUR_NOTION_INTEGRATION_TOKEN" in NOTION_API_KEY or "YOUR_MASTER_PAGE_ID" in MASTER_PAGE_ID:
        print("Error: Please replace the placeholder values for NOTION_API_KEY and MASTER_PAGE_ID.")
        return

    # Step 1: Find all databases on the master page
    database_ids_to_process = find_databases_on_page(MASTER_PAGE_ID)
    
    if not database_ids_to_process:
        print("\nNo databases were found on the specified page. Exiting.")
        return

    # Step 2: Loop through each found database and update its pages
    total_success = 0
    total_fails = 0
    for db_id in database_ids_to_process:
        success, fails = update_pages_in_database(db_id)
        total_success += success
        total_fails += fails
        
    print("\n--- SCRIPT COMPLETE ---")
    print(f"Total pages updated successfully: {total_success}")
    print(f"Total pages that failed to update: {total_fails}")

if __name__ == "__main__":
    main()