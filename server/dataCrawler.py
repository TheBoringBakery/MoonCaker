"""
	Crawls lol data with the APi and stores it in a database
"""

from riotwatcher import LolWatcher,ApiError
from pymongo import MongoClient
import argparse
import numpy as np
import time

REGIONS= ['euw1','eun1','kr','na1'] #just this because other regions sucks? :P moreover, why no china rito? :( 
from pymongo import MongoClient
def sum_name_id(lw, region, mode, tier, division, get_key):
	"""
		Fetch all the summoner names in a tier and division
		
		Parameters: 
		lw (LolWatcher): a LolWatcher instance
		region(String): a server region
		mode(String): type of queue
		tier(String): tier of the queue
		division(String): division of the queue
		
		Returns:
		List[List[String]]: list of players' summoner name and summonerId belonging to the given tier,division,region
	"""
	redo=True
	players_list=[]
	while(redo):
		try:
			players_list= lw.league.entries(region, mode, tier, division)
			redo= False
		except ApiError as err:	
			if err.response.status_code == 403:
				lw._base_api._api_key = get_key()
			elif err.response.status_code == 429:
				time.sleep(60)
			else:
				raise
	return np.array([[summoner.get('summonerName'), summoner.get('summonerId')] for summoner in players_list])

#gets account Ids of given summoners, returning None for accounts not found (che cazzo ne so anche se li ho appena fetchati dalla lega non li trova)
def acc_id_by_sum_name(lw, region, summoner_names, get_key):
	"""
		Fetch accountIds for each summoner name and returns them as a list
		
		Parameters: 
		lw (LolWatcher): a LolWatcher instance
		region(String): the server region to which the accounts belong
		summoner_names(List[String]): list of summoner names to search accountIds for
		
		Returns:
		List[String]: list of accountIds associated to input summoner names, containing None if no accountId was found for the summoner name 
	"""
	ids=[]
	for name in summoner_names[:10]:
		redo=True
		while(redo):
			try:
				ids.append(lw.summoner.by_name(region, name).get('accountId'))
				redo=False
			except ApiError as err:
				if err.response.status_code == 404:
					ids.append(None)
					redo=False
				elif err.response.status_code == 403:
					lw._base_api._api_key = get_key()
				elif err.response.status_code == 429:
					time.sleep(60)
				else:
						raise
	return ids

#gets Clash match list for each given accountId, returning None for accounts with no clash games
def clash_matches(lw, region, accountIds, get_key):
	"""
		Fetch all clash games for the given accounts
		
		Parameters: 
		lw (LolWatcher): a LolWatcher instance
		region(String): the server region to which the accounts belong
		accountIds(List[String]): list of accountIds to search games for
		
		Returns:
		List[List[Dict]]: list containing a list of dictionaries with clash matches info for each accountId
	"""
	match_list=[]
	for encr_id in accountIds:
		redo=True
		while(redo):
			try:
				match_list.append(lw.match.matchlist_by_account(region,encr_id, '700').get('matches'))
				redo=False
			except ApiError as err:
				if err.response.status_code == 404:
					match_list.append(None)
					redo=False
				elif err.response.status_code == 403:
					lw._base_api._api_key = get_key()
				elif err.response.status_code == 429:
					time.sleep(60)
				else:
					raise
	return match_list

#returns list of account infos: summoner name,summoner Id, account Id
def account_info(lw, region, mode, tier, division, get_key):
	"""
		Fetch account details about all the players in the given tier,division,region,mode
		
		Parameters: 
		lw (LolWatcher): a LolWatcher instance
		region(String): a server region
		mode(String): type of queue
		tier(String): tier of the queue
		division(String): division of the queue
		
		Returns:
		List[Dict]: list of players' summoner name, summonerId, accountId belonging to the given tier,division,region
	"""
	names = sum_name_id(lw, region, mode, tier, division, get_key)
	ids = acc_id_by_sum_name(lw, region, names[:,0], get_key)
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
	match_list = [match for match_list in match_lists for match in match_list]
	game_ids = [match.get('gameId') for match in match_list]
	game_ids = list(dict.fromkeys(game_ids))	
	for g_id in game_ids:
		if db_matches.count_documents({"gameId": g_id}) > 0: #Collection.find({}).count() is much faster but deprecated :(
			game_ids.remove(g_id)
	return game_ids

def add_new_matches(match_list, db_matches):
		"""
		Fetch details of matches and store them into the database
	
		Parameters: 
		match_lists(List[Integer]): List of clash games ids
		db_matches(Collection): pymongo collection containing matches documents 
	"""
#TODO
	
	




#to add iteration over all regions, divisions and tiers. Write on file every tier fetched.
def start_crawling(API_KEY, get_key):
	cluster = MongoClient("mongodb+srv://mortorit:<PASSWORD>@mooncaker0.lzfme.mongodb.net/Mooncaker0?retryWrites=true&w=majority")
	db = cluster["mooncaker"]
	db_matches= db["matches"]
	lol_watcher = LolWatcher(API_KEY)
	accounts = account_info(lol_watcher, 'euw1', 'RANKED_SOLO_5x5', 'DIAMOND', 'I', get_key) #TODO loop over all division, tiers, regions
	match_lists = clash_matches(lol_watcher, 'euw1', [account.get('accountId') for account in accounts], get_key)
	match_list = cln_match(match_lists, db_matches)
	add_new_matches(match_list, db_matches)
	#TODO: crawl some data

def main():
	#parse arguments in order to get the riot API
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
	get_key= lambda: input() #why not pass directly input instead of lambda? I'm noob I don't understand
	start_crawling(RIOT_API_KEY, get_key)

if __name__ == "__main__":
	main()
	
	
	

