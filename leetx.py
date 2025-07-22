# VERSION: 1.00
# AUTHORS: qBittorrent Community Plugin
# CONTRIBUTORS: Based on official plugin structure

import re
from html.parser import HTMLParser
from helpers import retrieve_url
from novaprinter import prettyPrinter


class leetx(object):
    """
    1337x.to search plugin for qBittorrent
    """
    url = 'https://1337x.to'
    name = '1337x'
    supported_categories = {
        'all': 'all',
        'anime': 'Anime',
        'books': 'Books',
        'games': 'Games',
        'movies': 'Movies',
        'music': 'Music',
        'software': 'Apps',
        'tv': 'TV'
    }

    def download_torrent(self, info):
        """
        Optional method for downloading torrents
        """
        print(info)

    def search(self, what, cat='all'):
        """
        Search for torrents on 1337x.to
        
        what: search query string (already escaped)
        cat: search category
        """
        category = self.supported_categories[cat]
        
        # Build search URL
        if cat == 'all':
            search_url = f"{self.url}/search/{what}/1/"
        else:
            search_url = f"{self.url}/category-search/{what}/{category}/1/"
        
        # Retrieve search results page
        try:
            html = retrieve_url(search_url)
            if html:
                self._parse_search_results(html)
        except Exception:
            # Fail silently as per qBittorrent convention
            pass

    def _parse_search_results(self, html):
        """
        Parse search results from HTML and print using prettyPrinter
        """
        try:
            # Use regex to find torrent table rows
            # This is more reliable than complex HTML parsing for 1337x
            row_pattern = r'<tr[^>]*>.*?</tr>'
            rows = re.findall(row_pattern, html, re.DOTALL | re.IGNORECASE)
            
            for row in rows:
                # Skip header rows
                if '<th' in row.lower() or 'class="header"' in row.lower():
                    continue
                
                # Extract torrent name and detail page link
                name_match = re.search(r'<a[^>]+href="/torrent/([^"]+)"[^>]*title="([^"]*)"', row, re.IGNORECASE)
                if not name_match:
                    # Try alternative pattern
                    name_match = re.search(r'<a[^>]+href="/torrent/([^"]+)"[^>]*>([^<]+)</a>', row, re.IGNORECASE)
                
                if not name_match:
                    continue
                
                torrent_path = name_match.group(1)
                torrent_name = name_match.group(2).strip()
                
                # Skip if name is empty
                if not torrent_name:
                    continue
                
                detail_url = f"{self.url}/torrent/{torrent_path}"
                
                # Extract seeds and leechers
                seeds = self._extract_number(row, 0)  # First number is usually seeds
                leech = self._extract_number(row, 1)  # Second number is usually leechers
                
                # Extract size
                size = self._extract_size(row)
                
                # Get magnet link from detail page
                magnet_link = self._get_magnet_link(detail_url)
                
                if magnet_link:
                    # Create result dictionary with all required fields
                    result = {
                        'link': magnet_link,
                        'name': torrent_name,
                        'size': size,
                        'seeds': seeds,
                        'leech': leech,
                        'engine_url': self.url,
                        'desc_link': detail_url,
                        'pub_date': -1  # 1337x doesn't provide reliable dates
                    }
                    
                    # Print result using qBittorrent's standard function
                    prettyPrinter(result)
        
        except Exception:
            # Fail silently
            pass

    def _extract_number(self, html_row, index):
        """Extract number by index from HTML row"""
        try:
            numbers = re.findall(r'>(\d+)<', html_row)
            if len(numbers) > index and numbers[index].isdigit():
                return int(numbers[index])
        except Exception:
            pass
        return -1

    def _extract_size(self, html_row):
        """Extract file size from HTML row"""
        try:
            size_match = re.search(r'>([0-9.]+\s*[KMGT]?B)<', html_row, re.IGNORECASE)
            if size_match:
                return size_match.group(1)
        except Exception:
            pass
        return '-1'

    def _get_magnet_link(self, detail_url):
        """
        Get magnet link from torrent detail page
        """
        try:
            html = retrieve_url(detail_url)
            if not html:
                return None
            
            # Look for magnet links using multiple patterns
            patterns = [
                r'href="(magnet:\?[^"]+)"',
                r"href='(magnet:\?[^']+)'",
                r'(magnet:\?xt=urn:btih:[a-fA-F0-9]{40}[^\s<>"]*)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    return match.group(1)
            
        except Exception:
            pass
        
        return None
