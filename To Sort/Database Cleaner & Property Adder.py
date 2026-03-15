import requests
import re
from urllib.parse import unquote
import time

# Configuration
NOTION_API_KEY = "diddy"  # Replace with your actual API key
DATABASE_ID = "1bb83b71d8f3809d9622f1b88fa0a345"  # Replace with your actual database ID
headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}
# The exact name of the property you want to update in Notion
JD_PROPERTY_NAME = "Job Description" 

def extract_jd_from_url(url):
    # Handle different URL formats
    patterns = [
        r'https://www\.notion\.so/[^/]+/(.*?)-([a-f0-9]{32})',
        r'https://www\.notion\.so/(.*?)-([a-f0-9]{32})',
        r'notion\.so/[^/]+/(.*?)-([a-f0-9]{32})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            # Return the part of the title from the URL slug
            return match.group(1)
    return None

def clean_jd_name(jd):
    if not jd:
        return ""
    
    # URL decode first
    jd = unquote(jd)
    
    # Replace hyphens with spaces
    jd = jd.replace("-", " ")
    
    # Remove duplicate words (case-insensitive)
    words = jd.split()
    seen = set()
    unique_words = []
    
    for word in words:
        lower_word = word.lower()
        if lower_word not in seen:
            seen.add(lower_word)
            unique_words.append(word)
    
    # Capitalize each word
    jd = " ".join(unique_words)
    return jd.title()

def fetch_pages():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    all_pages = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {"start_cursor": next_cursor} if next_cursor else {}
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            print(f"Error fetching pages: {response.status_code} - {response.text}")
            return []
        
        data = response.json()
        all_pages.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor")

    return all_pages

def update_page_with_jd(page_id, jd_cleaned):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    payload = {
        "properties": {
            JD_PROPERTY_NAME: {
                "rich_text": [
                    {
                        "text": {
                            "content": jd_cleaned
                        }
                    }
                ]
            }
        }
    }
    
    response = requests.patch(url, headers=headers, json=payload)
    return response.status_code, response.json()

# Debug function to check database properties
def check_database_properties():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        print("Database properties found:", list(response.json().get("properties", {}).keys()))
    else:
        print(f"Error checking database: {response.status_code} - {response.text}")

# Main execution
if __name__ == "__main__":
    # First check if we can access the database
    check_database_properties()
    
    pages = fetch_pages()
    if not pages:
        print("No pages fetched. Check your API key and database ID.")
    else:
        print(f"\nFetched {len(pages)} pages. Starting update process...")
        for page in pages:
            # 1. Get the URL from the current page object
            page_url = page.get("url")
            
            if not page_url:
                print(f"Skipping page {page['id']} - no URL found.")
                print("---")
                continue

            # 2. Extract the raw "JD" part from this page's URL
            raw_jd = extract_jd_from_url(page_url)
            
            # 3. Clean the extracted text
            jd_cleaned = clean_jd_name(raw_jd)
            
            # 4. Check if we actually got a JD to update
            if not jd_cleaned:
                print(f"Skipping page {page['id']} - could not extract a clean JD from URL: {page_url}")
                print("---")
                continue

            print(f"Updating page: {page['id']}")
            print(f"  - Cleaned JD to add: {jd_cleaned}")
            
            # 5. Update the page with the cleaned JD specific to this page
            status, response = update_page_with_jd(page["id"], jd_cleaned)
            
            print(f"Status: {status}")
            if status != 200:
                print(f"Error response: {response}")
            
            print("---")
            # Add a small delay to respect Notion's API rate limits (avg 3 requests per second)
            time.sleep(0.5)