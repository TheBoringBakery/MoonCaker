"""
    Flask server that will run the data crawler and provide the RESTful API
"""
from mooncaker import app

if __name__ == "__main__":
    # from dataCrawler import start_crawling
    
    app.run(host="0.0.0.0", debug=True)
    # start_crawling(API_KEY, block_until_new_key)