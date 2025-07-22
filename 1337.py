# -*- coding: utf-8 -*-
# VERSION: 1.0
# AUTHORS: qBittorrent search plugin for 1337x.to

try:
    from HTMLParser import HTMLParser
except ModuleNotFoundError:
    from html.parser import HTMLParser

# import qBT modules
try:
    from novaprinter import prettyPrinter
    from helpers import retrieve_url
except ModuleNotFoundError:
    pass

import re

class leet(object):
    """Class used by qBittorrent to search for torrents on 1337x.to"""

    url = 'https://1337x.to'
    name = '1337x'

    # defines which search categories are supported by this search engine
    supported_categories = {
        'all': '',
        'movies': 'Movies',
        'tv': 'TV',
        'music': 'Music',
        'games': 'Games',
        'anime': 'Anime',
        'software': 'Apps'
    }

    class LeetParser(HTMLParser):
        """Parses 1337x.to search results"""

        def __init__(self, results, base_url):
            """Initialize parser"""
            try:
                super().__init__()
            except TypeError:
                HTMLParser.__init__(self)
            
            self.results = results
            self.base_url = base_url
            self.current_item = None
            self.td_counter = -1

        def handle_starttag(self, tag, attrs):
            """Handle opening tags"""
            if tag == 'a':
                self.start_a(attrs)

        def handle_endtag(self, tag):
            """Handle closing tags"""
            if tag == 'td':
                self.start_td()

        def start_a(self, attrs):
            """Handle anchor tags"""
            params = dict(attrs)
            
            # Get torrent name and detail page link from title attribute
            if 'title' in params and 'href' in params and params['href'].startswith('/torrent/'):
                hit = {
                    'name': params['title'],
                    'desc_link': self.base_url + params['href'],
                    'engine_url': self.base_url
                }
                if not self.current_item:
                    self.current_item = hit
                    
            elif 'href' in params and self.current_item:
                # Look for magnet links
                if params['href'].startswith('magnet:?'):
                    self.current_item['link'] = params['href']
                    self.td_counter += 1

        def start_td(self):
            """Handle table cell transitions"""
            if self.td_counter >= 0:
                self.td_counter += 1

            # After processing enough cells, add result and reset
            if self.td_counter >= 4:  # Reduced since we get name from title attribute
                if self.current_item and self.current_item.get('name'):
                    # If no magnet link found, try to get it from detail page
                    if 'link' not in self.current_item:
                        magnet = self._get_magnet_from_page(self.current_item['desc_link'])
                        if magnet:
                            self.current_item['link'] = magnet
                    
                    if 'link' in self.current_item:
                        # Set defaults for missing data
                        if 'seeds' not in self.current_item:
                            self.current_item['seeds'] = -1
                        if 'leech' not in self.current_item:
                            self.current_item['leech'] = -1
                        if 'size' not in self.current_item:
                            self.current_item['size'] = '-1'
                        
                        self.results.append(self.current_item)
                        
                self.current_item = None
                self.td_counter = -1

        def handle_data(self, data):
            """Handle text data"""
            if self.td_counter > 0 and self.td_counter <= 5 and self.current_item:
                data = data.strip()
                if not data:
                    return
                    
                # Size info
                if self.td_counter == 1:
                    self.current_item['size'] = data
                # Seeds
                elif self.td_counter == 2:
                    try:
                        self.current_item['seeds'] = int(data)
                    except ValueError:
                        self.current_item['seeds'] = -1
                # Leechers  
                elif self.td_counter == 3:
                    try:
                        self.current_item['leech'] = int(data)
                    except ValueError:
                        self.current_item['leech'] = -1

        def _get_magnet_from_page(self, detail_url):
            """Get magnet link from detail page"""
            try:
                page_content = retrieve_url(detail_url)
                if page_content:
                    magnet_match = re.search(r'(magnet:\?[^\s<>"&]+)', page_content, re.IGNORECASE)
                    if magnet_match:
                        return magnet_match.group(1)
            except Exception:
                pass
            return None

    def search(self, what, cat='all'):
        """
        Search for torrents on 1337x.to
        
        Parameters:
        :param what: search query string
        :param cat: search category
        """
        # Build search URL
        if cat == 'all':
            url = "{}/search/{}/1/".format(self.url, what)
        else:
            category = self.supported_categories.get(cat, '')
            if category:
                url = "{}/category-search/{}/{}/1/".format(self.url, what, category)
            else:
                url = "{}/search/{}/1/".format(self.url, what)

        hits = []
        page = 1
        parser = self.LeetParser(hits, self.url)
        
        while True:
            # Build URL with page number
            page_url = url.replace('/1/', '/{}/'.format(page))
            res = retrieve_url(page_url)
            
            if not res:
                break
                
            parser.feed(res)
            
            # Print results
            for hit in hits:
                prettyPrinter(hit)

            # Stop if we got less than expected results (end of pages)
            if len(hits) < 20:  # 1337x typically shows 20 results per page
                break
                
            del hits[:]
            page += 1
            
            # Limit to reasonable number of pages
            if page > 10:
                break

        parser.close()
