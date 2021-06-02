from flask import Flask
from flask_restful import Api
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from dotenv import load_dotenv
from os import environ
from threading import RLock, Condition
import logging

app = Flask(__name__)
api = Api(app)


LOG_FILENAME = "mooncaker.log"
app.config['LOG_FILENAME'] = LOG_FILENAME
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)
logging.info('Server has started from main')

#load environment variables from file .env 
load_dotenv()
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
try:
    app.config['MAIL_SERVER'] = environ['mail-server']
    app.config['MAIL_USERNAME'] = environ['mail-user']
    app.config['MAIL_PASSWORD'] = environ['mail-pass']
    app.config['SECRET_KEY'] = environ['secret-key']
    app.config['SALT'] = environ['hash-salt'].encode('latin1').decode('unicode-escape').encode('latin1')
    app.config['ADMIN_USER'] = environ['admin-user']
    app.config['ADMIN_PASS'] = environ['admin-hashed-pass'].encode('latin1').decode('unicode-escape').encode('latin1')
except KeyError:
    print("The .env file was improperly set, please check the README for further information")
    exit()

mail = Mail(app)
Bootstrap(app)

api_lock = RLock()
api_condition = Condition(api_lock)
API_KEY = ""

from mooncaker import routes