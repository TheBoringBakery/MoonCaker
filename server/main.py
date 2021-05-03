"""
    Flask server that will run the data crawler and provide the RESTful API
"""

from flask import Flask, request
from flask_restful import Resource, Api

app = Flask(__name__)
api = Api(app)

API_KEY = ""

class ApiKeyUpdate(Resource):
    def put(self):
        API_KEY = request.form['data']
        return {"result": "ok"}


api.add_resource(ApiKeyUpdate, '/set_api_key')

@app.route('/')
def hello_world():
    return 'Hello, World!'