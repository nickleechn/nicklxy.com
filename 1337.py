# VERSION: 1.0
# AUTHORS: qBittorrent 1337x.to search plugin

import re
from html.parser import HTMLParser

from helpers import retrieve_url
from novaprinter import prettyPrinter


class leet(object):
    url = "https://1337x.to"
    name = "1337x"
    supported_categories = {'all': 'all',
                            'movies': 'Movies',
                            'tv': 'TV', 
                            'music': 'Music',
                            'games': 'Games',
                            'anime': 'Anime',
                            'software': 'Apps'}

    def download_torrent(self, info):
        print(info)

    class MyHtmlParser(HTMLParser):
        """ Parser for 1337x search results """
        def __init__(self, url):
            HTMLParser.__init__(self)
            self.url = url
            self.tbody_found = False
            self.row_found = False
            self.name_cell = False
            self.seeds_cell = False
            self.leech_cell = False
            self.size_cell = False
            self.current_item = {}
            self.cell_count = 0
            self.page_items = 0

        def handle_starttag(self, tag, attrs):
            params = dict(attrs)
            
            if tag == "tbody":
                self.tbody_found = True
                
            elif self.tbody_found and tag == "tr":
                self.row_found = True
                self.current_item = {}
                self.cell_count = 0
                
            elif self.row_found and tag == "td":
                self.cell_count += 1
                # Reset cell flags
                self.name_cell = False
                self.seeds_cell = False
                self.leech_cell = False
                self.size_cell = False
                
                # Set appropriate cell flag based on position
                if self.cell_count == 1:  # Name column
                    self.name_cell = True
                elif self.cell_count == 2:  # Seeders
                    self.seeds_cell = True
                elif self.cell_count == 3:  # Leechers  
                    self.leech_cell = True
                elif self.cell_count == 5:  # Size (usually 5th column)
                    self.size_cell = True
                    
            elif self.name_cell and tag == "a":
                if "href" in params and params["href"].startswith("/torrent/"):
                    self.current_item["desc_link"] = self.url + params["href"]
                    self.current_item["engine_url"] = self.url

        def handle_data(self, data):
            data = data.strip()
            if not data:
                return
                
            if self.name_cell and "name" not in self.current_item:
                self.current_item["name"] = data
            elif self.seeds_cell:
                try:
                    self.current_item["seeds"] = int(data)
                except ValueError:
                    self.current_item["seeds"] = -1
            elif self.leech_cell:
                try:
                    self.current_item["leech"] = int(data)
                except ValueError:
                    self.current_item["leech"] = -1
            elif self.size_cell:
                self.current_item["size"] = data

        def handle_endtag(self, tag):
            if tag == "tbody":
                self.tbody_found = False
            elif tag == "tr" and self.row_found:
                # End of row - process item if valid
                if self.current_item.get("name") and self.current_item.get("desc_link"):
                    # Get magnet link from detail page
                    magnet_link = self._get_magnet_link(self.current_item["desc_link"])
                    if magnet_link:
                        self.current_item["link"] = magnet_link
                        
                        # Set defaults for missing data
                        if "seeds" not in self.current_item:
                            self.current_item["seeds"] = -1
                        if "leech" not in self.current_item:
                            self.current_item["leech"] = -1
                        if "size" not in self.current_item:
                            self.current_item["size"] = "-1"
                            
                        prettyPrinter(self.current_item)
                        self.page_items += 1
                
                self.row_found = False
                self.current_item = {}

        def _get_magnet_link(self, detail_url):
            """Extract magnet link from torrent detail page"""
            try:
                page_content = retrieve_url(detail_url)
                if page_content:
                    # Look for magnet links
                    magnet_match = re.search(r'href=["\']?(magnet:\?[^"\'\s>]+)["\']?', 
                                           page_content, re.IGNORECASE)
                    if magnet_match:
                        return magnet_match.group(1)
                    
                    # Alternative pattern
                    magnet_match2 = re.search(r'(magnet:\?[^\s<>"&]+)', 
                                            page_content, re.IGNORECASE)
                    if magnet_match2:
                        return magnet_match2.group(1)
            except Exception:
                pass
            return None

    def search(self, query, cat='all'):
        """ Performs search """
        category = self.supported_categories[cat]
        
        # Build search URL
        if cat == 'all':
            search_url = f"{self.url}/search/{query}/1/"
        else:
            search_url = f"{self.url}/category-search/{query}/{category}/1/"

        # Parse first page
        parser = self.MyHtmlParser(self.url)
        html = retrieve_url(search_url)
        if html:
            parser.feed(html)
            parser.close()
