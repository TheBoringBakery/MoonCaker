from riotwatcher import LolWatcher
import numpy as np
import argparse


def getSummonersIdAndNameByLeague(lw, region,mode,tier,division):
	playersList= lw.league.entries(region,mode,tier,division)
	return np.array([[summoner['summonerName'],summoner['summonerId']] for summoner in playersList])

#gets account Ids of given summoners, returning None for accounts not found (che cazzo ne so anche se li ho appena fetchati dalla lega non li trova)
def getAccountIdsBySummoners(lw, region,summonerNames):
	ids=[]
	for name in summonerNames:
		try:
			ids.append(lw.summoner.by_name(region, name).get('accountId'))
		except:
			ids.append(None)
	return ids

#gets Clash match list for each given accountId, returning None for accounts with no clash games
def getClashMatchlist(lw, region,accountIds):
	matchList=[]
	for encr_id in accountIds:
		try:
			matchList.append(lw.match.matchlist_by_account(region,encr_id, '700'))
		except:
			matchList.append(None)
	return matchList

#returns list of account infos: summoner name,summoner Id, account Id
def getAccountInfo(lw, region,mode,tier,division):
	names= getSummonersIdAndNameByLeague(lw, region,mode,tier,division)
	ids= getAccountIdsBySummoners(lw, region,names[:,0])
	accounts=[]
	for i in range(len(ids)): 
		accounts.append({'summonerName': names[i,0], 'summonerId': names[i,1], 'accountId': ids[i]})		
	return accounts


def main():
	#parse arguments in order to get the riot API
	parser = argparse.ArgumentParser(description='Crawls some lol data about clash')
	parser.add_argument('--API-file', help='the filename with the riot API key')
	parser.add_argument('--API', help='the riot API key')
	args = vars(parser.parse_args())

	if args['API'] is None and args['API_file'] is None:
		print("You must either provide the API through the command line or through a file")
		parser.print_help()
		exit()
	
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
			exit()
			
	lol_watcher = LolWatcher(RIOT_API_KEY)
	accounts = getAccountInfo(lol_watcher, 'euw1','RANKED_SOLO_5x5', 'DIAMOND', 'I') #still to remove accounts with None values :)
	clashMatchLists = getClashMatchlist(lol_watcher, 'euw1', [account.get('accountId') for account in accounts])


if __name__ == "__main__":
	main()
	
	
	

