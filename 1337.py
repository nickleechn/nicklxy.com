# VERSION: 2.0
# AUTHORS: Inspired by Academic Torrents plugin structure
# DESCRIPTION: 1337x.to search plugin for qBittorrent

import re
import sys
from urllib.parse import quote_plus
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Python 3 support with Python 2 fallback
try:
    from html.parser import HTMLParser
except ImportError:
    from HTMLParser import HTMLParser

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from novaprinter import prettyPrinter

class LeetxParser(HTMLParser):
    """HTML parser for extracting torrent data from 1337x search results"""
    
    def __init__(self):
        HTMLParser.__init__(self)
        self.results = []
        self.current_item = {}
        self.inside_table = False
        self.inside_tbody = False
        self.inside_row = False
        self.current_cell = 0
        self.current_tag = None
        self.collecting_data = False
        
    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            # Look for the main results table
            for attr_name, attr_value in attrs:
                if attr_name == 'class' and 'table-list' in attr_value:
                    self.inside_table = True
                    break
                    
        elif self.inside_table and tag == 'tbody':
            self.inside_tbody = True
            
        elif self.inside_tbody and tag == 'tr':
            self.inside_row = True
            self.current_item = {}
            self.current_cell = 0
            
        elif self.inside_row and tag == 'td':
            self.current_cell += 1
            self.collecting_data = True
            
        elif self.inside_row and tag == 'a':
            # Extract torrent links and magnet links
            for attr_name, attr_value in attrs:
                if attr_name == 'href':
                    if attr_value.startswith('/torrent/'):
                        # Torrent detail page link
                        self.current_item['desc_link'] = 'https://1337x.to' + attr_value
                    elif attr_value.startswith('magnet:'):
                        # Magnet link
                        self.current_item['link'] = attr_value
                    break
                    
        self.current_tag = tag
        
    def handle_endtag(self, tag):
        if tag == 'table' and self.inside_table:
            self.inside_table = False
            
        elif tag == 'tbody' and self.inside_tbody:
            self.inside_tbody = False
            
        elif tag == 'tr' and self.inside_row:
            # Finished processing a row, add to results if valid
            if self.current_item.get('name') and self.current_item.get('link'):
                # Set default values for missing data
                if 'seeds' not in self.current_item:
                    self.current_item['seeds'] = -1
                if 'leech' not in self.current_item:
                    self.current_item['leech'] = -1
                if 'size' not in self.current_item:
                    self.current_item['size'] = -1
                if 'desc_link' not in self.current_item:
                    self.current_item['desc_link'] = ''
                    
                self.current_item['engine_url'] = 'https://1337x.to'
                self.results.append(self.current_item.copy())
                
            self.inside_row = False
            self.current_item = {}
            
        elif tag == 'td':
            self.collecting_data = False
            
        self.current_tag = None
        
    def handle_data(self, data):
        if not self.inside_row or not self.collecting_data:
            return
            
        data = data.strip()
        if not data:
            return
            
        # Map cell positions to data fields (approximate structure)
        if self.current_cell == 1:
            # First cell usually contains the torrent name
            if 'name' not in self.current_item:
                self.current_item['name'] = data
        elif self.current_cell == 2:
            # Second cell might contain seeders
            if data.isdigit():
                self.current_item['seeds'] = int(data)
        elif self.current_cell == 3:
            # Third cell might contain leechers
            if data.isdigit():
                self.current_item['leech'] = int(data)
        elif self.current_cell == 4:
            # Fourth cell might contain file size
            if any(unit in data.lower() for unit in ['mb', 'gb', 'kb', 'tb']):
                self.current_item['size'] = data


class leetx(object):
    """Main plugin class for 1337x.to search"""
    
    url = 'https://1337x.to'
    name = '1337x'
    
    supported_categories = {
        'all': 'All',
        'movies': 'Movies', 
        'tv': 'TV',
        'music': 'Music',
        'games': 'Games',
        'anime': 'Anime',
        'software': 'Apps',
        'adult': 'XXX'
    }
    
    def _get_search_url(self, what, cat='all'):
        """Build search URL based on category and search terms"""
        search_query = quote_plus(what)
        
        if cat == 'all':
            return f"{self.url}/search/{search_query}/1/"
        else:
            # Category-specific search
            cat_mapping = {
                'movies': 'Movies',
                'tv': 'TV', 
                'music': 'Music',
                'games': 'Games',
                'anime': 'Anime',
                'software': 'Apps',
                'adult': 'XXX'
            }
            category = cat_mapping.get(cat, 'All')
            return f"{self.url}/category-search/{search_query}/{category}/1/"
    
    def _retrieve_url(self, url):
        """Safely retrieve URL content with proper headers"""
        try:
            # Add user agent to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            req = Request(url, headers=headers)
            response = urlopen(req, timeout=30)
            return response.read().decode('utf-8', errors='ignore')
        except (URLError, HTTPError, UnicodeDecodeError) as e:
            print(f"Error fetching {url}: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            return None
    
    def _extract_magnet_from_page(self, torrent_url):
        """Extract magnet link from torrent detail page"""
        try:
            page_content = self._retrieve_url(torrent_url)
            if not page_content:
                return None
                
            # Look for magnet links in the page
            magnet_pattern = r'href="(magnet:\?[^"]+)"'
            matches = re.findall(magnet_pattern, page_content, re.IGNORECASE)
            
            if matches:
                return matches[0]  # Return first magnet link found
                
            # Alternative pattern for magnet links
            magnet_pattern2 = r'(magnet:\?[^\s<>"]+)'
            matches2 = re.findall(magnet_pattern2, page_content, re.IGNORECASE)
            
            if matches2:
                return matches2[0]
                
        except Exception as e:
            print(f"Error extracting magnet from {torrent_url}: {e}", file=sys.stderr)
            
        return None
    
    def _process_results(self, html_content):
        """Process HTML content and extract torrent results"""
        parser = LeetxParser()
        parser.feed(html_content)
        
        # If no magnet links were found in search results, try to get them from detail pages
        for result in parser.results:
            if not result.get('link') and result.get('desc_link'):
                magnet = self._extract_magnet_from_page(result['desc_link'])
                if magnet:
                    result['link'] = magnet
                    
            # Only output results that have magnet links
            if result.get('link'):
                prettyPrinter(result)
                
    def search(self, what, cat='all'):
        """Main search function called by qBittorrent"""
        if not what.strip():
            return
            
        search_url = self._get_search_url(what, cat)
        
        try:
            html_content = self._retrieve_url(search_url)
            if html_content:
                self._process_results(html_content)
            else:
                print("Failed to retrieve search results", file=sys.stderr)
                
        except Exception as e:
            print(f"Search error: {e}", file=sys.stderr)
            
    def download_torrent(self, info):
        """Download torrent file (not implemented for magnet-only approach)"""
        # For magnet links, qBittorrent handles this automatically
        # This method can be left empty or return the magnet link
        print(info)


# Test the plugin (remove this section for production)
if __name__ == "__main__":
    # Test search functionality
    plugin = leetx()
    print("Testing 1337x plugin...")
    plugin.search("ubuntu", "software")
