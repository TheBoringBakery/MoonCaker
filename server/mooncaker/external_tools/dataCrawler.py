"""
    Crawls lol data with the APi and stores it in a database
"""

from riotwatcher import LolWatcher, ApiError
from pymongo import MongoClient
import argparse
import numpy as np
import time
from pymongo import MongoClient
import logging

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
    redo = True
    players_list = []
    while (redo):
        try:
            players_list = lw.league.entries(region, mode, tier, division)
            redo = False
        except ApiError as err:
            if err.response.status_code == 403:
                lw._base_api._api_key = get_key()
            elif err.response.status_code == 429:
                time.sleep(60)
            else:
                raise
    return np.array([[summoner.get('summonerName'), summoner.get('summonerId')] for summoner in players_list])


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
    for name in summoner_names[:10]:
        redo = True
        while (redo):
            try:
                ids.append(lw.summoner.by_name(region, name).get('accountId'))
                redo = False
            except ApiError as err:
                if err.response.status_code == 404:
                    ids.append(None)
                    redo = False
                elif err.response.status_code == 403:
                    lw._base_api._api_key = get_key()
                elif err.response.status_code == 429:
                    time.sleep(60)
                else:
                    raise
    return ids


# gets Clash match list for each given accountId, returning None for accounts with no clash games
def clash_matches(lw, region, accountIds, get_key):
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
    for encr_id in accountIds:
        redo = True
        while (redo):
            try:
                match_list.append(lw.match.matchlist_by_account(region, encr_id, '700').get('matches'))
                redo = False
            except ApiError as err:
                if err.response.status_code == 404:
                    match_list.append(None)
                    redo = False
                elif err.response.status_code == 403:
                    lw._base_api._api_key = get_key()
                elif err.response.status_code == 429:
                    time.sleep(60)
                else:
                    raise
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
    names = sum_name_id(lw, region, mode, tier, division, get_key)
    ids = acc_id_by_sum_name(lw, region, names[:, 0], get_key)
    accounts = []
    for i in range(len(ids)):
        if not ids[i] is None:
            accounts.append({'summonerName': names[i, 0], 'summonerId': names[i, 1], 'accountId': ids[i]})
    return accounts


def cln_match(match_lists, db_matches):
    """
        Clean match lists by removing None values and duplicated games, both present inside the list and the database

        Parameters:
        match_lists(List[Dict]): List of clash games for each account
        db_matches(Collection): pymongo collection containing matches documents

        Returns:
        List[Dict]: list of clash games ids
    """
    match_list = list(filter(None, match_lists))
    match_list = [match for matches in match_list for match in matches]
    game_ids = [match.get('gameId') for match in match_list]
    game_ids = list(dict.fromkeys(game_ids))
    for g_id in game_ids:
        if db_matches.count_documents({"gameId": g_id}) > 0:  
            game_ids.remove(g_id)
    return game_ids


def check_jungler(player):
    spells = [player["spell1Id"], player["spell2Id"]]
    return 11 in spells  # 11 is smite #todo (low): remove hardcoded value


def get_role(pos, player):
    if check_jungler(player):
        return "JUNGLE"
    x = pos["x"]
    y = pos["y"]
    if x > 3500 and y < 3500 or x > 11000 and y < 11000: #todo (very low): can remove the hardcoded values? 
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
    for g_id in match_list:
        try:
            match = lw.match.by_id(region, g_id)
            m2_frame = lw.match.timeline_by_match(region, g_id)['frames'][2]['participantFrames']
            m_last_frame = lw.match.timeline_by_match(region, g_id)['frames'][-1]['participantFrames']
            redo = False #variable not used?
        except ApiError as err:
            if err.response.status_code == 404:
                logging.warning(f"Received a 404 status code when retrieving {g_id} game id")
                match_list.append(None)
                redo = False
            elif err.response.status_code == 403:
                logging.warning(f"Received a 403 status code, waiting new API")
                lw._base_api._api_key = get_key()
            elif err.response.status_code == 429:
				#todo (medium): when does this happen ?? Todo: add log to this branch
                time.sleep(60)
            else:
                raise
        m2_pos = {int(num): m2_frame[num]['position'] for num in m2_frame.keys()}
        new_doc = {"_id": match["gameId"], "region": 'euw1', "duration": match["gameDuration"],
                   "season": match["seasonId"]}
        teams = [team["teamId"] for team in match["teams"]]
        new_doc["winner"] = teams[0] if match["teams"][0]["win"] == 'Win' else teams[1]
        i = 0
        bans = [[], []]
        for team in match["teams"]:
            for ban in team["bans"]:
                bans[i].append(ban["championId"])
            i += 1
        teams = ({"teamId": teams[0], "bans": bans[0]}, {"teamId": teams[1], "bans": bans[0]})
        identities = {part["participantId"]: part["player"]["summonerId"] for part in match["participantIdentities"]}
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


# to add iteration over all regions, divisions and tiers. Write on file every tier fetched.
def start_crawling(API_KEY, get_key):
    REGIONS = ['euw1', 'eun1', 'kr', 'na1']
    TIERS = ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'IRON']
    DIVISIONS = ['I', 'II', 'III', 'IV', 'V']
    cluster = MongoClient('mongodb://localhost:27017/') 
    db = cluster["mooncaker"]
    db_matches = db["matches"]
    lol_watcher = LolWatcher(API_KEY)
    for region in REGIONS:
        for tier in TIERS:
            for division in DIVISIONS:
                logging.info(f"Crawling {region}, {tier}, {division}")
                accounts = account_info(lol_watcher, region, 'RANKED_SOLO_5x5', tier, division, get_key)
                match_lists = clash_matches(lol_watcher, 'euw1', [account.get('accountId') for account in accounts],
                                            get_key)
                match_list = cln_match(match_lists, db_matches)
                add_new_matches(lol_watcher, match_list, db_matches, region, get_key)


def main():
    # parse arguments in order to get the riot API
    parser = argparse.ArgumentParser(description='Crawls some lol data about clash')
    parser.add_argument('--API-file', help='the filename with the riot API key')
    parser.add_argument('--API', help='the riot API key')
    args = vars(parser.parse_args())

    if args['API'] is None and args['API_file'] is None:
        print("You must either provide the API through the command line or through a file")
        parser.print_help()
        return

    RIOT_API_KEY = ""
    if not args['API'] is None:
        RIOT_API_KEY = args['API']
    else:
        RIOT_API_KEY_FILENAME = args['API_file']
        try:
            with open(RIOT_API_KEY_FILENAME) as file:
                RIOT_API_KEY = file.readline()
        except FileNotFoundError:
            print("Couldn't find the specified file with the RIOT API key, please check again")
            return
    start_crawling(RIOT_API_KEY, input)


if __name__ == "__main__":
    main()
