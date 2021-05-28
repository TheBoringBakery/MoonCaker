"""
    Flask server that will run the data crawler and provide the RESTful API
"""

from flask import Flask, request, send_file
from flask_restful import Resource, Api
from flask_mail import Mail, Message
from threading import RLock, Condition
import logging
from dotenv import load_dotenv
from os import getcwd, path, environ

app = Flask(__name__)
api = Api(app)

#load environment variables from file .env 
load_dotenv()
if environ['variables-are-set'] == '0':
    print("You need to edit the .env file before you can run this application")
    raise NotImplementedError
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_SERVER'] = environ['mail-server']
app.config['MAIL_USERNAME'] = environ['mail-user']
app.config['MAIL_PASSWORD'] = environ['mail-pass']

mail = Mail(app)

api_lock = RLock()
api_condition = Condition(api_lock)
API_KEY = ""
LOG_FILENAME = "mooncaker.log"

class ApiKeyUpdate(Resource):
    def put(self):
        global API_KEY
        with api_lock:
            API_KEY = request.form['data']
            logging.info("Received a new API key")
            api_condition.notify()
        
        return {"result": "ok"}

class DownloadLog(Resource):
    def get(self):
        return send_file(path.join(getcwd(), LOG_FILENAME), download_name=LOG_FILENAME)

api.add_resource(ApiKeyUpdate, '/set_api_key')
api.add_resource(DownloadLog, '/get_log')

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/send_suggestion/')
def send_suggestion():
    text = "Either this is a test or something went wrong with the parsing of the suggestion, see server log for further information"
    # todo: parse text from POST request
    msg = Message(subject="A suggestion was submitted for Mooncaker!",
                  body=text,
                  sender=environ['mail-user'],
                  recipients=environ['mail-recipients'].split(" "))
    mail.send(msg)
    return {"result": "ok"}


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
            logging.debug("Stopping thread until new API KEY is provided")
            api_condition.wait()
    return API_KEY

if __name__ == "__main__":
    from dataCrawler import start_crawling
    
    logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)
    logging.info('Server has started from main')
    app.run(host="0.0.0.0", debug=True)
    # start_crawling(API_KEY, block_until_new_key)