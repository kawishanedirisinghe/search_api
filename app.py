from flask import Flask, request, jsonify
from ddgs import DDGS
import json

app = Flask(__name__)

@app.route('/api/search', methods=['GET'])
def search():
    """
    Search API endpoint
    Parameters:
    - q: search query (required)
    - max_results: number of results (optional, default: 20)
    """
    
    # Get parameters from query string
    query = request.args.get('q')
    max_results = request.args.get('max_results', 20, type=int)
    
    # Validate required parameters
    if not query:
        return jsonify({
            'error': 'Missing required parameter: q (search query)'
        }), 400
    
    try:
        results = []
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                results.append(result)
        
        return jsonify({
            'query': query,
            'max_results': max_results,
            'results_count': len(results),
            'results': results
        })
    
    except Exception as e:
        return jsonify({
            'error': f'Search failed: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'Search API'})

@app.route('/')
def home():
    """API documentation"""
    return '''
    <h1>Search API</h1>
    <p>Available endpoints:</p>
    <ul>
        <li><strong>GET /api/search?q=query&max_results=number</strong> - Perform search</li>
        <li><strong>GET /api/health</strong> - Health check</li>
    </ul>
    <p>Example: <a href="/api/search?q=Elon Musk&max_results=5">/api/search?q=Elon Musk&max_results=5</a></p>
    '''

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
