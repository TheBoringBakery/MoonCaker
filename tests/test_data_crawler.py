import time
import pytest
from mooncaker.external_tools.data_crawler import Crawler
from riotwatcher._apis.league_of_legends import LeagueApiV4
from riotwatcher._apis.league_of_legends import SummonerApiV4
from riotwatcher._apis import BaseApi
from riotwatcher.exceptions import ApiError


key_request_counter = 0
sleep_called_counter = 0


def increase_key_counter(*_):
    global key_request_counter
    key_request_counter += 1
    return "RGAPI-notanapi"


def increase_sleep_counter(*_):
    global sleep_called_counter
    sleep_called_counter += 1


# recycle object
@pytest.fixture()
def crawler():
    return Crawler("RGAPI-notanapi", increase_key_counter, None)


# Used to check http errors
class MockStatusCode:
    def __init__(self, code):
        self.status_code = code


def raise_api_error(response):
    raise ApiError(response=response)


@pytest.fixture(params=[400, 401, 402, 404, 415, 500, 503])
def mock_entries_generic_http_error(monkeypatch, request):
    code = request.param
    monkeypatch.setattr(BaseApi, "raw_request",
                        lambda *_:
                            raise_api_error(MockStatusCode(code)))


@pytest.fixture
def mock_entries_403_error(monkeypatch):
    monkeypatch.setattr(BaseApi, "raw_request",
                        lambda *_:
                            raise_api_error(MockStatusCode(403)))


@pytest.fixture
def mock_entries_429_error(monkeypatch):
    monkeypatch.setattr(BaseApi, "raw_request",
                        lambda *_:
                            raise_api_error(MockStatusCode(429)))


@pytest.fixture
def mock_sleep(monkeypatch):
    monkeypatch.setattr(time, "sleep", increase_sleep_counter)


# test summoner names function
class TestSummonerNames:
    # check on successful call
    succ_list = [{'summonerName': 'mockName1', 'summonerId': 0},
                 {'summonerName': 'mockName2', 'summonerId': 1}]

    @pytest.fixture()
    def mock_entries_succ(self, monkeypatch):
        monkeypatch.setattr(LeagueApiV4, "entries", lambda *_: self.succ_list)

    def test_entries_succ(self, crawler, mock_entries_succ):
        names, ids = crawler.summoner_names('region', 'tier', 'division', 1)
        for summoner in self.succ_list:
            assert summoner['summonerName'] in names
            assert summoner['summonerId'] in ids

    # check on empty response
    @pytest.fixture()
    def mock_entries_empty(self, monkeypatch):
        monkeypatch.setattr(LeagueApiV4, "entries", lambda *_: [])

    def test_entries_empty(self, crawler, mock_entries_empty):
        names, ids = crawler.summoner_names('region', 'tier', 'division', 1)
        assert not names
        assert not ids

    # check on http error codes
    def test_entries_generic_http_error(self, crawler, mock_entries_generic_http_error):
        names, ids = crawler.summoner_names('region', 'tier', 'division', 1)
        assert names is None
        assert ids is None

    def test_entries_key_error(self, crawler, mock_entries_403_error):
        old_counter = key_request_counter
        names, ids = crawler.summoner_names('region', 'tier', 'division', 1)
        assert names is None
        assert ids is None
        assert key_request_counter - old_counter > 0

    def test_entries_timeout_error(self, crawler, mock_entries_429_error, mock_sleep):
        old_counter = sleep_called_counter
        names, ids = crawler.summoner_names('region', 'tier', 'division', 1)
        assert names is None
        assert ids is None
        assert sleep_called_counter - old_counter > 0


class TestAccIdBySumName:
    # check on successful call
    succ_list = [{'puuid': 'aaaaaaaaaaaaaaaa32aaaaaaaaaaaaaaaa'},
                 {'puuid': 'bbbbbbbbbbbbbbbb32bbbbbbbbbbbbbbbb'},
                 {}]
    index = -1

    def get_puuid(self, *_):
        self.index += 1
        return self.succ_list[self.index]

    @pytest.fixture()
    def mock_entries_succ(self, monkeypatch):
        monkeypatch.setattr(SummonerApiV4, "by_name", self.get_puuid)

    def test_entries_succ(self, crawler, mock_entries_succ):
        puuids = crawler.acc_id_by_sum_name('region', ['mockName1', 'mockName2', 'nonExistantName'])
        for user in self.succ_list:
            assert user.get('puuid') in puuids
        assert len(puuids) == 3

    # check on http error codes
    def test_entries_generic_http_error(self, crawler, mock_entries_generic_http_error):
        puuids = crawler.acc_id_by_sum_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3

    def test_entries_key_error(self, crawler, mock_entries_403_error):
        old_counter = key_request_counter
        puuids = crawler.acc_id_by_sum_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3
        assert key_request_counter - old_counter > 0

    def test_entries_timeout_error(self, crawler, mock_entries_429_error, mock_sleep):
        old_counter = sleep_called_counter
        puuids = crawler.acc_id_by_sum_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3
        assert sleep_called_counter - old_counter > 0


class TestClashMatches:
    # check on successful call
    succ_list = [{'puuid': 'aaaaaaaaaaaaaaaa32aaaaaaaaaaaaaaaa'},
                 {'puuid': 'bbbbbbbbbbbbbbbb32bbbbbbbbbbbbbbbb'},
                 {}]
    index = -1

    def get_puuid(self, *_):
        self.index += 1
        return self.succ_list[self.index]

    @pytest.fixture()
    def mock_entries_succ(self, monkeypatch):
        monkeypatch.setattr(SummonerApiV4, "by_name", self.get_puuid)

    def test_entries_succ(self, crawler, mock_entries_succ):
        puuids = crawler.acc_id_by_sum_name('region', ['mockName1', 'mockName2', 'nonExistantName'])
        for user in self.succ_list:
            assert user.get('puuid') in puuids
        assert len(puuids) == 3

    # check on http error codes
    def test_entries_generic_http_error(self, crawler, mock_entries_generic_http_error):
        puuids = crawler.acc_id_by_sum_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3

    def test_entries_key_error(self, crawler, mock_entries_403_error):
        old_counter = key_request_counter
        puuids = crawler.acc_id_by_sum_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3
        assert key_request_counter - old_counter > 0

    def test_entries_timeout_error(self, crawler, mock_entries_429_error, mock_sleep):
        old_counter = sleep_called_counter
        puuids = crawler.acc_id_by_sum_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3
        assert sleep_called_counter - old_counter > 0
