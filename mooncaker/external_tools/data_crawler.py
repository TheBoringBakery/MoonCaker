"""
    Crawls lol data with the APi and stores it in a database
"""

import re
import time
from functools import partial
from logging import INFO, DEBUG, WARNING
from riotwatcher import LolWatcher, ApiError
from . import REGION2BIG_REGION
from .db_interactor import Database
from .logger import log as log_raw


log = partial(log_raw, "datacrawler")
# todo: add conccurent requests where possible to speed things up


class Crawler():

    def __init__(self,
                 API_KEY,
                 get_key_blocking,
                 db_url):

        self.db = Database(db_url)
        self.watcher = LolWatcher(API_KEY, default_match_v5=True)
        self.get_new_key = get_key_blocking

    def safe_api_call(self, attributes, args, retry_count=3):
        """calls the given command and checks for the successful outcome
        If the outcome is not successful, it intercepts the error and based on
        that will either retry (up to 3 times) or return unsuccessful status

        Args:
            attributes (list(str)): a list string with the names of the attributes of the api to exec
            args (tuple): the arguments to pass to the function
            redo_count (int, optional): used internally to count how many times
                                        the call has been retried.
                                        Defaults to 3.

        Returns:
            (bool, Any | None): the outcome of the operation and the result, None if it was unsuccessful
        """
        log(INFO, f"Calling {attributes} with args: {args}")
        result = None
        call_is_successful = False
        if retry_count > 0:
            # redo call in case of errors up to x times
            try:
                command = getattr(self.watcher, attributes[0])
                for attribute in attributes[1:]:
                    command = getattr(command, attribute)
                result = command(*args)
                call_is_successful = True
            except ApiError as err:
                if err.response.status_code == 403:
                    log(WARNING, "Received a 403 status code, waiting new API")
                    log(DEBUG, "Going to possibly hang while waiting new api key")
                    new_key = self.get_new_key()
                    self.watcher = LolWatcher(new_key, default_match_v5=True)
                    log(DEBUG, f"Received new api key ending with {new_key[-5:]}")
                elif err.response.status_code == 404:
                    log(WARNING, "Received a 404 status code with the following arguments: ")
                    log(WARNING, f"{args}")
                    log(WARNING, f"While calling {attributes}")
                elif err.response.status_code == 429:
                    sleep_time = err.response.headers.get("Retry-After")
                    sleep_time = 60 * (4 - retry_count) if sleep_time is None else int(sleep_time)
                    log(WARNING, f"Received a 429 status code, too many same type requests, sleeping for {sleep_time}")
                    log(WARNING, f"The request was: {attributes}")
                    time.sleep(sleep_time)
                else:
                    log(WARNING, f"Received a {err.response.status_code} status code with the following arguments:")
                    log(WARNING, f"{args}")
                    log(WARNING, f"While calling {attributes}")
            if not call_is_successful:
                return self.safe_api_call(attributes, args, retry_count - 1)
        return call_is_successful, result

    def puuids_by_name(self, region, summoner_names):
        """
            Fetch PUUIDs for each summoner name and returns them as a list

            Parameters:
            region(String): the server region to which the accounts belong
            summoner_names(List[String]): list of summoner names to search PUUID for

            Returns:
            List[String]: list of PUUIDs associated to input summoner names,
                          containing None if no PUUID was found for the summoner name
        """
        ids = []
        for name in summoner_names:
            # todo: check when 404 maybe name has changed
            is_successful, user = self.safe_api_call(["summoner", "by_name"],
                                                     (region, name))
            if is_successful:
                ids.append(user.get('puuid'))
            else:
                ids.append(None)
        return ids

    def clash_matches(self, region, names):
        """
        From summoner names gets their puuid, their match list,
        then returns only the clash matches of the given players.

        Args:
            region (str): the server region to which the accounts belong (euw1, eune1, ...)
            names (list(str)): list of summoner names to crawl

        Returns:
            list(str): list of strings with the clash match ids as string
        """
        # retrieve accounts puuids
        puuids = self.puuids_by_name(region, names)
        puuids = list(filter(None, puuids))
        match_list = []
        big_region = REGION2BIG_REGION[region]
        for puuid in puuids:
            is_successful, matches = self.safe_api_call(['match', "matchlist_by_puuid"],
                                                        (big_region,
                                                         puuid,
                                                         700,
                                                         None,
                                                         0,
                                                         100))
            if is_successful:
                for match in matches:
                    match_list.append(match)

        match_list = list(filter(None, match_list))  # todo: might not be needed anymore
        return self.db.filter_match_duplicates(match_list)

    def summoner_names(self, region, tier, division, page, mode='RANKED_SOLO_5x5'):
        """
            Fetch all the summoner names in a tier and division

            Parameters:
            region(String): a server region
            mode(String): type of queue
            tier(String): tier of the queue
            division(String): division of the queue

            Returns:
                List(str): list of players' summoner name or None if call is unsuccessful
        """
        is_successful, players_list = self.safe_api_call(['league', 'entries'],
                                                         (region,
                                                          mode,
                                                          tier,
                                                          division,
                                                          page))
        if is_successful:
            names = [summoner.get('summonerName') for summoner in players_list]
            return list(filter(lambda x: bool(x.strip()), names))  # filter empty names
        return None

    @staticmethod
    def is_jungler(player):
        spells = [player["summoner1Id"], player["summoner2Id"]]
        return 11 in spells  # 11 is smite #todo (low): remove hardcoded value

    @staticmethod
    def get_role(pos, player):
        if Crawler.is_jungler(player):
            return "JUNGLE"
        x = pos["x"]
        y = pos["y"]
        if x > 3500 and y < 3500 or x > 11000 and y < 11000:  # todo (very low): can remove the hardcoded values?
            return "BOT"
        if x < 3500 and y > 3500 or x < 11000 and y > 11000:
            return "TOP"
        return "MID"

    @staticmethod
    def check_bot_roles(botlane, frame):
        farm = [frame[str(player["id"])]['minionsKilled'] for player in botlane]
        support = 0 if farm[0] < farm[1] else 1  # todo: what about senna?
        adc = 0 if support == 1 else 1
        return {"SUPPORT": {"summonerId": botlane[support]['summonerId'],
                            "champion": botlane[support]['champion']},
                "ADC": {"summonerId": botlane[adc]['summonerId'], 
                        "champion": botlane[adc]['champion']}}

    def match_details(self, match_list, region):
        """
            Fetch details of matches and store them into docs

        Parameters:
            match_lists(List[Integer]): List of clash games ids
            region(String): a server region

        Returns:
            list: list of docs containing the specs of each match excluding invalid ones.
                  each doc is a dictionary with the following items:
                    'teamId': int
                    'bans': list(int)
                    '<role>': dict('summonerId': int, 'champion': int) 
                              for each <role> in ADC, SUPPORT, MID, JUNGLE, TOP
        """
        big_region = REGION2BIG_REGION[region]
        match_docs = []
        for g_id in match_list:

            # get match by id
            is_successful, match = self.safe_api_call(['match', 'by_id'],
                                                      (big_region,
                                                       g_id))
            if not is_successful:
                continue  # unlucky

            # get timeline to enstablish roles
            is_successful, timeline = self.safe_api_call(['match', 'timeline_by_match'],
                                                         (big_region,
                                                          g_id))
            if not is_successful:
                continue  # unlucky part2

            m2_frame = timeline['info']['frames'][2]['participantFrames']
            m_last_frame = timeline['info']['frames'][-1]['participantFrames']
            m2_pos = {int(num): m2_frame[num]['position'] for num in m2_frame.keys()}
            new_doc = {"_id": g_id, "region": region, "duration": match['info']["gameDuration"],
                       "patch": re.search(r'^\d+[.]\d+', match['info']["gameVersion"]).group()}
            teams = [team["teamId"] for team in match['info']["teams"]]
            new_doc["winner"] = teams[0] if match['info']["teams"][0]["win"] is True else teams[1]
            i = 0
            bans = [[], []]
            for team in match['info']["teams"]:
                for ban in team["bans"]:
                    bans[i].append(ban["championId"])
                i += 1
            teams = ({"teamId": teams[0], "bans": bans[0]}, {"teamId": teams[1], "bans": bans[0]})
            identities = {part["participantId"]: part["puuid"] for part in
                          match['info']["participants"]}
            bot = [[], []]
            for player in match['info']["participants"]:
                team = 0 if player["teamId"] == teams[0]["teamId"] else 1
                role = Crawler.get_role(m2_pos[player["participantId"]], player)
                champion = player["championId"]
                sum_id = identities[player["participantId"]]
                if role != "BOT":
                    teams[team][role] = {"summonerId": sum_id, "champion": champion}
                else:
                    bot[team].append({"summonerId": sum_id,
                                      "champion": champion,
                                      "id": player["participantId"]})
            if len(bot[0]) == 2 and len(bot[1]) == 2 and len(teams[0]) == 5 and len(teams[1]) == 5:
                for team in range(2):
                    bot_roles = Crawler.check_bot_roles(bot[team], m_last_frame)
                    teams[team]["SUPPORT"] = bot_roles["SUPPORT"]
                    teams[team]["ADC"] = bot_roles["ADC"]
                new_doc["team1"] = teams[0]
                new_doc["team2"] = teams[1]
                match_docs.append(new_doc)
        return match_docs

    def start_crawling(self):
        for id, region, tier, division, page in self.db.ranks2crawl():
            is_last_page = False
            while not is_last_page:
                log(INFO, f"Crawling {region}, {tier}, {division}, {page}")
                names = self.summoner_names(region, tier, division, page)
                if names is None:
                    # call is unsuccessful
                    log(WARNING, f"Call to look up summoner names for {region}, {tier}, {division}, {page} was unsuccessful")
                    break
                elif len(names) == 0:
                    # No names on that page
                    log(INFO, f"Crawled last page for {region}, {tier}, {division}, {page}")
                    is_last_page = True
                else:
                    page += 1

                    # retrieve matches by batches of summoner names
                    batch_size = 100
                    for index in range(0, len(names), batch_size):
                        batch_names = names[index: min(index+batch_size, len(names))]
                        match_list = self.clash_matches(region,
                                                        batch_names)
                        match_docs = self.match_details(match_list, region)
                        if match_docs:
                            self.db.insert_match_page(id, match_docs, page)
            if is_last_page:
                self.db.mark_as_crawled(id)
        log(INFO, 'Finished crawling, resetting rediti and starting again')
        self.db.reset_rediti()
