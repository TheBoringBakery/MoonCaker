"""
    Flask server that will run the data crawler and provide the RESTful API
"""

from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Hello, World!'