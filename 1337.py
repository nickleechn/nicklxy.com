# VERSION: 2.0
# AUTHORS: qBittorrent plugin for 1337x.to
# CONTRIBUTORS: Based on Academic Torrents plugin structure

import re
import sys

# Python 3 support with Python 2 fallback
try:
    from html.parser import HTMLParser
    from urllib.parse import quote_plus
except ImportError:
    from HTMLParser import HTMLParser
    from urllib import quote_plus

# qBittorrent plugin imports
from helpers import retrieve_url
from novaprinter import prettyPrinter

class LeetxParser(HTMLParser):
    """Simplified HTML parser for extracting torrent data from 1337x"""
    
    def __init__(self):
        HTMLParser.__init__(self)
        self.current_item = {}
        self.inside_name_cell = False
        self.inside_seeds_cell = False
        self.inside_leech_cell = False
        self.inside_size_cell = False
        self.name_link = ""
        self.torrent_page_url = ""
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'td':
            # Check if this is a name cell
            if 'class' in attrs_dict and 'name' in attrs_dict['class']:
                self.inside_name_cell = True
                
        elif tag == 'a' and self.inside_name_cell:
            # Extract torrent name link
            if 'href' in attrs_dict and attrs_dict['href'].startswith('/torrent/'):
                self.torrent_page_url = 'https://1337x.to' + attrs_dict['href']
                
        elif tag == 'a':
            # Look for magnet links anywhere in the page
            if 'href' in attrs_dict and attrs_dict['href'].startswith('magnet:'):
                self.current_item['link'] = attrs_dict['href']
                
    def handle_endtag(self, tag):
        if tag == 'td':
            self.inside_name_cell = False
            self.inside_seeds_cell = False
            self.inside_leech_cell = False
            self.inside_size_cell = False
            
    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
            
        if self.inside_name_cell and not self.current_item.get('name'):
            self.current_item['name'] = data
            if self.torrent_page_url:
                self.current_item['desc_link'] = self.torrent_page_url


class leet(object):
    """qBittorrent search plugin for 1337x.to"""
    
    url = 'https://1337x.to'
    name = '1337x'
    
    supported_categories = {
        'all': 'All',
        'movies': 'Movies', 
        'tv': 'TV',
        'music': 'Music',
        'games': 'Games',
        'anime': 'Anime',
        'software': 'Apps'
    }
    
    def _get_magnet_from_page(self, torrent_url):
        """Extract magnet link from torrent detail page"""
        try:
            print(f"DEBUG: Fetching magnet from: {torrent_url}")
            page_content = retrieve_url(torrent_url)
            if not page_content:
                print("DEBUG: No page content received")
                return None
                
            print(f"DEBUG: Got {len(page_content)} characters from detail page")
            
            # Simple regex to find magnet links
            magnet_pattern = r'magnet:\?[^\s<>"&]*'
            matches = re.findall(magnet_pattern, page_content, re.IGNORECASE)
            
            print(f"DEBUG: Found {len(matches)} potential magnet links")
            
            if matches:
                # Return the longest magnet link (usually most complete)
                best_magnet = max(matches, key=len)
                print(f"DEBUG: Selected magnet link: {best_magnet[:100]}...")
                return best_magnet
            else:
                print("DEBUG: No magnet links found in page")
                
        except Exception as e:
            print(f"DEBUG: Error getting magnet from {torrent_url}: {e}")
            import traceback
            traceback.print_exc()
            
        return None
    
    def _parse_size(self, size_str):
        """Convert size string to standardized format"""
        if not size_str or size_str == '-':
            return '-1'
        return size_str
        
    def _parse_seeds_leech(self, text):
        """Parse seeds/leech numbers from text"""
        if not text or not text.isdigit():
            return -1
        return int(text)
    
    def search(self, what, cat='all'):
        """Main search function"""
        what = what.strip()
        if not what:
            print("DEBUG: Empty search query")
            return
            
        print(f"DEBUG: Starting search for '{what}' in category '{cat}'")
        
        # Build search URL
        query = quote_plus(what)
        if cat == 'all':
            search_url = f"{self.url}/search/{query}/1/"
        else:
            # Category search  
            cat_name = self.supported_categories.get(cat, 'All')
            search_url = f"{self.url}/category-search/{query}/{cat_name}/1/"
        
        print(f"DEBUG: Search URL: {search_url}")
        
        try:
            # Get search results page
            html = retrieve_url(search_url)
            if not html:
                print("DEBUG: Failed to retrieve search page")
                return
                
            print(f"DEBUG: Retrieved {len(html)} characters of HTML")
            
            # Look for table rows with torrent data
            # Use a simple regex approach since the site structure can vary
            self._extract_torrents_simple(html)
            
        except Exception as e:
            print(f"DEBUG: Search error: {e}")
            import traceback
            traceback.print_exc()
    
    def _extract_torrents_simple(self, html):
        """Simple torrent extraction using regex patterns"""
        try:
            print("DEBUG: Starting torrent extraction")
            
            # Pattern to match torrent rows in table
            # This is a simplified approach that looks for common patterns
            row_pattern = r'<tr[^>]*>.*?</tr>'
            rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)
            
            print(f"DEBUG: Found {len(rows)} table rows")
            
            results_count = 0
            for i, row in enumerate(rows):
                # Skip header rows
                if '<th' in row.lower():
                    continue
                    
                # Extract torrent page link and name
                name_match = re.search(r'<a[^>]+href="/torrent/([^"]+)"[^>]*>([^<]+)</a>', row, re.IGNORECASE)
                if not name_match:
                    continue
                    
                torrent_path = name_match.group(1)
                torrent_name = name_match.group(2).strip()
                torrent_url = f"{self.url}/torrent/{torrent_path}"
                
                print(f"DEBUG: Processing torrent {i+1}: {torrent_name}")
                
                # Try to extract seeds and leechers from the row
                seeds = -1
                leech = -1
                size = '-1'
                
                # Look for numbers that might be seeds/leechers
                numbers = re.findall(r'>(\d+)<', row)
                if len(numbers) >= 2:
                    seeds = int(numbers[0]) if numbers[0].isdigit() else -1
                    leech = int(numbers[1]) if numbers[1].isdigit() else -1
                
                # Look for size information
                size_match = re.search(r'>([0-9.]+\s*[KMGT]?B)<', row, re.IGNORECASE)
                if size_match:
                    size = size_match.group(1)
                
                print(f"DEBUG: Getting magnet link for: {torrent_url}")
                
                # Get magnet link from detail page
                magnet_link = self._get_magnet_from_page(torrent_url)
                
                if magnet_link and torrent_name:
                    result = {
                        'link': magnet_link,
                        'name': torrent_name,
                        'size': size,
                        'seeds': seeds,
                        'leech': leech,
                        'engine_url': self.url,
                        'desc_link': torrent_url
                    }
                    
                    print(f"DEBUG: Found valid result: {torrent_name}")
                    prettyPrinter(result)
                    results_count += 1
                else:
                    print(f"DEBUG: No magnet link found for: {torrent_name}")
                    
            print(f"DEBUG: Extraction complete. Found {results_count} valid torrents")
                    
        except Exception as e:
            print(f"DEBUG: Extraction error: {e}")
            import traceback
            traceback.print_exc()
    
    def download_torrent(self, info):
        """Handle torrent download (not needed for magnet links)"""
        print(info)
