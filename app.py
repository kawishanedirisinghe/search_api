from flask import Flask, request, jsonify
from flask_cors import CORS
from ddgs import DDGS
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

class SearchAPI:
    def __init__(self):
        self.max_allowed_results = 50
    
    def perform_search(self, query, max_results=20):
        """Perform search using DuckDuckGo"""
        try:
            if max_results > self.max_allowed_results:
                max_results = self.max_allowed_results
            
            results = []
            with DDGS() as ddgs:
                for result in ddgs.text(query, max_results=max_results):
                    cleaned_result = {
                        'title': result.get('title', ''),
                        'url': result.get('href', ''),
                        'description': result.get('body', ''),
                        'rank': len(results) + 1
                    }
                    results.append(cleaned_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            raise

search_api = SearchAPI()

@app.route('/api/search', methods=['GET'])
def search():
    """Search endpoint"""
    try:
        query = request.args.get('q', '').strip()
        max_results = request.args.get('max_results', 20, type=int)
        
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query (q) parameter is required'
            }), 400
        
        if max_results <= 0:
            max_results = 20
        
        results = search_api.perform_search(query, max_results)
        
        return jsonify({
            'success': True,
            'query': query,
            'max_results': max_results,
            'results_count': len(results),
            'results': results
        })
    
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'Search API'
    })

@app.route('/')
def home():
    return jsonify({
        'message': 'Search API is running',
        'endpoints': {
            'search': '/api/search?q=query&max_results=number',
            'health': '/api/health'
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
