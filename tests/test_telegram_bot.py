import datetime

import pytest
from mooncaker.external_tools.mooncaker_bot import MooncakerBot
from multiprocessing import Queue
from telegram.ext import CallbackContext, Dispatcher
from telegram import Update, User, Message, Chat
import telegram


@pytest.fixture()
def bot():
    return MooncakerBot('not_a_token', None, 'not_a_path', 'not_a_whitelist')


def mock_dispatcher(update, context):
    return 1


@pytest.fixture()
def dispatcher():
    return mock_dispatcher


@pytest.fixture()
def mock_reply_sticker(monkeypatch):
    monkeypatch.setattr(Message, "reply_sticker", lambda *_: 1)


@pytest.fixture()
def mock_reply_text(monkeypatch):
    monkeypatch.setattr(Message, "reply_text", lambda *_: 1)


# test users whitelisting
class TestWhitelisting:
    whitelist = 'auth_user_1 auth_user_2'
    user = User(0, 'user_first_name', False, 'user_surname', 'not_an_username')
    message = Message(0, datetime.datetime.now(), Chat(0, 'private'), user)

    def test_not_authorized(self, bot, dispatcher, mock_reply_sticker, mock_reply_text):
        self.message.from_user.__setattr__('username', 'not_auth_user')
        update = Update(0, self.message)
        assert (bot.authorize_and_dispatch(update, None, dispatcher,
                                           self.whitelist) is None and not self.message.from_user.username in self.whitelist)

    def test_authorized_1(self, bot, mock_reply_sticker, mock_reply_text, dispatcher):
        self.message.from_user.__setattr__('username', 'auth_user_1')
        update = Update(0, self.message)
        assert (not bot.authorize_and_dispatch(update, None, dispatcher,
                                               self.whitelist) is None and self.message.from_user.username in self.whitelist)

    def test_authorized_2(self, bot, mock_reply_sticker, mock_reply_text, dispatcher):
        self.message.from_user.__setattr__('username', 'auth_user_2')
        update = Update(0, self.message)
        assert (not bot.authorize_and_dispatch(update, None, dispatcher,
                                               self.whitelist) is None and self.message.from_user.username in self.whitelist)


# test new api_key insertion
class TestApiKeySet:
    api_queue = Queue()
    message = Message(0, datetime.datetime.now(), Chat(0, 'private'))
    update = Update(0, message)

    def test_wrong_length(self, bot, mock_reply_sticker, mock_reply_text):
        self.update.message.__setattr__('text', 'abcdIAmNotAValidKey')
        len_before = self.api_queue.qsize()
        bot.set_new_api(self.update, None, self.api_queue.put)
        len_after = self.api_queue.qsize()
        assert (len_after == len_before)

    def test_not_alphanum_dash_ley(self, bot, mock_reply_sticker, mock_reply_text):
        self.update.message.__setattr__('text', 'aaaaaaaaaaaaaaaaaaaa.aaaaaaaaaaaaaaaaaa.aa')
        len_before = self.api_queue.qsize()
        bot.set_new_api(self.update, None, self.api_queue.put)
        len_after = self.api_queue.qsize()
        assert (len_after == len_before)

    def test_valid_key(self, bot, mock_reply_sticker, mock_reply_text):
        self.update.message.__setattr__('text', 'aaaaaaa-aaaaaaaa-aaaaaaaaaaa-aaaaaaaaaa-aa')
        len_before = self.api_queue.qsize()
        bot.set_new_api(self.update, None, self.api_queue.put)
        len_after = self.api_queue.qsize()
        assert (len_after == len_before + 1)