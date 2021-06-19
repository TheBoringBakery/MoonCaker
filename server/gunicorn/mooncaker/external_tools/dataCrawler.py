"""
    Crawls lol data with the APi and stores it in a database
"""

from riotwatcher import LolWatcher, ApiError
from pymongo import MongoClient
from functools import partial
import argparse
import re
import time
import logging


BIG_REGIONS = ['europe', 'americas', 'asia']
REGIONS = ['euw1', 'eun1', 'kr', 'na1']
#league api wants region=euw1,... while matchv5 wants region=europe,... (riot, hello?!)
REGION2BIG_REGION = {'euw1': 'europe', 'eun1': 'europe', 'kr': 'asia', 'na1': 'americas'}
TIERS = ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'IRON']
DIVISIONS = ['I', 'II', 'III', 'IV']

def set_new_key(watcher, new_key):
    logging.debug("datacrawler: going to possibly hang while waiting new api key")
    watcher._base_api._api_key = new_key() #todo: is this even the right way to set the new key?
    logging.debug(f"datacrawler: received new api key ending with {watcher._base_api._api_key[-5:]}")

def safe_api_call(command, wait_set_new_key, retry_count=3):
    """calls the given command and checks for the successful outcome
    If the outcome is not successful, it intercepts the error and based on
    that will either retry (up to 3 times) or return unsuccessful status

    Args:
        command (fun): a callable of the api to exec which was already given the arguments needed (use partial)
        wait_set_new_key (fun): basically the defined set_new_key with the args already given
        redo_count (int, optional): used internally to count how many times the call has been retried. Defaults to 3.

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
                wait_set_new_key() #todo: is it bad to hang inside except?
            elif err.response.status_code == 429:
                #todo: how many is too many ?
                logging.warning("datacrawler: Received a 429 status code, too many same type requests, sleeping for 60s")
                time.sleep(60)
            else:
                logging.warning(f"datacrawler: Received a {err.response.status_code} status code")
        if not call_is_successful:
            return safe_api_call(command, wait_set_new_key, retry_count - 1)
    return call_is_successful, result

def sum_name_id(lw, region, mode, tier, division, get_key):
    """
        Fetch all the summoner names in a tier and division

        Parameters:
        lw (LolWatcher): a LolWatcher instance
        region(String): a server region
        mode(String): type of queue
        tier(String): tier of the queue
        division(String): division of the queue
        get_key(Func): function that returns a new api key

        Returns:
        List[List[String]]: list of players' summoner name and summonerId belonging to the given tier,division,region
    """
    command2call = partial(lw.league.entries, region, mode, tier, division)
    is_successful, players_list = safe_api_call(command2call, get_key)
    if is_successful:
        return [summoner.get('summonerName') for summoner in players_list], \
               [summoner.get('summonerId') for summoner in players_list]
    return None


# gets account Ids of given summoners, returning None for accounts not found (che cazzo ne so anche se li ho appena fetchati dalla lega non li trova)
def acc_id_by_sum_name(lw, region, summoner_names, get_key):
    """
        Fetch accountIds for each summoner name and returns them as a list

        Parameters:
        lw (LolWatcher): a LolWatcher instance
        region(String): the server region to which the accounts belong
        summoner_names(List[String]): list of summoner names to search accountIds for
        get_key(Func): function that returns a new api key

        Returns:
        List[String]: list of accountIds associated to input summoner names, containing None if no accountId was found for the summoner name
    """
    ids = []
    for name in summoner_names[:10]: #todo: what is this slicing for (?!)
        command2call = partial(lw.summoner.by_name, region, name)
        is_successful, user = safe_api_call(command2call, get_key)
        if is_successful:
            ids.append(user.get('puuid'))
        # else:
        #     ids.append(None) #todo: why is this ? - was present in previous version
    return ids


# gets Clash match list for each given accountId, returning None for accounts with no clash games
def clash_matches(lw, region, puuids, get_key):
    """
        Fetch all clash games for the given accounts

        Parameters:
        lw (LolWatcher): a LolWatcher instance
        region(String): the server region to which the accounts belong
        accountIds(List[String]): list of accountIds to search games for
        get_key(Func): function that returns a new api key

        Returns:
        List[List[Dict]]: list containing a list of dictionaries with clash matches info for each accountId
    """
    match_list = []
    big_region = REGION2BIG_REGION[region] 
    for encr_puuid in puuids:
        command2call = partial(lw.matchv5.matchlist_by_puuid, big_region, encr_puuid)
        is_successful, matches = safe_api_call(command2call, get_key)
        if is_successful:
            match_list.append(matches)
    
    match_list = list(filter(None, match_list)) #todo: might not be needed anymore
    return match_list


# returns list of account infos: summoner name,summoner Id, account Id
def account_info(lw, region, mode, tier, division, get_key):
    """
        Fetch account details about all the players in the given tier,division,region,mode

        Parameters:
        lw (LolWatcher): a LolWatcher instance
        region(String): a server region
        mode(String): type of queue
        tier(String): tier of the queue
        division(String): division of the queue
        get_key(Func): function that returns a new api key

        Returns:
        List[Dict]: list of players' summoner name, summonerId, accountId belonging to the given tier,division,region
    """
    names, sum_ids = sum_name_id(lw, region, mode, tier, division, get_key)
    acc_ids = acc_id_by_sum_name(lw, region, names, get_key)
    accounts = []
    for i in range(len(acc_ids)):
        if not acc_ids[i] is None:
            accounts.append({'summonerName': names[i], 'summonerId': sum_ids[i], 'puuid': acc_ids[i]})
    return accounts


def cln_match(match_lists, db_matches):
    """
        Clean match lists by removing duplicated games, both present inside the list and the database

        Parameters:
        match_lists(List[Dict]): List of clash games for each account
        db_matches(Collection): pymongo collection containing matches documents

        Returns:
        List[Dict]: list of clash games ids
    """
    # match_list = [match for matches in match_lists for match in matches]
    # game_ids = [match.get('gameId') for match in match_list]
    # game_ids = list(dict.fromkeys(game_ids))
    for g_id in match_lists:
        if db_matches.count_documents({"_id": g_id}) > 0: #TODO (high prio): g_id is now a string, is that a problem ?
            match_lists.remove(g_id)
    return match_lists


def check_jungler(player):
    spells = [player["spell1Id"], player["spell2Id"]]
    return 11 in spells  # 11 is smite #todo (low): remove hardcoded value


def get_role(pos, player):
    if check_jungler(player):
        return "JUNGLE"
    x = pos["x"]
    y = pos["y"]
    if x > 3500 and y < 3500 or x > 11000 and y < 11000:  # todo (very low): can remove the hardcoded values?
        return "BOT"
    if x < 3500 and y > 3500 or x < 11000 and y > 11000:
        return "TOP"
    return "MID"


def check_bot_roles(botlane, frame):
    farm = [frame[str(player["id"])]['minionsKilled'] for player in botlane]
    support = 0 if farm[0] < farm[1] else 1
    adc = 0 if support == 1 else 1
    return {"SUPPORT": {"summonerId": botlane[support]['summonerId'], "champion": botlane[support]['champion']},
            "ADC": {"summonerId": botlane[adc]['summonerId'], "champion": botlane[adc]['champion']}}


def add_new_matches(lw, match_list, db_matches, region, get_key):
    """
        Fetch details of matches and store them into the database

        Parameters:
        lw (LolWatcher): a LolWatcher instance
        match_lists(List[Integer]): List of clash games ids
        db_matches(Collection): pymongo collection containing matches documents
        region(String): a server region
        get_key(Func): function that returns a new api key
    """
    big_region = REGION2BIG_REGION[region]
    for g_id in match_list:

        #get match by id
        command2call = partial(lw.matchv5.by_id, region, g_id)
        is_successful, match = safe_api_call(command2call, get_key)
        if not is_successful:
            continue #unlucky

        if match['info']['queueId'] != 700: #get only clash queues: todo: improve code
            break

        #get timeline to enstablish roles
        command2call = partial(lw.matchv5.timeline_by_match, big_region, g_id)
        is_successful, timeline = safe_api_call(command2call, get_key)
        if not is_successful:
            continue #unlucky part2

        m2_frame = timeline['frames'][2]['participantFrames']
        m_last_frame = timeline['frames'][-1]['participantFrames']
        m2_pos = {int(num): m2_frame[num]['position'] for num in m2_frame.keys()}
        new_doc = {"_id": match["gameId"], "region": region, "duration": match["gameDuration"],
                    "season": match["seasonId"],
                    "patch": float(re.search('^\d+[.]\d+', match["gameVersion"]).group())}
        teams = [team["teamId"] for team in match["teams"]]
        new_doc["winner"] = teams[0] if match["teams"][0]["win"] == 'Win' else teams[1]
        i = 0
        bans = [[], []]
        for team in match["teams"]:
            for ban in team["bans"]:
                bans[i].append(ban["championId"])
            i += 1
        teams = ({"teamId": teams[0], "bans": bans[0]}, {"teamId": teams[1], "bans": bans[0]})
        identities = {part["participantId"]: part["player"]["summonerId"] for part in
                        match["participantIdentities"]}
        bot = [[], []]
        for player in match["participants"]:
            team = 0 if player["teamId"] == teams[0]["teamId"] else 1
            role = get_role(m2_pos[player["participantId"]], player)
            champion = player["championId"]
            sum_id = identities[player["participantId"]]
            if role != "BOT":
                teams[team][role] = {"summonerId": sum_id, "champion": champion}
            else:
                bot[team].append({"summonerId": sum_id, "champion": champion, "id": player["participantId"]})
        if len(bot[0]) == 2 and len(bot[1]) == 2 and len(teams[0]) == 5 and len(teams[1]) == 5:
            for team in range(2):
                bot_roles = check_bot_roles(bot[team], m_last_frame)
                teams[team]["SUPPORT"] = bot_roles["SUPPORT"]
                teams[team]["ADC"] = bot_roles["ADC"]
            new_doc["team1"] = teams[0]
            new_doc["team2"] = teams[1]
            db_matches.insert_one(new_doc)


def get_uncrawled(db):
    if not "ReDiTi" in db.list_collection_names():
        comb = [{'region': reg, 'tier': tier, 'division': div, 'crawled': False} for reg in REGIONS for tier in TIERS
                for div in DIVISIONS]
        re_di_ti = db["ReDiTi"]
        re_di_ti.insert_many(comb)
    else:
        re_di_ti = db["ReDiTi"]
    to_crawl = re_di_ti.find({'crawled': False})
    return [elem for elem in to_crawl]


def start_crawling(API_KEY, get_key, db_url = "mongodb://datacaker:27017"):
    cluster = MongoClient(db_url, connect=True)
    db = cluster.get_database("mooncaker")
    db_matches = db.get_collection("matches")
    to_crawl = get_uncrawled(db)
    db_rediti= db.get_collection("ReDiTi")
    lol_watcher = LolWatcher(API_KEY)
    key_set = partial(set_new_key, lol_watcher, get_key)
    for elem in to_crawl:
        region = elem['region']
        tier = elem['tier']
        division = elem['division']
        logging.info(f"datacrawler: Crawling {region}, {tier}, {division}")
        accounts = account_info(lol_watcher, region, 'RANKED_SOLO_5x5', tier, division, key_set) #todo: not hardcode mode
        match_lists = clash_matches(lol_watcher, region,
                                    [account.get('puuid') for account in accounts],
                                    key_set)
        match_list = cln_match(match_lists, db_matches)
        add_new_matches(lol_watcher, match_list, db_matches, region, key_set)
        db_rediti.update_one({'_id': elem['_id']}, {'$set': {'crawled': True}})

def main():
    # parse arguments in order to get the riot API
    parser = argparse.ArgumentParser(description='Crawls some lol data about clash')
    parser.add_argument('--API-file', help='the filename with the riot API key')
    parser.add_argument('--API', help='the riot API key')
    parser.add_argument('--db-url', help='the url of the mongo db, default is localhost')
    parser.add_argument('--test-api', help='if given it will only test the connection to riot API without the database',
                        action='store_true')
    parser.add_argument('--test-db', help= 'if given it will only test the database without accessing the api',
    action='store_true')
    args = vars(parser.parse_args())

    if args['test_db'] == True:
        #todo: test the database
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
    
    if args['test_api'] == True:
        # test only api connection without db    
        import random
        region = random.choice(REGIONS)
        tier = random.choice(TIERS)
        division = random.choice(DIVISIONS)
        big_region = REGION2BIG_REGION[region]
        print(f"Connecting to lol API, crawling {region} {tier} {division}", flush=True)
        watcher = LolWatcher(api_key=RIOT_API_KEY)
        print("Connected", flush=True)
        print("Retrieving account info", flush=True)
        accounts = account_info(watcher, region, 'RANKED_SOLO_5x5', tier, division, input)
        print("Account info retrieved", flush=True)
        print("Retrieving match list", flush=True)
        match_lists = clash_matches(watcher, region, [account.get('puuid') for account in accounts], input)
        print("Match list retrieved", flush=True) 
        match_list = [match for matches in match_lists for match in matches]
        for g_id in match_list[:20]:
            print("Getting match by id", flush=True)
            watcher.matchv5.by_id(big_region, g_id)
            print("Got match by id", flush=True)
            watcher.matchv5.timeline_by_match(big_region, g_id)
            print("Successfully crawled one match", flush=True)
        print("Successfully crawled 20 matches", flush=True)
        return

    db_url = "mongodb://localhost:27017" if args['db_url'] is None else args['db_url']

    start_crawling(RIOT_API_KEY, input, db_url)
    
if __name__ == "__main__":
    main()
