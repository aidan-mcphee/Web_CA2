import xml.etree.ElementTree as ET
import re
import sys
import os
from datetime import date
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from wikimap.models import Article

# Pre-compile Regex Patterns
CITATION_PATTERN = re.compile(r'\{\{\s*(?:Cite|Citation)[^}]*\}\}', re.IGNORECASE | re.DOTALL)
URL_PATTERN = re.compile(r'\|\s*url\s*=\s*([^|}]*)', re.IGNORECASE)
DATE_PATTERN = re.compile(r'\|\s*(?:date|year)\s*=\s*([^|}]*)', re.IGNORECASE)
YEAR_PATTERN = re.compile(r'\d{4}')
DAY_PATTERN = re.compile(r'\b([1-9]|[12][0-9]|3[01])\b')

# Coordinate regex (simplified for {{Coord|lat|lon|...}})
# Matches {{Coord|12|34|N|56|78|W|...}} or {{Coord|12.34|-56.78|...}}
COORD_PATTERN = re.compile(r'\{\{Coord\s*\|(.*?)\}\}', re.IGNORECASE)

# Global Constants
MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

class Command(BaseCommand):
    help = 'Parses a Wikipedia XML dump and saves article titles, oldest dates, and coordinates to the database.'

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str, help='Path to the Wikipedia XML dump file')
        parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for database inserts')

    def handle(self, *args, **options):
        filename = options['filename']
        batch_size = options['batch_size']

        if not os.path.exists(filename):
            self.stderr.write(self.style.ERROR(f"Error: File '{filename}' not found."))
            return

        self.stdout.write(f"Starting to parse {filename}...")
        self.parse_xml(filename, batch_size)

    def parse_xml(self, filename, batch_size):
        """
        Parses a Wikipedia XML dump iteratively and saves article titles, oldest ref dates,
        and coordinates to PostgreSQL via Django ORM.
        """
        
        articles_to_create = []
        articles_processed_count = 0
        articles_saved_count = 0

        # We use a try-except block to handle cases where the file might be truncated
        try:
            context = ET.iterparse(filename, events=("end",))
            for event, elem in context:
                tag_name = elem.tag
                # Remove namespace for easier comparison if present
                if '}' in tag_name:
                    tag_name = tag_name.split('}', 1)[1]

                if tag_name == 'page':
                    articles_processed_count += 1
                    
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
                    
                    if title_text and text_content:
                        oldest_date = self.extract_oldest_date(text_content)
                        coordinates = self.extract_coordinates(text_content)
                        
                        # Only save if we have both date and coordinates
                        if coordinates:
                            article = Article(
                                title=title_text[:200], # Truncate title if too long
                                oldest_date=oldest_date,
                                coordinates=coordinates
                            )
                            articles_to_create.append(article)
                            articles_saved_count += 1

                        if len(articles_to_create) >= batch_size:
                            Article.objects.bulk_create(articles_to_create)
                            self.stdout.write(f"Saved {articles_saved_count} articles... (Latest: {title_text})")
                            articles_to_create = []

                    # Clear the element from memory
                    elem.clear()
            
            # Insert remaining records
            if articles_to_create:
                Article.objects.bulk_create(articles_to_create)
                
            self.stdout.write(self.style.SUCCESS(f"Finished. Processed {articles_processed_count} pages. Saved {articles_saved_count} articles."))

        except ET.ParseError as e:
            # Commit whatever we have so far
            if articles_to_create:
                Article.objects.bulk_create(articles_to_create)
            self.stderr.write(self.style.WARNING(f"Parse error (expected for truncated file): {e}"))
        except Exception as e:
            if articles_to_create:
                Article.objects.bulk_create(articles_to_create)
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e}"))


    def extract_oldest_date(self, text_content):
        oldest_date = None
        matches = CITATION_PATTERN.finditer(text_content)
        
        for match in matches:
            template_text = match.group(0)
            date_str = None
            date_match = DATE_PATTERN.search(template_text)
            if date_match:
                date_str = date_match.group(1).strip()
            
            if date_str:
                parsed_date = self.parse_date_string(date_str)
                if parsed_date:
                    if oldest_date is None or parsed_date < oldest_date:
                        oldest_date = parsed_date
        return oldest_date

    def parse_date_string(self, date_str):
        # Heuristic parsing for common formats in Wikipedia
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
                date_str_no_year = date_str.replace(str(year), '', 1)
                day_match = DAY_PATTERN.search(date_str_no_year)
                if day_match:
                    day = int(day_match.group(1))
                    
                return date(year, month, day)
        except Exception:
            pass
        return None

    def extract_coordinates(self, text_content):
        """
        Extracts coordinates from {{Coord|...}} template.
        Returns a Point object or None.
        Handles:
            {{Coord|57|18|22|N|4|27|32|W|...}}
            {{Coord|44.112|N|87.913|W|...}}
            {{Coord|44.112|-87.913|...}}
        """
        match = COORD_PATTERN.search(text_content)
        if not match:
            return None
        
        params = match.group(1).split('|')
        # Filter out empty strings and non-coordinate params (like display=title)
        clean_params = []
        for p in params:
            p = p.strip()
            if not p: continue
            if '=' in p: continue # Skip named params
            clean_params.append(p)
            
        if not clean_params:
            return None

        try:
            lat = 0.0
            lon = 0.0
            
            # Case 1: Decimal degrees: {{Coord|lat|lon|...}}
            # Logic: If first two are numbers and not N/S/E/W, assume decimal
            if len(clean_params) >= 2 and self.is_number(clean_params[0]) and self.is_number(clean_params[1]):
                lat = float(clean_params[0])
                lon = float(clean_params[1])
                # Check for N/S/E/W after
                if len(clean_params) > 2:
                    if clean_params[2].upper() == 'S': lat = -lat
                    if clean_params[2].upper() == 'W': lon = -lon
                    if len(clean_params) > 3 and clean_params[3].upper() == 'W': lon = -lon # Handle {{Coord|lat|N|lon|W}} mixed case unlikely but safer

            # Case 2: DMS or DM : {{Coord|deg|min|sec|dir|...}}
            else:
                layout = []
                values = []
                for p in clean_params:
                    if self.is_number(p):
                        values.append(float(p))
                    elif p.upper() in ['N', 'S', 'E', 'W']:
                        layout.append(p.upper())
                
                # We need at least one direction or we can't be sure (unless it fell into Case 1)
                # Parse logic is complex, simplified version:
                # Expect structure like: [vals...] [N/S] [vals...] [E/W]
                
                # Split values into lat parts and lon parts based on direction
                lat_val = 0.0
                lon_val = 0.0
                
                current_vals = []
                lat_done = False
                
                val_idx = 0
                for p in clean_params:
                    if self.is_number(p):
                        current_vals.append(float(p))
                    elif p.upper() in ['N', 'S']:
                        lat_val = self.dms_to_dd(current_vals)
                        if p.upper() == 'S': lat_val = -lat_val
                        lat_done = True
                        current_vals = []
                    elif p.upper() in ['E', 'W']:
                         # If we haven't processed lat yet, this is weird for standard structure but we assume it's lon
                        if not lat_done: 
                            # Maybe it was just numbers for lat?
                             pass # Ambiguous, but let's assume this closes the second set
                        lon_val = self.dms_to_dd(current_vals)
                        if p.upper() == 'W': lon_val = -lon_val
                        current_vals = []
                        break # Done finding both
                
                if lat_val == 0.0 and lon_val == 0.0:
                     return None
                
                lat = lat_val
                lon = lon_val

            return Point(lon, lat) # Point takes (x, y) = (lon, lat)

        except Exception:
            return None

    def is_number(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    def dms_to_dd(self, parts):
        """Converts [deg, min, sec] to decimal degrees"""
        if not parts: return 0.0
        dd = parts[0]
        if len(parts) > 1:
            dd += parts[1] / 60.0
        if len(parts) > 2:
            dd += parts[2] / 3600.0
        return dd

