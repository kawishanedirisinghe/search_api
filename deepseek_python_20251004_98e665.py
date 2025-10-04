import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import quote_plus
from flask import Flask, request, jsonify
from typing import List, Optional, Tuple
from dataclasses import dataclass
import random
import os

app = Flask(__name__)

# Constants for search engines
ABSTRACT_MAX_LENGTH = 300
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/49.0.2623.108 Chrome/49.0.2623.108 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; pt-BR) AppleWebKit/533.3 (KHTML, like Gecko) QtWeb Internet Browser/3.7 http://www.QtWeb.net",
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/532.2 (KHTML, like Gecko) ChromePlus/4.0.222.3 Chrome/4.0.222.3 Safari/532.2",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.4pre) Gecko/20070404 K-Ninja/2.1.3",
    "Mozilla/5.0 (Future Star Technologies Corp.; Star-Blade OS; x86_64; U; en-US) iNet Browser 4.7",
    "Mozilla/5.0 (Windows; U; Windows NT 6.1; rv:2.2) Gecko/20110201",
    "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.13) Gecko/20080414 Firefox/2.0.0.13 Pogo/2.0.0.13.6866",
]

BING_HOST_URL = "https://www.bing.com"
BING_SEARCH_URL = "https://www.bing.com/search?q="

@dataclass
class SearchItem:
    title: str
    url: str
    description: Optional[str] = None

class WebSearchEngine:
    """Base class for web search engines"""
    def perform_search(self, query: str, num_results: int = 10) -> List[SearchItem]:
        raise NotImplementedError("Subclasses must implement perform_search")

class GoogleSearchEngine(WebSearchEngine):
    """Google search engine using googlesearch library only"""
    
    def perform_search(self, query: str, num_results: int = 10) -> List[SearchItem]:
        """
        Google search engine using googlesearch-python library.
        
        Returns results formatted according to SearchItem model.
        """
        try:
            from googlesearch import search as google_lib_search
            
            raw_results = google_lib_search(query, num_results=num_results, advanced=True)
            
            results = []
            for i, item in enumerate(raw_results):
                if isinstance(item, str):
                    # If it's just a URL
                    results.append(
                        SearchItem(
                            title=f"Google Result {i+1}",
                            url=item,
                            description=""
                        )
                    )
                else:
                    # Advanced search returns objects with title, url, description attributes
                    results.append(
                        SearchItem(
                            title=item.title,
                            url=item.url,
                            description=item.description
                        )
                    )
            
            return results
        except Exception as e:
            print(f"Google search error: {e}")
            return []

class BingSearchEngine(WebSearchEngine):
    """Advanced Bing search engine with session management"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://www.bing.com/",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
    
    def perform_search(self, query: str, num_results: int = 10) -> List[SearchItem]:
        if not query:
            return []
        
        list_result = []
        first = 1
        next_url = BING_SEARCH_URL + quote_plus(query)
        
        while len(list_result) < num_results:
            data, next_url = self._parse_html(next_url, rank_start=len(list_result), first=first)
            if data:
                list_result.extend(data)
            if not next_url:
                break
            first += 10
        
        return list_result[:num_results]
    
    def _parse_html(self, url: str, rank_start: int = 0, first: int = 1) -> Tuple[List[SearchItem], Optional[str]]:
        """Parse Bing search result HTML to extract search results"""
        try:
            res = self.session.get(url=url, timeout=10)
            res.encoding = "utf-8"
            root = BeautifulSoup(res.text, "lxml")
            
            list_data = []
            ol_results = root.find("ol", id="b_results")
            if not ol_results:
                return [], None
            
            for li in ol_results.find_all("li", class_="b_algo"):
                try:
                    h2 = li.find("h2")
                    if not h2:
                        continue
                    
                    title = h2.text.strip()
                    url = h2.a["href"].strip() if h2.a else ""
                    
                    p = li.find("p")
                    abstract = p.text.strip() if p else ""
                    
                    if ABSTRACT_MAX_LENGTH and len(abstract) > ABSTRACT_MAX_LENGTH:
                        abstract = abstract[:ABSTRACT_MAX_LENGTH]
                    
                    rank_start += 1
                    
                    list_data.append(
                        SearchItem(
                            title=title or f"Bing Result {rank_start}",
                            url=url,
                            description=abstract
                        )
                    )
                except Exception:
                    continue
            
            next_btn = root.find("a", title="Next page")
            if not next_btn or not next_btn.get("href"):
                return list_data, None
            
            next_url = BING_HOST_URL + next_btn["href"]
            return list_data, next_url
        except Exception as e:
            print(f"Error parsing Bing HTML: {e}")
            return [], None

class BaiduSearchEngine(WebSearchEngine):
    """Advanced Baidu search engine"""
    
    def perform_search(self, query: str, num_results: int = 10) -> List[SearchItem]:
        try:
            from baidusearch.baidusearch import search as baidu_lib_search
            raw_results = baidu_lib_search(query, num_results=num_results)
            
            results = []
            for i, item in enumerate(raw_results):
                if isinstance(item, str):
                    results.append(
                        SearchItem(
                            title=f"Baidu Result {i+1}",
                            url=item,
                            description=""
                        )
                    )
                elif isinstance(item, dict):
                    results.append(
                        SearchItem(
                            title=item.get("title", f"Baidu Result {i+1}"),
                            url=item.get("url", ""),
                            description=item.get("abstract", "")
                        )
                    )
                else:
                    try:
                        results.append(
                            SearchItem(
                                title=getattr(item, "title", f"Baidu Result {i+1}"),
                                url=getattr(item, "url", ""),
                                description=getattr(item, "abstract", "")
                            )
                        )
                    except Exception:
                        results.append(
                            SearchItem(
                                title=f"Baidu Result {i+1}",
                                url=str(item),
                                description=""
                            )
                        )
            return results
        except ImportError:
            print("Baidu search library not installed")
            return []
        except Exception as e:
            print(f"Error with Baidu search: {e}")
            return []

# Initialize search engines
google_engine = GoogleSearchEngine()
bing_engine = BingSearchEngine()
baidu_engine = BaiduSearchEngine()

def search_item_to_dict(item: SearchItem) -> dict:
    """Convert SearchItem to dictionary"""
    return {
        'title': item.title,
        'link': item.url,
        'snippet': item.description or ""
    }

@app.route('/')
def home():
    """API documentation"""
    return jsonify({
        'message': 'Advanced Search API - No API Key Required',
        'version': '2.0',
        'features': [
            'Multiple search engines (Google, Bing, Baidu)',
            'User agent rotation for reliability',
            'Pagination support',
            'Advanced error handling',
            'Class-based architecture'
        ],
        'endpoints': {
            '/search': {
                'method': 'GET',
                'params': {
                    'q': 'search query (required)',
                    'engine': 'google, bing, baidu, or all (default: all)',
                    'num': 'number of results (default: 10)'
                },
                'example': '/search?q=python&engine=all&num=5'
            },
            '/google': {
                'method': 'GET',
                'params': {
                    'q': 'search query (required)',
                    'num': 'number of results (default: 10)'
                },
                'example': '/google?q=python&num=5'
            },
            '/bing': {
                'method': 'GET',
                'params': {
                    'q': 'search query (required)',
                    'num': 'number of results (default: 10)'
                },
                'example': '/bing?q=python&num=5'
            },
            '/baidu': {
                'method': 'GET',
                'params': {
                    'q': 'search query (required)',
                    'num': 'number of results (default: 10)'
                },
                'example': '/baidu?q=python&num=5'
            }
        }
    })

@app.route('/search')
def search():
    """Search multiple engines"""
    query = request.args.get('q', '')
    engine = request.args.get('engine', 'all').lower()
    num_results = min(int(request.args.get('num', 10)), 50)  # Limit to 50 results max
    
    if not query:
        return jsonify({'error': 'Missing query parameter "q"'}), 400
    
    result = {'query': query, 'engines_used': []}
    
    if engine in ['google', 'all']:
        google_results = google_engine.perform_search(query, num_results)
        result['google'] = {
            'count': len(google_results),
            'results': [search_item_to_dict(item) for item in google_results]
        }
        result['engines_used'].append('google')
    
    if engine in ['bing', 'all']:
        bing_results = bing_engine.perform_search(query, num_results)
        result['bing'] = {
            'count': len(bing_results),
            'results': [search_item_to_dict(item) for item in bing_results]
        }
        result['engines_used'].append('bing')
    
    if engine in ['baidu', 'all']:
        baidu_results = baidu_engine.perform_search(query, num_results)
        result['baidu'] = {
            'count': len(baidu_results),
            'results': [search_item_to_dict(item) for item in baidu_results]
        }
        result['engines_used'].append('baidu')
    
    return jsonify(result)

@app.route('/google')
def google_only():
    """Search Google only"""
    query = request.args.get('q', '')
    num_results = min(int(request.args.get('num', 10)), 50)
    
    if not query:
        return jsonify({'error': 'Missing query parameter "q"'}), 400
    
    results = google_engine.perform_search(query, num_results)
    return jsonify({
        'query': query,
        'engine': 'google',
        'count': len(results),
        'results': [search_item_to_dict(item) for item in results]
    })

@app.route('/bing')
def bing_only():
    """Search Bing only"""
    query = request.args.get('q', '')
    num_results = min(int(request.args.get('num', 10)), 50)
    
    if not query:
        return jsonify({'error': 'Missing query parameter "q"'}), 400
    
    results = bing_engine.perform_search(query, num_results)
    return jsonify({
        'query': query,
        'engine': 'bing',
        'count': len(results),
        'results': [search_item_to_dict(item) for item in results]
    })

@app.route('/baidu')
def baidu_only():
    """Search Baidu only"""
    query = request.args.get('q', '')
    num_results = min(int(request.args.get('num', 10)), 50)
    
    if not query:
        return jsonify({'error': 'Missing query parameter "q"'}), 400
    
    results = baidu_engine.perform_search(query, num_results)
    return jsonify({
        'query': query,
        'engine': 'baidu',
        'count': len(results),
        'results': [search_item_to_dict(item) for item in results]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("="*60)
    print("Advanced Search API Server v2.0")
    print("="*60)
    print("\n✨ Features:")
    print("  - Class-based architecture")
    print("  - User agent rotation")
    print("  - Advanced error handling")
    print("  - Session management for Bing")
    print("  - Pagination support")
    print("\n🔍 Available endpoints:")
    print("  GET /           - API documentation")
    print("  GET /search     - Search all engines")
    print("  GET /google     - Search Google only")
    print("  GET /bing       - Search Bing only")
    print("  GET /baidu      - Search Baidu only")
    print("\n📝 Example usage:")
    print(f"  http://0.0.0.0:{port}/search?q=python&num=5")
    print(f"  http://0.0.0.0:{port}/google?q=flask&num=3")
    print(f"  http://0.0.0.0:{port}/bing?q=web+scraping")
    print(f"  http://0.0.0.0:{port}/baidu?q=人工智能&num=5")
    print("="*60)
    app.run(host='0.0.0.0', port=port, debug=False)