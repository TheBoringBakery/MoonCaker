import logging
from functools import partial

from pymongo import MongoClient
from telegram import Update, ForceReply, Sticker, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from os import getcwd, path
from mooncaker import app

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)
waiting_api_key_key = False

# Define a few command handlers. These usually take the two arguments update and
# context.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    sticker= Sticker('CAACAgUAAxkBAAECjRVg5uYDQV50eYErYbW-52OzbJ9eWgACkh4AAsZRxhWMjlg7SAq03yAE','CAACAgUAAxkBAAECjRVg5uYDQV50eYErYbW-52OzbJ9eWgACkh4AAsZRxhWMjlg7SAq03yAE',512,512,False)
    update.message.reply_sticker(sticker)
    update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()} onii\-chan\!',
        reply_markup=ForceReply(selective=True),
    )
    keyboard = [
        [
            InlineKeyboardButton("Command list", callback_data='1'),
            InlineKeyboardButton("Cheer onii-chan", callback_data='2'),
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('How can I help you?', reply_markup=reply_markup)

def button(update: Update, context: CallbackContext) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    query.answer()
    if query.data == '1':
            query.edit_message_text(text=f"Available commands: \n /get_last_10_log \n /set_api_key \n /get_ReDiTi \n /get_count")
    else:
        query.edit_message_text(text=f"You are the best, onii-chan! I will always support you!")

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def get_last_10_log(update: Update, context: CallbackContext) -> None:
    with open(path.join(getcwd(), app.config['LOG_FILENAME'])) as file:
        res = ""
        for line in (file.readlines()[-10:]):
            res = res + line
    update.message.reply_text(res)



def set_api_key(update: Update, context: CallbackContext) -> None:
    global waiting_api_key
    waiting_api_key = True
    update.message.reply_text(f"Gimme the new API key")


def others(update: Update, context: CallbackContext, set_api) -> None:
    global waiting_api_key
    if waiting_api_key:
        set_api(update.message.text)
        waiting_api_key = False

def get_ReDiTi(update: Update, context: CallbackContext) -> None:
    cluster = MongoClient("mongodb://datacaker:27017", connect=True)
    db = cluster.get_database("mooncaker")
    rediti = db.get_collection("ReDiTi")
    rediti = [elem for elem in rediti.find()]
    update.message.reply_text(str(rediti))

def get_count(update: Update, context: CallbackContext) -> None:
    cluster = MongoClient("mongodb://datacaker:27017", connect=True)
    db = cluster.get_database("mooncaker")
    m = db.get_collection("matches")
    update.message.reply_text(str(m.count_documents()))

#TODO move get_count etc to dataCrawler
def start_bot(token, set_api) -> None:

    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    dispatcher.add_handler(CommandHandler("get_last_10_log", get_last_10_log))
    dispatcher.add_handler(CommandHandler("set_api_key", set_api_key))
    dispatcher.add_handler(CommandHandler("get_ReDiTi", get_ReDiTi))
    dispatcher.add_handler(CommandHandler("get_count", get_count))

    partial_set_api = partial(others, set_api=set_api)
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, partial_set_api))

    # Start the Bot
    updater.start_polling()
    updater.idle()

def main():
    pass

if __name__ == '__main__':
    main()