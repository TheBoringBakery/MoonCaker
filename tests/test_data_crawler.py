import time
import pytest
import random
from mooncaker.external_tools.data_crawler import Crawler
from mooncaker.external_tools.db_interactor import Database
from riotwatcher._apis.league_of_legends import LeagueApiV4
from riotwatcher._apis.league_of_legends import MatchApiV5
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
    succ_list = [{'summonerName': 'mockName1'},
                 {'summonerName': 'mockName2'}]

    @pytest.fixture()
    def mock_entries_succ(self, monkeypatch):
        monkeypatch.setattr(LeagueApiV4, "entries", lambda *_: self.succ_list)

    def test_entries_succ(self, crawler, mock_entries_succ):
        names = crawler.summoner_names('region', 'tier', 'division', 1)
        for summoner in self.succ_list:
            assert summoner['summonerName'] in names

    # check on empty response
    @pytest.fixture()
    def mock_entries_empty(self, monkeypatch):
        monkeypatch.setattr(LeagueApiV4, "entries", lambda *_: [])

    def test_entries_empty(self, crawler, mock_entries_empty):
        names = crawler.summoner_names('region', 'tier', 'division', 1)
        assert names is None

    # check on http error codes
    def test_entries_generic_http_error(self, crawler, mock_entries_generic_http_error):
        names = crawler.summoner_names('region', 'tier', 'division', 1)
        assert names is None

    def test_entries_key_error(self, crawler, mock_entries_403_error):
        old_counter = key_request_counter
        names = crawler.summoner_names('region', 'tier', 'division', 1)
        assert names is None
        assert key_request_counter - old_counter > 0

    def test_entries_timeout_error(self, crawler, mock_entries_429_error, mock_sleep):
        old_counter = sleep_called_counter
        names = crawler.summoner_names('region', 'tier', 'division', 1)
        assert names is None
        assert sleep_called_counter - old_counter > 0


class TestPuuidIdBySumName:
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
        puuids = crawler.puuids_by_name('region', ['mockName1', 'mockName2', 'nonExistantName'])
        for user in self.succ_list:
            assert user.get('puuid') in puuids
        assert len(puuids) == 3

    # check on http error codes
    def test_entries_generic_http_error(self, crawler, mock_entries_generic_http_error):
        puuids = crawler.puuids_by_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3

    def test_entries_key_error(self, crawler, mock_entries_403_error):
        old_counter = key_request_counter
        puuids = crawler.puuids_by_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3
        assert key_request_counter - old_counter > 0

    def test_entries_timeout_error(self, crawler, mock_entries_429_error, mock_sleep):
        old_counter = sleep_called_counter
        puuids = crawler.puuids_by_name('region', ['mockName1', 'mockName2', 'mockName3'])
        for puuid in puuids:
            assert puuid is None
        assert len(puuids) == 3
        assert sleep_called_counter - old_counter > 0


class TestClashMatches:
    # check on successful call
    puuid_list = ['aaaaaaaaaaaaaaaa32aaaaaaaaaaaaaaaa',
                  'bbbbbbbbbbbbbbbb32bbbbbbbbbbbbbbbb',
                  None]
    match_list = ['match_id1',
                  'match_id2',
                  'match_id3',
                  'match_id4']
    index = -1

    def get_puuids(self, *_):
        return self.puuid_list

    def get_matches(self, *_):
        random.shuffle(self.match_list)
        return self.match_list

    def get_filtered(self, matches):
        return matches

    @pytest.fixture()
    def mock_entries_succ(self, monkeypatch):
        monkeypatch.setattr(Crawler, "puuids_by_name", self.get_puuids)

    @pytest.fixture()
    def mock_matchlist_succ(self, monkeypatch):
        monkeypatch.setattr(MatchApiV5, "matchlist_by_puuid", self.get_matches)

    @pytest.fixture()
    def mock_matchlist_unsucc(self, monkeypatch):
        monkeypatch.setattr(MatchApiV5, "matchlist_by_puuid", lambda *_: [])

    @pytest.fixture()
    def mock_filter_succ(self, monkeypatch):
        monkeypatch.setattr(Database, "filter_match_duplicates", self.get_filtered)

    def test_entries_succ(self, crawler, mock_entries_succ, mock_matchlist_succ, mock_filter_succ):
        matches = crawler.clash_matches('euw1', ['mockName1', 'mockName2', 'nonExistentName'])
        for match in self.match_list:
            if match is not None:
                assert match in matches
        assert None not in matches
        assert len(matches) == 8

    def test_entries_unsucc(self, crawler, mock_entries_succ, mock_matchlist_unsucc, mock_filter_succ):
        matches = crawler.clash_matches('euw1', ['mockName1', 'mockName2', 'nonExistentName'])
        assert len(matches) == 0

    # check on http error codes
    def test_entries_generic_http_error(self, crawler, mock_entries_succ, mock_entries_generic_http_error):
        matches = crawler.clash_matches('euw1', ['mockName1', 'mockName2', 'nonExistentName'])
        assert len(matches) == 0

    def test_entries_key_error(self, crawler, mock_entries_succ, mock_entries_403_error):
        old_counter = key_request_counter
        matches = crawler.clash_matches('euw1', ['mockName1', 'mockName2', 'nonExistentName'])
        assert len(matches) == 0
        assert key_request_counter - old_counter > 0

    def test_entries_timeout_error(self, crawler, mock_entries_succ, mock_entries_429_error, mock_sleep):
        old_counter = sleep_called_counter
        matches = crawler.clash_matches('euw1', ['mockName1', 'mockName2', 'nonExistentName'])
        assert len(matches) == 0
        assert sleep_called_counter - old_counter > 0


class TestMatchDetails:
    matches = [{'info': {'gameDuration': 1234567,
                'gameVersion': '1.2.3.4', 
                'participants': [{'participantId': 1, 'puuid': 'a'}, {'participantId': 2, 'puuid': 'b'}, {'participantId': 3, 'puuid': 'c'}, {'participantId': 4, 'puuid': 'd'}, {'participantId': 5, 'puuid': 'e'}, {'participantId': 6, 'puuid': 'f'}, {'participantId': 7, 'puuid': 'g'}, {'participantId': 8, 'puuid': 'h'}, {'participantId': 9, 'puuid': 'i'}, {'participantId': 10, 'puuid': 'j'}],
                'teams': [{'teamId': 1, 'win': True, 'bans': [{'championId': 1}, {'championId': 2}, {'championId': 3}, {'championId': 4}, {'championId': 5}]},
                          {'teamId': 2, 'win': False, 'bans': [{'championId': 6}, {'championId': 7}, {'championId': 8}, {'championId': 9}, {'championId': 10}]}]}}
               for _ in range(3)]

    timelines = [{'info': {'frames': [{}, {}, {'ParticipantFrames': {'1': {'position': {'x': 2030, 'y': 12480}, 'minionsKilled': 1}, '2': {'position': {'x': 6215, 'y': 10700}, 'minionsKilled': 2}, '3': {'position': {'x': 7100, 'y': 7100}, 'minionsKilled': 3}, '4': {'position': {'x': 11500, 'y': 2000}, 'minionsKilled': 4}, '5': {'position': {'x': 11110, 'y': 1300}, 'minionsKilled': 5}, '6': {'position': {'x': 2600, 'y': 12700}, 'minionsKilled': 6}, '7': {'position': {'x': 7300, 'y': 5100}, 'minionsKilled': 7}, '8': {'position': {'x': 7900, 'y': 7300}, 'minionsKilled': 8}, '9': {'position': {'x': 12600, 'y': 3000}, 'minionsKilled': 9}, '10': {'position': {'x': 11100, 'y': 2100}, 'minionsKilled': 10}}}]}} 
                 for _ in range(3)]
    
    index = -1

    def match_by_id(self, *_):
        return self.matches[self.index]

    def timeline_by_id(self, *_):
        return self.timelines[self.index]

    @pytest.fixture()
    def mock_entries_succ(self, monkeypatch):
        monkeypatch.setattr(MatchApiV5, "by_id", self.get_puuids)

    @pytest.fixture()
    def mock_matchlist_succ(self, monkeypatch):
        monkeypatch.setattr(MatchApiV5, "timeline_by_match", self.get_matches)

