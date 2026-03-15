import os
import requests
import re
import yaml
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import markdown
from markdown.extensions import codehilite, tables, toc, fenced_code
from bs4 import BeautifulSoup
import html2text

# --- CONFIGURATION ---
@dataclass
class Config:
    """Configuration class for the Notion uploader."""
    NOTION_TOKEN: str = "nicetrydiddy"  # Replace with actual token
    DATABASE_ID: str = "26783b71d8f380769defe96bbb26b681"
    ROOT_FOLDER: str = r"C:\Users\ASUS\Videos\AnyDesk\Balasubramanian PG\Interview Question\StrataScratch"
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 0.3
    RATE_LIMIT_DELAY: float = 0.1
    CHUNK_SIZE: int = 100  # Process files in chunks

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('notion_bulk_import.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NotionMarkdownImporter:
    """Class to handle bulk import of markdown files to Notion - mimics native import."""
    
    def __init__(self, config: Config):
        self.config = config
        self.headers = {
            "Authorization": f"Bearer {config.NOTION_TOKEN}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Initialize markdown parser with extensions (like native import)
        self.md_parser = markdown.Markdown(extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            'toc',
            'md_in_html',
            'nl2br'
        ])
    
    def validate_config(self) -> bool:
        """Validate configuration settings."""
        if not self.config.NOTION_TOKEN or self.config.NOTION_TOKEN == "your_notion_token_here":
            logger.error("Please set a valid NOTION_TOKEN")
            return False
            
        if not os.path.exists(self.config.ROOT_FOLDER):
            logger.error(f"Root folder does not exist: {self.config.ROOT_FOLDER}")
            return False
            
        if not self.config.DATABASE_ID:
            logger.error("DATABASE_ID is required")
            return False
            
        return True
    
    def test_notion_connection(self) -> bool:
        """Test connection to Notion API."""
        try:
            url = f"https://api.notion.com/v1/databases/{self.config.DATABASE_ID}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                logger.info("Successfully connected to Notion API")
                return True
            elif response.status_code == 401:
                logger.error("Authentication failed. Check your NOTION_TOKEN")
                return False
            elif response.status_code == 404:
                logger.error("Database not found. Check your DATABASE_ID")
                return False
            else:
                logger.error(f"Connection test failed: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to connect to Notion API: {e}")
            return False
    
    def extract_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """Extract YAML frontmatter from markdown content."""
        try:
            if content.startswith('---\n'):
                try:
                    _, frontmatter, body = content.split('---\n', 2)
                    metadata = yaml.safe_load(frontmatter) or {}
                    return metadata, body.strip()
                except ValueError:
                    # No frontmatter found
                    pass
            return {}, content
        except Exception as e:
            logger.warning(f"Error extracting frontmatter: {e}")
            return {}, content
    
    def create_page_from_markdown(self, title: str, markdown_content: str, 
                                topic_area: str, subtopic: str, metadata: Dict = None) -> bool:
        """Create a Notion page by uploading the markdown content directly."""
        try:
            # First, create the page with basic properties
            page_data = {
                "parent": {"database_id": self.config.DATABASE_ID},
                "properties": {
                    "Name": {"title": [{"text": {"content": title}}]},
                    "Topic Area": {"select": {"name": topic_area}},
                    "Subtopic": {"select": {"name": subtopic}}
                }
            }
            
            # Add metadata if available
            if metadata:
                if "Difficulty" in metadata:
                    page_data["properties"]["Difficulty"] = {"select": {"name": str(metadata["Difficulty"])}}
                if "Company" in metadata:
                    companies = metadata["Company"]
                    if isinstance(companies, str):
                        companies = [companies]
                    elif isinstance(companies, list):
                        companies = [str(c) for c in companies if c]
                    if companies:
                        page_data["properties"]["Company"] = {"multi_select": [{"name": c} for c in companies[:10]]}
                if "Category" in metadata:
                    page_data["properties"]["Category"] = {"select": {"name": str(metadata["Category"])}}
            
            # Create the page first
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=self.headers,
                json=page_data,
                timeout=60
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to create page '{title}': {response.text}")
                return False
            
            page_info = response.json()
            page_id = page_info["id"]
            
            # Now add the markdown content to the page
            success = self.add_markdown_to_page(page_id, markdown_content, title)
            
            if success:
                logger.info(f"Successfully created and populated page: {title}")
                time.sleep(self.config.RATE_LIMIT_DELAY)
                return True
            else:
                logger.error(f"Failed to add content to page: {title}")
                return False
                
        except Exception as e:
            logger.error(f"Error creating page from markdown '{title}': {e}")
            return False
    
    def add_markdown_to_page(self, page_id: str, markdown_content: str, title: str) -> bool:
        """Add markdown content to an existing Notion page using a simpler approach."""
        try:
            # Split content into manageable sections
            sections = self.split_markdown_content(markdown_content)
            
            for i, section in enumerate(sections):
                blocks = self.convert_section_to_blocks(section)
                if not blocks:
                    continue
                    
                # Add blocks to page
                success = self.append_blocks_to_page(page_id, blocks, f"{title} - Section {i+1}")
                if not success:
                    logger.warning(f"Failed to add section {i+1} to page {title}")
                    
                # Small delay between sections
                time.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding markdown to page {title}: {e}")
            return False
    
    def split_markdown_content(self, content: str) -> List[str]:
        """Split markdown content into smaller sections to avoid API limits."""
        # Split by headers first
        header_pattern = r'\n#{1,6}\s+'
        sections = re.split(header_pattern, content)
        
        result_sections = []
        current_section = ""
        
        for section in sections:
            # If section is small enough, add to current
            if len(current_section + section) < 10000:  # Conservative limit
                current_section += section
            else:
                # Save current section and start new one
                if current_section.strip():
                    result_sections.append(current_section.strip())
                current_section = section
        
        # Add the last section
        if current_section.strip():
            result_sections.append(current_section.strip())
        
        return result_sections if result_sections else [content]
    
    def convert_section_to_blocks(self, section: str) -> List[Dict]:
        """Convert a markdown section to Notion blocks using simpler parsing."""
        blocks = []
        lines = section.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].rstrip()
            
            if not line.strip():
                i += 1
                continue
            
            try:
                # Headers
                if line.startswith('#'):
                    level = min(len(line) - len(line.lstrip('#')), 3)
                    text = line.lstrip('#').strip()
                    if text and len(text) <= 2000:
                        blocks.append({
                            "object": "block",
                            "type": f"heading_{level}",
                            f"heading_{level}": {
                                "rich_text": [{"type": "text", "text": {"content": text}}]
                            }
                        })
                
                # Code blocks
                elif line.startswith('```'):
                    language = line[3:].strip() or 'text'
                    code_lines = []
                    i += 1
                    
                    while i < len(lines) and not lines[i].startswith('```'):
                        code_lines.append(lines[i])
                        i += 1
                    
                    code_content = '\n'.join(code_lines)
                    if len(code_content) <= 2000:
                        blocks.append({
                            "object": "block",
                            "type": "code",
                            "code": {
                                "language": language,
                                "rich_text": [{"type": "text", "text": {"content": code_content}}]
                            }
                        })
                
                # Lists
                elif line.lstrip().startswith(('- ', '* ', '+ ')):
                    text = line.lstrip()[2:].strip()
                    if text and len(text) <= 2000:
                        blocks.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {
                                "rich_text": [{"type": "text", "text": {"content": text}}]
                            }
                        })
                
                elif re.match(r'^\s*\d+\.\s', line):
                    text = re.sub(r'^\s*\d+\.\s', '', line).strip()
                    if text and len(text) <= 2000:
                        blocks.append({
                            "object": "block",
                            "type": "numbered_list_item",
                            "numbered_list_item": {
                                "rich_text": [{"type": "text", "text": {"content": text}}]
                            }
                        })
                
                # Tables (convert to code blocks)
                elif '|' in line and line.count('|') >= 2:
                    table_lines = [line]
                    i += 1
                    while i < len(lines) and '|' in lines[i]:
                        table_lines.append(lines[i])
                        i += 1
                    i -= 1  # Back up one line
                    
                    table_content = '\n'.join(table_lines)
                    if len(table_content) <= 2000:
                        blocks.append({
                            "object": "block",
                            "type": "code",
                            "code": {
                                "language": "markdown",
                                "rich_text": [{"type": "text", "text": {"content": table_content}}]
                            }
                        })
                
                # Regular paragraphs
                else:
                    # Collect paragraph lines
                    paragraph_lines = [line]
                    i += 1
                    while (i < len(lines) and 
                           lines[i].strip() and 
                           not lines[i].startswith(('#', '```', '- ', '* ', '+ ')) and
                           not re.match(r'^\s*\d+\.\s', lines[i]) and
                           '|' not in lines[i]):
                        paragraph_lines.append(lines[i].rstrip())
                        i += 1
                    i -= 1  # Back up one line
                    
                    paragraph_text = '\n'.join(paragraph_lines).strip()
                    if paragraph_text and len(paragraph_text) <= 2000:
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": paragraph_text}}]
                            }
                        })
                    elif len(paragraph_text) > 2000:
                        # Split long paragraphs
                        chunks = [paragraph_text[i:i+2000] for i in range(0, len(paragraph_text), 2000)]
                        for chunk in chunks:
                            blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                                }
                            })
                
            except Exception as e:
                logger.warning(f"Error processing line '{line[:50]}...': {e}")
            
            i += 1
        
        return blocks
    
    def append_blocks_to_page(self, page_id: str, blocks: List[Dict], context: str = "") -> bool:
        """Append blocks to a Notion page."""
        try:
            if not blocks:
                return True
                
            # Notion allows max 100 blocks per request
            chunk_size = 100
            for i in range(0, len(blocks), chunk_size):
                chunk = blocks[i:i + chunk_size]
                
                url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                data = {"children": chunk}
                
                response = requests.patch(url, headers=self.headers, json=data, timeout=60)
                
                if response.status_code == 200:
                    logger.debug(f"Added {len(chunk)} blocks to {context}")
                elif response.status_code == 429:
                    logger.warning(f"Rate limited, waiting and retrying for {context}")
                    time.sleep(5)
                    response = requests.patch(url, headers=self.headers, json=data, timeout=60)
                    if response.status_code != 200:
                        logger.error(f"Failed after retry for {context}: {response.text}")
                        return False
                else:
                    logger.error(f"Failed to add blocks to {context}: {response.status_code} - {response.text}")
                    return False
                
                # Small delay between chunks
                if i + chunk_size < len(blocks):
                    time.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Error appending blocks to page {context}: {e}")
            return False
    
    def process_markdown_file(self, file_path: Path, topic_area: str, subtopic: str) -> bool:
        """Process a single markdown file and import it to Notion."""
        try:
            logger.info(f"Processing: {file_path}")
            
            # Read file with multiple encoding attempts
            content = None
            for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if content is None:
                logger.error(f"Could not decode file: {file_path}")
                return False
            
            if not content.strip():
                logger.warning(f"File is empty: {file_path}")
                return False
            
            # Extract frontmatter
            metadata, markdown_content = self.extract_frontmatter(content)
            
            # Use filename as title
            title = file_path.stem
            
            # Create the page
            success = self.create_page_from_markdown(title, markdown_content, topic_area, subtopic, metadata)
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return False
    
    def bulk_import(self) -> Tuple[int, int]:
        """Perform bulk import of all markdown files."""
        if not self.validate_config():
            return 0, 0
        
        if not self.test_notion_connection():
            return 0, 0
        
        root_path = Path(self.config.ROOT_FOLDER)
        successful = 0
        failed = 0
        
        logger.info(f"Starting bulk import from: {root_path}")
        
        # Walk through directory structure
        for topic_area_path in root_path.iterdir():
            if not topic_area_path.is_dir():
                continue
                
            topic_area = topic_area_path.name
            logger.info(f"Processing topic area: {topic_area}")
            
            for subtopic_path in topic_area_path.iterdir():
                if not subtopic_path.is_dir():
                    continue
                    
                subtopic = subtopic_path.name
                logger.info(f"Processing subtopic: {subtopic}")
                
                # Find all markdown files
                md_files = list(subtopic_path.glob("*.md"))
                if not md_files:
                    logger.info(f"No markdown files found in: {subtopic_path}")
                    continue
                
                logger.info(f"Found {len(md_files)} markdown files")
                
                # Process files in chunks to manage memory and API limits
                for i in range(0, len(md_files), self.config.CHUNK_SIZE):
                    chunk = md_files[i:i + self.config.CHUNK_SIZE]
                    logger.info(f"Processing chunk {i//self.config.CHUNK_SIZE + 1}/{(len(md_files)-1)//self.config.CHUNK_SIZE + 1}")
                    
                    for md_file in chunk:
                        try:
                            if self.process_markdown_file(md_file, topic_area, subtopic):
                                successful += 1
                                logger.info(f"✓ Successfully imported: {md_file.name}")
                            else:
                                failed += 1
                                logger.error(f"✗ Failed to import: {md_file.name}")
                        except KeyboardInterrupt:
                            logger.info("Import interrupted by user")
                            return successful, failed
                        except Exception as e:
                            logger.error(f"Unexpected error processing {md_file}: {e}")
                            failed += 1
        
        logger.info(f"Bulk import completed. Successful: {successful}, Failed: {failed}")
        return successful, failed

def main():
    """Main function to run the bulk importer."""
    print("=== Notion Bulk Markdown Importer ===")
    print("This tool mimics Notion's native import functionality")
    print("Processing large files without character limitations\n")
    
    config = Config()
    
    # Show configuration
    print("Configuration:")
    print(f"  Root folder: {config.ROOT_FOLDER}")
    print(f"  Database ID: {config.DATABASE_ID}")
    print(f"  Token: {'*' * 10}{config.NOTION_TOKEN[-4:] if len(config.NOTION_TOKEN) > 10 else 'Not set'}")
    print()
    
    importer = NotionMarkdownImporter(config)
    
    try:
        successful, failed = importer.bulk_import()
        
        print(f"\n{'='*50}")
        print(f"IMPORT SUMMARY")
        print(f"{'='*50}")
        print(f"✓ Successful imports: {successful}")
        print(f"✗ Failed imports: {failed}")
        print(f"📊 Total processed: {successful + failed}")
        print(f"📈 Success rate: {(successful/(successful + failed)*100 if successful + failed > 0 else 0):.1f}%")
        
        if failed > 0:
            print(f"\n📋 Check 'notion_bulk_import.log' for detailed error information")
            
        print(f"\n🎉 Import completed!")
            
    except KeyboardInterrupt:
        print("\n⏸️  Import interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"💥 Fatal error occurred. Check logs for details: {e}")

if __name__ == "__main__":
    main()