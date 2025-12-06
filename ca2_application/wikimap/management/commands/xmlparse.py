import xml.etree.ElementTree as ET
import sys
import os
import re

import sqlite3

import sqlite3

# Pre-compile Regex Patterns
CITATION_PATTERN = re.compile(r'\{\{\s*(?:Cite|Citation)[^}]*\}\}', re.IGNORECASE | re.DOTALL)
URL_PATTERN = re.compile(r'\|\s*url\s*=\s*([^|}]*)', re.IGNORECASE)
DATE_PATTERN = re.compile(r'\|\s*(?:date|year)\s*=\s*([^|}]*)', re.IGNORECASE)
YEAR_PATTERN = re.compile(r'\d{4}')
DAY_PATTERN = re.compile(r'\b([1-9]|[12][0-9]|3[01])\b')

# Global Constants
MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

def parse_xml(filename):
    """
    Parses a Wikipedia XML dump iteratively and saves article titles and oldest ref dates to SQLite.
    Using iterparse ensures that we don't load the entire file into memory.
    """
    
    # Connect to SQLite database
    db_filename = "wikipedia_articles.db"
    conn = sqlite3.connect(db_filename)
    cursor = conn.cursor()
    
    # Create the Article table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Article (
            title TEXT,
            oldest_date TEXT
        )
    ''')
    conn.commit()

    # Get current article count for resuming
    cursor.execute("SELECT COUNT(*) FROM Article")
    articles_parsed = cursor.fetchone()[0]
    if articles_parsed > 0:
        print(f"Resuming parsing. Already processed {articles_parsed} articles.")
    
    current_article_index = 0
    new_articles_count = 0

    # Batch insert list
    batch_data = []
    BATCH_SIZE = 10000

    # We use a try-except block to handle cases where the file might be truncated
    try:
        context = ET.iterparse(filename, events=("end",))
        for event, elem in context:
            tag_name = elem.tag
            # Remove namespace for easier comparison if present
            if '}' in tag_name:
                tag_name = tag_name.split('}', 1)[1]

            if tag_name == 'page':
                current_article_index += 1
                
                # Skip already processed articles
                if current_article_index <= articles_parsed:
                    elem.clear()
                    continue

                title_text = None
                text_content = None

                # Iterate through children to find title and revision/text
                for child in elem:
                    child_tag = child.tag
                    if not isinstance(child_tag, str):
                        continue
                    if '}' in child_tag:
                        child_tag = child_tag.split('}', 1)[1]
                    
                    if child_tag == 'title':
                        title_text = child.text
                    elif child_tag == 'revision':
                        for rev_child in child:
                            rev_child_tag = rev_child.tag
                            if not isinstance(rev_child_tag, str):
                                continue
                            if '}' in rev_child_tag:
                                rev_child_tag = rev_child_tag.split('}', 1)[1]
                            if rev_child_tag == 'text':
                                text_content = rev_child.text
                                break
                
                if title_text is not None:
                    oldest_date = None
                    
                    if text_content:
                        # Find citations
                        matches = CITATION_PATTERN.finditer(text_content)
                        
                        for match in matches:
                            template_text = match.group(0)
                            # Extract Date
                            # We treat date= or year= equally
                            date_str = None
                            date_match = DATE_PATTERN.search(template_text)
                            if date_match:
                                date_str = date_match.group(1).strip()
                            
                            if date_str:
                                # Parse date
                                # Heuristic parsing for common formats in Wikipedia
                                parsed_date = None
                                try:
                                    # Try to find a year
                                    year_match = YEAR_PATTERN.search(date_str)
                                    if year_match:
                                        year = int(year_match.group(0))
                                        
                                        # Initial default: Jan 1st of that year
                                        month = 1
                                        day = 1
                                        
                                        # Try to find month
                                        lower_date = date_str.lower()
                                        for m_name, m_num in MONTHS.items():
                                            if m_name in lower_date:
                                                month = m_num
                                                break
                                        
                                        # Try to find day (1 or 2 digits)
                                        # We look for digits that are NOT the year
                                        # We replace the year with empty to avoid matching it
                                        date_str_no_year = date_str.replace(str(year), '', 1)
                                        day_match = DAY_PATTERN.search(date_str_no_year)
                                        if day_match:
                                            day = int(day_match.group(1))
                                            
                                        # Crude datetime comparison key: tuple (year, month, day)
                                        parsed_date = (year, month, day)
                                except Exception:
                                    pass
                                
                                if parsed_date:
                                    if oldest_date is None or parsed_date < oldest_date:
                                        oldest_date = parsed_date

                    # Format date for DB
                    date_val = None
                    if oldest_date:
                        date_val = f"{oldest_date[2]:02d}-{oldest_date[1]:02d}-{oldest_date[0]}"
                    
                    batch_data.append((title_text, date_val))
                    new_articles_count += 1
                    
                    # Print progress every 1000 new items
                    if new_articles_count % 1000 == 0:
                        print(f"Processed {articles_parsed + new_articles_count} total articles... (Latest: {title_text})")

                    # Execute batch insert
                    if len(batch_data) >= BATCH_SIZE:
                        cursor.executemany("INSERT INTO Article (title, oldest_date) VALUES (?, ?)", batch_data)
                        conn.commit()
                        batch_data = []

                # Clear the element from memory to handle large files
                elem.clear()
        
        # Insert remaining records
        if batch_data:
            cursor.executemany("INSERT INTO Article (title, oldest_date) VALUES (?, ?)", batch_data)
            conn.commit()
            
        print(f"Finished. Total articles processed: {articles_parsed + new_articles_count}")

    except ET.ParseError as e:
        # Commit whatever we have so far
        if batch_data:
            cursor.executemany("INSERT INTO Article (title, oldest_date) VALUES (?, ?)", batch_data)
            conn.commit()
        print(f"Parse error (expected for truncated file): {e}", file=sys.stderr)
        pass
    except Exception as e:
        # Commit whatever we have so far (optional, depends on consistency requirements)
        if batch_data:
            cursor.executemany("INSERT INTO Article (title, oldest_date) VALUES (?, ?)", batch_data)
            conn.commit()
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python xmlparse.py <filename>")
        sys.exit(1)
        
    filename = sys.argv[1]
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' not found.")
        sys.exit(1)
        
    parse_xml(filename)
