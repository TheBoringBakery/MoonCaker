from functools import partial
from pymongo import MongoClient
from telegram import Update, ForceReply, Sticker, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler, \
    ConversationHandler
from os import remove

WAITING_API = 0
SAD_ZOE = 'CAACAgIAAxkBAAECkWNg7Fo-k6squNhgN_2bLL2X3F6DhQACWwADsiFfFVNQKDUCqm9IIAQ'
MEGUMIN_THUMB_UP = 'CAACAgUAAxkBAAECkXNg7GRAgV-Bw0QddeuTXXLcS_WV7gACnBwAAsZRxhXGsrj-QloNWyAE'
PARTY_GIRL = 'CAACAgUAAxkBAAECkXFg7GNN3M6hwcJb21P74JELHq0mHQACpxwAAsZRxhXfhZz2U_6oByAE'
LOLI = 'CAACAgUAAxkBAAECjRVg5uYDQV50eYErYbW-52OzbJ9eWgACkh4AAsZRxhWMjlg7SAq03yAE'
NAME_TO_STICKER = {name: Sticker(name, name, 512, 512, False) for name in [SAD_ZOE, MEGUMIN_THUMB_UP, PARTY_GIRL, LOLI]}


def authorize_and_dispatch(update: Update, context: CallbackContext, dispatcher, whitelist):
    if update.effective_user.username in whitelist.split():
        return dispatcher(update=update, context=context)
    else:
        update.message.reply_sticker(NAME_TO_STICKER[SAD_ZOE])
        update.message.reply_text("Sorry, you cannot do that")


def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_sticker(NAME_TO_STICKER[LOLI])
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
        query.edit_message_text(
            text=f"Available commands: \n /get_full_log \n /get_last_10_log \n /set_api_key \n /get_ReDiTi \n /get_count")
    else:
        query.edit_message_text(text=f"You are the best, onii-chan! I will always support you!")


def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Help!')


def get_log(update: Update, context: CallbackContext, log_filename, lines=None) -> None:
    with open(log_filename) as log:
        if not lines is None:
            with open("tmp.txt", "a") as less_log:
                for line in (log.readlines()[-lines:]):
                    less_log.write(line + "\n")
            with open("tmp.txt", "r") as less_log:
                context.bot.send_document(chat_id=update.effective_chat.id, document=less_log,
                                          filename="last_10_lines_of_log.txt")
            remove("tmp.txt")
        else:
            context.bot.send_document(chat_id=update.effective_chat.id, document=log,
                                      filename="full_log.txt")


def set_api_key_req(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        f"Please gimme all your new API key, I want it so bad..or use /cancel to make me stop waiting..")
    return WAITING_API


def set_new_api(update: Update, context: CallbackContext, set_api) -> None:
    new_api = update.message.text
    if len(new_api) != 42:
        update.message.reply_sticker(NAME_TO_STICKER[SAD_ZOE])
        update.message.reply_text('Why r u tryin to troll me, insert a valid key baka')
        return WAITING_API
    set_api(update.message.text)
    update.message.reply_sticker(NAME_TO_STICKER[PARTY_GIRL])
    update.message.reply_text(f"New API key set! Hurray!")
    return ConversationHandler.END


def get_ReDiTi(update: Update, context: CallbackContext) -> None:
    cluster = MongoClient("mongodb://datacaker:27017", connect=True)
    db = cluster.get_database("mooncaker")
    rediti = db.get_collection("ReDiTi")
    elems = rediti.find({}, {'_id': 0})
    with open('rediti.txt', 'a') as res:
        for elem in elems:
            res.write(str(elem) + "\n")
    with open('rediti.txt', 'r') as out:
        context.bot.send_document(chat_id=update.effective_chat.id, document=out,
                                  filename="rediti.txt")
    remove('rediti.txt')


def get_count(update: Update, context: CallbackContext) -> None:
    cluster = MongoClient("mongodb://datacaker:27017", connect=True)
    db = cluster.get_database("mooncaker")
    m = db.get_collection("matches")
    update.message.reply_text(str(m.count_documents({})))


def canc_key_wait(update: Update, context: CallbackContext):
    update.message.reply_sticker(NAME_TO_STICKER[MEGUMIN_THUMB_UP])
    update.message.reply_text(f'Okidoki! Not waiting for key anymore!')
    return ConversationHandler.END


# TODO move get_count etc to dataCrawler
def start_bot(token, set_api, log_name, whitelist) -> None:
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # on different commands - answer in Telegram
    part_auth_dispatch = partial(authorize_and_dispatch, whitelist= whitelist)
    part = partial(part_auth_dispatch, dispatcher=start)
    dispatcher.add_handler(CommandHandler("start", part))
    part = partial(part_auth_dispatch, dispatcher=help_command)
    dispatcher.add_handler(CommandHandler("help", part))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    part_last_10 = partial(get_log, log_filename=log_name, lines=10)
    part = partial(part_auth_dispatch, dispatcher=part_last_10)
    dispatcher.add_handler(CommandHandler("get_last_10_log", part))
    part_log = partial(get_log, log_filename=log_name)
    part = partial(part_auth_dispatch, dispatcher=part_log)
    dispatcher.add_handler(CommandHandler("get_full_log", part))
    part = partial(part_auth_dispatch, dispatcher=set_api_key_req)
    partial_set_api = partial(set_new_api, set_api=set_api)
    part_set = partial(part_auth_dispatch, dispatcher=partial_set_api)
    set_key_handler = ConversationHandler(entry_points=[CommandHandler('set_api_key', part)],
                                          states={
                                              WAITING_API: [
                                                  MessageHandler(Filters.text & ~Filters.command, part_set)
                                              ]
                                          },
                                          fallbacks=[CommandHandler('cancel', canc_key_wait)])
    dispatcher.add_handler(set_key_handler)
    part = partial(part_auth_dispatch, dispatcher=get_ReDiTi)
    dispatcher.add_handler(CommandHandler("get_ReDiTi", part))
    part = partial(part_auth_dispatch, dispatcher=get_count)
    dispatcher.add_handler(CommandHandler("get_count", part))
    updater.start_polling()
    updater.idle()


def main():
    pass


if __name__ == '__main__':
    main()
