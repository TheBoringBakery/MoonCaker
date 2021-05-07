"""
    Flask server that will run the data crawler and provide the RESTful API
"""

from flask import Flask, request
from flask_restful import Resource, Api
from threading import RLock, Condition

app = Flask(__name__)
api = Api(app)

api_lock = RLock()
api_condition = Condition(api_lock)
API_KEY = ""

class ApiKeyUpdate(Resource):
    def put(self):
        global API_KEY
        with api_lock:
            API_KEY = request.form['data']
            api_condition.notify()
        
        return {"result": "ok"}


api.add_resource(ApiKeyUpdate, '/set_api_key')

@app.route('/')
def hello_world():
    return 'Hello, World!'

def block_until_new_key():
    """
        This gets called once the API key expires, it will block until a new API key is sent to the server

        Returns:
            str: The new API key
    """
    global API_KEY
    with api_lock:
        API_KEY = ""
        while not API_KEY:
            api_condition.wait()
    return API_KEY

if __name__ == "__main__":
    from dataCrawler import start_crawling

    start_crawling(API_KEY, block_until_new_key)