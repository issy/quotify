from flask import Flask, request
from urllib.parse import unquote
import utils as db
import config


app = Flask(__name__)


# Get random quotes
@app.route('/api/v1/get-random-quotes', methods=['GET'])
def _random_quotes():
    args = request.args
    n_quotes = int(args['n']) if 'n' in args else 1
    if not 1 <= n_quotes >= config.RANDOM_QUOTES_UPPER_LIMIT:
        n_quotes = 1 if n_quotes < 1 else config.RANDOM_QUOTES_UPPER_LIMIT
    quotes = db.get_random_quotes(n_quotes)
    if not quotes:
        return {'message': 'No quotes found'}, 404
    return list(quotes), 200


# Get quote by ID
@app.route('/api/v1/get-quote-by-id', methods=['GET'])
def _quote_by_id():
    args = request.args
    if 'id' not in args:
        return {'message': 'Query parameter missing'}, 400
    quote_id = args['id']
    try:
        quote = db.get_quote_by_id(quote_id)
    except db.QuoteNotFound:
        return {'message': 'Quote not found'}, 404
    return quote, 200


# Search for quotes
@app.route('/api/v1/search', methods=['GET'])
def _search():
    args = request.args
    if 'q' not in args:
        return {'message': 'Missing search query'}, 400
    query = unquote(args['q'])
    try:
        quotes = db.search(query)
    except db.QuoteNotFound:
        return {'message': 'No quotes found'}, 404
    return list(quotes)


# Add quote
@app.route('/api/v1/add-quote', methods=['POST'])
def _add():
    if 'Authorization' not in request.headers or not db.is_authorized(request.headers['Authorization']):
        return {'message': "Unauthorized"}, 403
    try:
        data = request.get_json(force=False, silent=False)
    except:
        return {'message': 'Malformed request'}, 400
    try:
        db.check_request(data)
    except (db.ForeignType, db.MissingField):
        return {'message': 'Malformed request'}, 400
    quote = db.add_quote(data)
    return {
        'message': 'Quote successfully created',
        'id': quote.id,
        'permalink': f'{config.MAIN_SITE_BASE_URL}/id/{quote.id}'
    }, 201


# Delete quote
@app.route('/api/v1/delete-quote/<id>', methods=['DELETE'])
def _delete_quote(quote_id):
    if 'Authorization' not in request.headers or not db.is_authorized(request.headers['Authorization']):
        return {'message': "Unauthorized"}, 403
    try:
        quote = db.get_quote_by_id(quote_id)
    except db.QuoteNotFound:
        return {'message': f'Quote with ID {quote_id} not found'}, 404
    db.delete_quote(quote_id)
    return {'message': f'Quote with ID {quote_id} successfully deleted'}, 200


if __name__ == '__main__':
    app.run(debug=True)
