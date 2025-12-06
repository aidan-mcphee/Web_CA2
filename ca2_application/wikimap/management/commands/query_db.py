import sqlite3
import os
from datetime import datetime

def get_articles_before_date(db_path, article_names, timestamp_str):
    """
    Returns a list of article details (title, date) from the database that match 
    the given names and have a date STRICTLY BEFORE the timestamp.
    Articles with no date are excluded.
    
    timestamp_str format: 'DD-MM-YYYY'
    """
    if not os.path.exists(db_path):
        print(f"Database file '{db_path}' not found.")
        return []

    cutoff_date = None
    try:
        cutoff_date = datetime.strptime(timestamp_str, "%d-%m-%Y")
    except ValueError:
        print(f"Invalid timestamp format: {timestamp_str}. Use DD-MM-YYYY.")
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # SQLite doesn't support array parameters directly in a clean way unless using specific extensions
    # so we construct the query with placeholders.
    placeholders = ','.join('?' for _ in article_names)
    query = f"SELECT title, oldest_date FROM Article WHERE title IN ({placeholders})"
    
    results = []
    try:
        cursor.execute(query, article_names)
        rows = cursor.fetchall()
        
        for title, date_str in rows:
            if not date_str:
                continue
            
            try:
                article_date = datetime.strptime(date_str, "%d-%m-%Y")
                if article_date < cutoff_date:
                    results.append((title, date_str))
            except ValueError:
                continue # Skip invalid dates in DB if any
                
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()
        
    return results

if __name__ == "__main__":
    db_file = 'wikipedia_articles.db'
    
    # Test Data: Based on known sample file content
    test_articles = ["Anarchism", "Albedo", "AccessibleComputing", "NonExistent"]
    cutoff = "01-01-1970"
    
    print(f"Querying articles: {test_articles}")
    print(f"Cutoff Date: {cutoff}")
    print("-" * 40)
    
    matches = get_articles_before_date(db_file, test_articles, cutoff)
    
    for title, date in matches:
        print(f"MATCH: {title} (Date: {date})")
    
    print("-" * 40)

