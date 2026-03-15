from notion_client import Client
import re

# Initialize Notion client with your API key
notion = Client(auth="diddy")

def extract_job_role_from_title(title):
    """
    Extract job role from page title using regex patterns
    Modify these patterns based on how your titles are structured
    """
    # Example patterns - customize these based on your title formats
    patterns = [
        r"(\w+\s\w+)\s-\s",  # "Job Role - Company Name"
        r"(\w+)\s@",         # "Job Role @ Company"
        r"^([\w\s&]+)$",     # Just the job role itself
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            return match.group(1).strip()
    
    # If no pattern matches, return the original title
    return title

def update_job_roles_in_database(database_id):
    """
    Query all pages in the database and update their Job Role property
    based on the JD property content
    """
    try:
        # Query the database
        response = notion.databases.query(database_id=database_id)
        
        for page in response["results"]:
            # Get the JD property
            jd_property = page["properties"].get("JD")
            
            if not jd_property:
                print(f"Skipping page {page['id']}: No JD property found")
                continue
                
            # Extract JD text based on property type
            jd_text = ""
            if jd_property["type"] == "title":
                jd_text = " ".join([t["plain_text"] for t in jd_property["title"]])
            elif jd_property["type"] == "rich_text":
                jd_text = " ".join([t["plain_text"] for t in jd_property["rich_text"]])
            elif jd_property["type"] == "select" and jd_property["select"]:
                jd_text = jd_property["select"]["name"]
            elif jd_property["type"] == "formula" and jd_property["formula"]["type"] == "string":
                jd_text = jd_property["formula"]["string"]
            # Add more property types if needed
            
            if not jd_text:
                print(f"Skipping page {page['id']}: Empty JD property")
                continue
                
            # Extract job role from JD text
            job_role = extract_job_role_from_title(jd_text)
            
            # Update the Job Role property (select type)
            notion.pages.update(
                page_id=page["id"],
                properties={
                    "Job Role": {
                        "select": {
                            "name": job_role
                        }
                    }
                }
            )
            
            print(f"Updated '{jd_text}' → Job Role: {job_role}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Your database ID
    DATABASE_ID = "1bb83b71d8f3809d9622f1b88fa0a345"
    
    update_job_roles_in_database(DATABASE_ID)