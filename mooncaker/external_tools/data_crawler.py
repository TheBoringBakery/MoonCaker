"""
    Crawls lol data with the APi and stores it in a database
"""

from functools import partial
import argparse
import re
import time
import logging
from riotwatcher import LolWatcher, ApiError
from external_tools import REGION2BIG_REGION
from external_tools.db_interactor import Database

# todo: add conccurent requests were possible to speed things up


class Crawler():

    def __init__(self,
                 API_KEY,
                 get_key_blocking,
                 db_url="mongodb://datacaker:27017"):

        self.db = Database(db_url)
        self.watcher = LolWatcher(API_KEY, default_match_v5=True)
        self.get_new_key = get_key_blocking

    def safe_api_call(self, command, retry_count=3):
        """calls the given command and checks for the successful outcome
        If the outcome is not successful, it intercepts the error and based on
        that will either retry (up to 3 times) or return unsuccessful status

        Args:
            command (fun): a callable of the api to exec which was already
                           given the arguments needed (use partial)
            redo_count (int, optional): used internally to count how many times
                                        the call has been retried.
                                        Defaults to 3.

        Returns:
            (bool, Any | None): the outcome of the operation and the result, None if it was unsuccessful
        """
        result = None
        call_is_successful = False
        if retry_count > 0:
            # redo call in case of errors up to x times
            try:
                result = command()
                call_is_successful = True
            except ApiError as err:
                if err.response.status_code == 404:
                    logging.warning(f"datacrawler: Received a 404 status code with the following arguments")
                elif err.response.status_code == 403:
                    logging.warning(f"datacrawler: Received a 403 status code, waiting new API")
                    logging.debug("datacrawler: going to possibly hang while waiting new api key")
                    new_key = self.get_new_key()
                    self.watcher = LolWatcher(new_key, default_match_v5=True)
                    logging.debug(f"datacrawler: received new api key ending with {new_key[-5:]}")  # todo: is it bad to hang inside except?
                elif err.response.status_code == 429:
                    # todo: how many is too many ?
                    logging.warning("datacrawler: Received a 429 status code, too many same type requests, sleeping for 60s")
                    time.sleep(60)
                else:
                    logging.warning(f"datacrawler: Received a {err.response.status_code} status code")
            if not call_is_successful:
                return self.safe_api_call(command, retry_count - 1)
        return call_is_successful, result

    # gets account Ids of given summoners, returning None for accounts not found (che cazzo ne so anche se li ho appena fetchati dalla lega non li trova)
    def acc_id_by_sum_name(self, region, summoner_names):
        """
            Fetch accountIds for each summoner name and returns them as a list

            Parameters:
            region(String): the server region to which the accounts belong
            summoner_names(List[String]): list of summoner names to search accountIds for

            Returns:
            List[String]: list of accountIds associated to input summoner names, containing None if no accountId was found for the summoner name
        """
        ids = []
        for name in summoner_names:
            command2call = partial(self.watcher.summoner.by_name, region, name)
            # todo: check when 404 maybe name has changed
            is_successful, user = self.safe_api_call(command2call)
            if is_successful:
                ids.append(user.get('puuid'))
            # else:
            #     ids.append(None) # todo: why is this ? - was present in previous version
        return ids

    def clash_matches(self, region, names, sum_ids):
        """
        From summoner names and ids, gets their puuid, their match list,
        then returns only the clash matches of the given players.

        Args:
            region (str): the server region to which the accounts belong (euw1, eune1, ...)
            names (list(str)): list of summoner names to crawl
            sum_ids (list[int]): list of summoner ids respetive to the above name

        Returns:
            list(str): list of strings with the clash match ids as string
        """
        # retrieve accounts puuids
        accounts = []
        acc_ids = self.acc_id_by_sum_name(region, names)
        for i in range(len(acc_ids)):
            if not acc_ids[i] is None:
                accounts.append({'summonerName': names[i], 'summonerId': sum_ids[i], 'puuid': acc_ids[i]})

        # retrieve match list for each account
        puuids = [account.get('puuid') for account in accounts]
        match_list = []
        big_region = REGION2BIG_REGION[region] 
        for encr_puuid in puuids:
            command2call = partial(self.watcher.match.matchlist_by_puuid,
                                   big_region,
                                   encr_puuid,
                                   queue=700,
                                   type=None,
                                   start=0,
                                   count=100)
            is_successful, matches = self.safe_api_call(command2call)
            if is_successful:
                for match in matches:
                    match_list.append(match)

        match_list = list(filter(None, match_list))  # todo: might not be needed anymore
        return self.db.filter_duplicates(match_list)

    # returns list of account infos: summoner name,summoner Id, account Id
    def summoner_names(self, region, tier, division, page, mode='RANKED_SOLO_5x5'):
        """
            Fetch all the summoner names in a tier and division

            Parameters:
            region(String): a server region
            mode(String): type of queue
            tier(String): tier of the queue
            division(String): division of the queue

            Returns:
                List(str), List(str): list of players' summoner name and summonerId belonging to the given tier,division,region
        """
        command2call = partial(self.watcher.league.entries, region, mode, tier, division, page)
        is_successful, players_list = self.safe_api_call(command2call)
        if is_successful and players_list:
            return [summoner.get('summonerName') for summoner in players_list], \
                   [summoner.get('summonerId') for summoner in players_list]
        return None, None

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
        return {"SUPPORT": {"summonerId": botlane[support]['summonerId'], "champion": botlane[support]['champion']},
                "ADC": {"summonerId": botlane[adc]['summonerId'], "champion": botlane[adc]['champion']}}

    def match_details(self, match_list, region):
        """
            Fetch details of matches and store them into docs

        Parameters:
            match_lists(List[Integer]): List of clash games ids
            region(String): a server region

        Returns:
            list: list of docs containing the specs of the matches
        """
        big_region = REGION2BIG_REGION[region]
        match_docs = []
        for g_id in match_list:

            # get match by id
            command2call = partial(self.watcher.match.by_id, big_region, g_id)
            is_successful, match = self.safe_api_call(command2call)
            if not is_successful:
                continue  # unlucky

            # get timeline to enstablish roles
            command2call = partial(self.watcher.match.timeline_by_match, big_region, g_id)
            is_successful, timeline = self.safe_api_call(command2call)
            if not is_successful:
                continue  # unlucky part2

            m2_frame = timeline['info']['frames'][2]['participantFrames']
            m_last_frame = timeline['info']['frames'][-1]['participantFrames']
            m2_pos = {int(num): m2_frame[num]['position'] for num in m2_frame.keys()}
            new_doc = {"_id": g_id, "region": region, "duration": match['info']["gameDuration"],
                       "patch": float(re.search('^\d+[.]\d+', match['info']["gameVersion"]).group())}
            teams = [team["teamId"] for team in match['info']["teams"]]
            new_doc["winner"] = teams[0] if match['info']["teams"][0]["win"] == 'Win' else teams[1]
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
                    bot[team].append({"summonerId": sum_id, "champion": champion, "id": player["participantId"]})
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
                logging.info(f"datacrawler: Crawling {region}, {tier}, {division}, {page}")
                names, sum_ids = self.summoner_names(region, tier, division, page)
                if names is None or sum_ids is None:
                    is_last_page = True
                else:
                    page += 1

                    # retrieve matches by batches of summoner names
                    batch_size = 100
                    for index in range(0, len(names), batch_size):
                        batch_names = names[index: min(index+batch_size, len(names))]
                        match_list = self.clash_matches(region,
                                                        batch_names,
                                                        sum_ids)
                        match_docs = self.match_details(match_list, region)
                        self.db.insert_match_page(id, match_docs, page)
        logging.info('datacrawler: Finished crawling, resetting rediti and starting again')
        self.db.reset_rediti()


def main():
    logging.basicConfig(level=logging.DEBUG)
    # parse arguments in order to get the riot API
    parser = argparse.ArgumentParser(description='Crawls some lol data about clash')
    parser.add_argument('--API-file', help='the filename with the riot API key')
    parser.add_argument('--API', help='the riot API key')
    parser.add_argument('--db-url', help='the url of the mongo db, default is localhost')
    parser.add_argument('--test-api', help='if given it will only test the connection to riot API without the database',
                        action='store_true')
    parser.add_argument('--test-db', help='if given it will only test the database without accessing the api',
                        action='store_true')
    args = vars(parser.parse_args())

    if args['test_db'] is True:
        # todo: test the database
        return

    # Check avilability of API key
    if args['API'] is None and args['API_file'] is None:
        print("You must either provide the API through the command line or through a file")
        parser.print_help()
        return

    RIOT_API_KEY = ""
    if args['API'] is not None:
        RIOT_API_KEY = args['API']
    else:
        RIOT_API_KEY_FILENAME = args['API_file']
        try:
            with open(RIOT_API_KEY_FILENAME) as file:
                RIOT_API_KEY = file.readline()
        except FileNotFoundError:
            print("Couldn't find the specified file with the RIOT API key, please check again")
            return

    if args['test_api'] is True:
        # test only api connection without db
        crawler = Crawler(RIOT_API_KEY, input)
        for id, region, tier, division, page in crawler.db.ranks2crawl():
            logging.info(f"datacrawler: Crawling {region}, {tier}, {division}, {page}")
            names, sum_ids = crawler.summoner_names(region, tier, division, page)

            # retrieve matches by batches of summoner names
            batch_size = 100
            for index in range(0, batch_size+1, batch_size):
                batch_names = names[index: min(index+batch_size, len(names))]
                match_list = crawler.clash_matches(region,
                                                   batch_names,
                                                   sum_ids)
                match_docs = crawler.match_details(match_list, region)
                crawler.db.insert_match_page(id, match_docs, page)
        return

    db_url = "mongodb://localhost:27017" if args['db_url'] is None else args['db_url']

    crawler = Crawler(RIOT_API_KEY, input, db_url)
    crawler.start_crawling()


if __name__ == "__main__":
    main()
