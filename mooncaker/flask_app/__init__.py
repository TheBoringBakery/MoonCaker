from os import path, getcwd, environ
from functools import partial
from logging import WARNING, DEBUG, INFO
from multiprocessing import Process, Queue
from flask import Flask
from flask_restful import Api
from flask_bootstrap import Bootstrap
from flask_mail import Mail, Message
from flask_talisman import Talisman
from dotenv import load_dotenv
from mooncaker.external_tools.data_crawler import Crawler
from mooncaker.external_tools.mooncaker_bot import MooncakerBot
from mooncaker.external_tools.logger import log as log_raw

app = Flask(__name__)
api = Api(app)
# Talisman(app, force_https=False)

log = partial(log_raw, 'mooncaker')
log(INFO, 'Server has started from main')

# load environment variables from file .env
load_dotenv()
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
if 'testing' in environ:
    app.config['TESTING'] = True
try:
    app.config['MAIL_SERVER'] = environ['mail-server']
    app.config['MAIL_USERNAME'] = environ['mail-user']
    app.config['MAIL_PASSWORD'] = environ['mail-pass']
    app.config['MAIL_RECIPIENTS'] = environ['mail-recipients'].split(" ")
    app.config['SECRET_KEY'] = environ['secret-key']
    app.config['SALT'] = environ['hash-salt'].encode('latin1').decode('unicode-escape').encode('latin1')
    app.config['ADMIN_USER'] = environ['admin-user']
    app.config['ADMIN_PASS'] = environ['admin-hashed-pass'].encode('latin1') \
                                                           .decode('unicode-escape') \
                                                           .encode('latin1')
    app.config['TELEGRAM_TOKEN'] = environ['telegram-token']
    app.config['TELEGRAM_WHITELIST'] = environ['telegram-whitelist']
    app.config['TELEGRAM_REMINDER_CHAT_ID'] = environ['telegram-reminder-chat-id']
except KeyError:
    print("The .env file was improperly set, please check the README for further information")
    exit()

mail = Mail(app)
Bootstrap(app)

api_key_queue = Queue()  # Where the new API key will be put

bot = MooncakerBot(app.config['TELEGRAM_TOKEN'],
                   api_key_queue.put,
                   app.config['TELEGRAM_WHITELIST'])

bot_process = Process(target=bot.start_bot)
bot_process.start()
log(INFO, "Starting telegram bot")


def get_api_key():
    """
    Function that get called when a new api key is required
    It sends an email and a telegram message to warn the admins of this need
    and hangs waiting for a new key

    Returns:
        str: the new api key
    """
    with app.app_context():
        msg = Message(subject="Mooncaker needs your attention",
                      body="Notice me senpai, I need a new API key!\n"
                      + "A quick link for you! https://developer.riotgames.com/",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=app.config['MAIL_RECIPIENTS'])
        mail.send(msg)
    log(INFO, "Signal email sent")
    bot.send_new_api_reminder(app.config['TELEGRAM_REMINDER_CHAT_ID'])
    log(INFO, "Signal telegram message sent")
    return api_key_queue.get()


crawler = Crawler("NotAnAPIKey", get_api_key)
crawling_process = Process(target=crawler.start_crawling)
crawling_process.start()
log(INFO, "Starting datacrawling")

from flask_app import routes
