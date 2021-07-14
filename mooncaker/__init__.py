from os import path, getcwd

from flask import Flask
from flask_restful import Api
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_talisman import Talisman
from dotenv import load_dotenv
from os import environ
from multiprocessing import Process, Queue
from mooncaker.external_tools.data_crawler import Crawler
from mooncaker.external_tools.telegram_bot import start_bot
import logging

app = Flask(__name__)
api = Api(app)
# Talisman(app, force_https=False)


LOG_FILENAME = "mooncaker.log"
app.config['LOG_FILENAME'] = LOG_FILENAME
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)
logging.info('mooncaker: Server has started from main')

# load environment variables from file .env
load_dotenv()
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
try:
    app.config['MAIL_SERVER'] = environ['mail-server']
    app.config['MAIL_USERNAME'] = environ['mail-user']
    app.config['MAIL_PASSWORD'] = environ['mail-pass']
    app.config['SECRET_KEY'] = environ['secret-key']
    app.config['SALT'] = environ['hash-salt'].encode('latin1').decode('unicode-escape').encode('latin1')
    app.config['ADMIN_USER'] = environ['admin-user']
    app.config['ADMIN_PASS'] = environ['admin-hashed-pass'].encode('latin1').decode('unicode-escape').encode('latin1')
    app.config['TELEGRAM_TOKEN'] = environ['telegram-token']
    app.config['TELEGRAM_WHITELIST'] = environ['telegram-whitelist']

except KeyError:
    print("The .env file was improperly set, please check the README for further information")
    exit()

mail = Mail(app)
Bootstrap(app)

api_key_queue = Queue()
DUMMY_API_KEY = "RGAPI-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"  # this key DOESN'T work but it's needed to start the process.
# TODO (low): can we avoid using the above key ?

crawler = Crawler(DUMMY_API_KEY, api_key_queue.get)
crawling_process = Process(target=crawler.start_crawling)
crawling_process.start()
logging.info("mooncaker: starting datacrawling")
bot_process = Process(target=start_bot,
                      args=(app.config['TELEGRAM_TOKEN'],
                            api_key_queue.put,
                            path.join(getcwd(), app.config['LOG_FILENAME']),
                            app.config['TELEGRAM_WHITELIST'],))
bot_process.start()
logging.info("mooncaker: starting telegram bot")

from mooncaker import routes
