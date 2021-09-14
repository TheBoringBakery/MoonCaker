from functools import partial
from os import getcwd, path, remove
import os
import requests
from telegram import Update, ForceReply, Sticker, InlineKeyboardButton, \
    InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, \
    CallbackContext, CallbackQueryHandler, ConversationHandler
from mooncaker.external_tools.logger import get_log
from mooncaker.external_tools.db_interactor import Database


class MooncakerBot:
    SAD_ZOE = 'CAACAgIAAxkBAAECkWNg7Fo-k6squNhgN_2bLL2X3F6DhQACWwADsiFfFVNQKDUCqm9IIAQ'
    MEGUMIN_THUMB_UP = 'CAACAgUAAxkBAAECkXNg7GRAgV-Bw0QddeuTXXLcS_WV7gACnBwAAsZRxhXGsrj-QloNWyAE'
    PARTY_GIRL = 'CAACAgUAAxkBAAECkXFg7GNN3M6hwcJb21P74JELHq0mHQACpxwAAsZRxhXfhZz2U_6oByAE'
    LOLI = 'CAACAgUAAxkBAAECjRVg5uYDQV50eYErYbW-52OzbJ9eWgACkh4AAsZRxhWMjlg7SAq03yAE'
    NAME_TO_STICKER = {name: Sticker(name, name, 512, 512, False) for name in
                       [SAD_ZOE, MEGUMIN_THUMB_UP, PARTY_GIRL, LOLI]}

    def __init__(self, token, set_api, whitelist, db_url, reminder_chat_id, client_user):
        """
            Initializes the bot, stores the telegram token, connects to the
            database and saves the url of the log and
            the function to call when setting a new api_key
        """
        self.db = Database(db_url)
        self.token = token
        self.set_api = set_api
        self.whitelist = whitelist
        self.WAITING_API = 0
        self.WAITING_NUM_LINES = 0
        self.reminder_chat_id = reminder_chat_id
        self.client_user = client_user

    def send_new_api_reminder(self) -> None:
        """
            sends to admins a reminder for the insertion of a new api key

            Args:
                chat_id: telegram chat id of the admin to which the message
                         should be sent
        """
        params = {
            'chat_id': self.reminder_chat_id,
            'text': 'Senpai, I need a new api key :('
        }
        url = "https://api.telegram.org/bot" + self.token + "/sendMessage"
        requests.get(url, params=params)

    def authorize_and_dispatch(self, update: Update, context: CallbackContext, dispatcher):
        """
            Authorizes a user to access functionalities by checking its
            username in the stored whitelist, if the user is
            authorized the passed dispatcher is called to handle the request
        """
        if update.effective_user.username in self.whitelist.split():
            return dispatcher(update=update, context=context)
        else:
            update.message.reply_sticker(self.NAME_TO_STICKER[self.SAD_ZOE])
            update.message.reply_text("Sorry, you cannot do that")

    def start(self, update: Update, context: CallbackContext) -> None:
        """Dispatcher for the command /start."""
        print(update.effective_chat.id)
        user = update.effective_user
        update.message.reply_sticker(self.NAME_TO_STICKER[self.LOLI])
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

    def button(self, update: Update, context: CallbackContext) -> None:
        """Parses the CallbackQuery and updates the message text."""
        query = update.callback_query
        query.answer()
        if query.data == '1':
            query.edit_message_text(
                text=f"Available commands: \n /get_log \n /set_api_key \n /get_ReDiTi \n "
                     f"/get_count \n /get_csv")
        else:
            query.edit_message_text(text=f"You are the best, onii-chan! I will always support you!")

    def send_log(self, update: Update, context: CallbackContext, n_lines=0):
        """
        Dispatcher for the commands which have to retrieve the log. Retrieves the whole log if the argument lines is
        None, otherwise it returns the last n_lines lines of the log.
        """
        log = get_log()
        n_lines = int(update.message.text) if update.message.text.isnumeric() else 0
        with open("tmp.txt", "a") as log2send:
            log2send.writelines(log[-n_lines:])
        with open("tmp.txt", "r") as log2send:
            context.bot.send_document(chat_id=update.effective_chat.id,
                                      document=log2send,
                                      filename="mooncaker.log")
        os.system('rm tmp.txt')
        return ConversationHandler.END

    def get_csv(self, update: Update, context: CallbackContext):
        """
        Generates and sends csv file for matches collection. Since telegram bots are limited to sending at most 
        50 MB files, the file is first sent by a Client (not bot instance) of Telegram to the bot, then sent by 
        their file_id in the Telegram server to the requiring user, except the case of the requiring user being
        the user which is used for the Client instance. 
        """
        matches_filename = self.db.create_matches_csv()
        os.system(f'telegram-upload --to Mooncaker_bot --print-file-id "{matches_filename}" > tmp.txt')
        with open('tmp.txt') as tmp:
            tmp_file = tmp.read()
            file_id = tmp_file.split("file_id ", 1)[1].strip().replace(')', '')
        os.system('rm tmp.txt')
        if update.effective_user != self.client_user:
            context.bot.send_document(chat_id=update.effective_chat.id, document=file_id)

    def set_api_key_req(self, update: Update, context: CallbackContext) -> int:
        """
        Replies to the user wanting to set a new api key. By returning WAITING_API the set-api-key-dispatcher state
        machine transitions and waits for the next message which should be the new api key.
        """
        update.message.reply_text("Please gimme all your new API key, I want it so bad..or use /cancel to make me stop waiting..")
        return self.WAITING_API

    def set_new_api(self, update: Update, context: CallbackContext):
        """
        Checks the correct format of the given api key and then sets the new api key to the user-given one. Upon
        returning, the set-api-key-dispatcher state machine terminate if the insertion was successful and loops back
        to the same state otherwise.
        """
        new_api = ''.join([c for c in update.message.text if c.isalnum() or c in ['-']])
        if len(new_api) != 42:
            update.message.reply_sticker(self.NAME_TO_STICKER[self.SAD_ZOE])
            update.message.reply_text('Why r u tryin to troll me, insert a valid key baka')
            return self.WAITING_API
        self.set_api(new_api)
        update.message.reply_sticker(self.NAME_TO_STICKER[self.PARTY_GIRL])
        update.message.reply_text("New API key set! Hurray!")
        return ConversationHandler.END

    def get_ReDiTi(self, update: Update, context: CallbackContext) -> None:
        """
        Retrieves from the database the collection of crawled regions, divisions, tiers and sends it to the user in
        textual format.
        """
        elems = self.db.get_rediti()
        with open('rediti.txt', 'a') as res:
            for elem in elems:
                res.write(str(elem) + "\n")
        with open('rediti.txt', 'r') as out:
            context.bot.send_document(chat_id=update.effective_chat.id, document=out,
                                      filename="rediti.txt")
        remove('rediti.txt')

    def get_count(self, update: Update, context: CallbackContext) -> None:
        """
        Retrieves from the database the number of crawled matches and sends it to the user.
        """
        update.message.reply_text(str(self.db.count_matches()))

    def canc_wait(self, update: Update, context: CallbackContext):
        """
        Makes the set-api-key-dispatcher state machine stop waiting for an api key, terminating the state machine.
        """
        update.message.reply_sticker(self.NAME_TO_STICKER[self.MEGUMIN_THUMB_UP])
        update.message.reply_text(f'Okidoki! Not waiting anymore!')
        return ConversationHandler.END

    def ask_log_num(self, update: Update, context: CallbackContext):
        """
        Send a message asking to insert the desired number of lines wanted for the log
        """
        update.message.reply_text(f'How many lines of log would you like to have, senpai? Use /cancel to make me stop waiting')
        return self.WAITING_NUM_LINES

    def start_bot(self) -> None:
        """
        Starts the bot, creating the updater and adding the dispatchers for the available commands.
        """
        updater = Updater(self.token)
        dispatcher = updater.dispatcher
        part = partial(self.authorize_and_dispatch, dispatcher=self.start)
        dispatcher.add_handler(CommandHandler("start", part))
        updater.dispatcher.add_handler(CallbackQueryHandler(self.button))
        part_last_10 = partial(self.send_log, n_lines=10)
        part = partial(self.authorize_and_dispatch, dispatcher=part_last_10)
        dispatcher.add_handler(CommandHandler("get_last_10_log", part))
        part = partial(self.authorize_and_dispatch, dispatcher=self.send_log)
        dispatcher.add_handler(CommandHandler("get_full_log", part))
        part = partial(self.authorize_and_dispatch, dispatcher=self.set_api_key_req)
        part_set = partial(self.authorize_and_dispatch, dispatcher=self.set_new_api)
        set_key_handler = ConversationHandler(entry_points=[CommandHandler('set_api_key', part)],
                                              states={
                                                  self.WAITING_API: [
                                                      MessageHandler(Filters.text & ~Filters.command, part_set)
                                                  ]
                                              },
                                              fallbacks=[CommandHandler('cancel', self.canc_wait)])
        dispatcher.add_handler(set_key_handler)
        part = partial(self.authorize_and_dispatch, dispatcher=self.ask_log_num)
        part_log = partial(self.authorize_and_dispatch, dispatcher=self.send_log)
        get_log_handler = ConversationHandler(entry_points=[CommandHandler('get_log', part)],
                                              states={
                                                  self.WAITING_NUM_LINES: [
                                                      MessageHandler(Filters.text & ~Filters.command, part_log)
                                                  ]
                                              },
                                              fallbacks=[CommandHandler('cancel', self.canc_wait)])
        dispatcher.add_handler(get_log_handler)
        part = partial(self.authorize_and_dispatch, dispatcher=self.get_csv)
        dispatcher.add_handler(CommandHandler("get_csv", part))

        part = partial(self.authorize_and_dispatch, dispatcher=self.get_ReDiTi)
        dispatcher.add_handler(CommandHandler("get_ReDiTi", part))
        part = partial(self.authorize_and_dispatch, dispatcher=self.get_count)
        dispatcher.add_handler(CommandHandler("get_count", part))
        updater.start_polling()
        updater.idle()