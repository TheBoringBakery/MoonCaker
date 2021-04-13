from riotwatcher import LolWatcher
import numpy as np


lw= LolWatcher('RGAPI-cbe3128a-f9c2-48f4-9a70-1b5d5f78a402')


def getSummonersIdAndNameByLeague(region,mode,tier,division):
	playersList= lw.league.entries(region,mode,tier,division)
	return np.array([[summoner['summonerName'],summoner['summonerId']] for summoner in playersList])

#gets account Ids of given summoners, returning None for accounts not found (che cazzo ne so anche se li ho appena fetchati dalla lega non li trova)
def getAccountIdsBySummoners(region,summonerNames):
	ids=[]
	for name in summonerNames:
		try:
			ids.append(lw.summoner.by_name(region, name).get('accountId'))
		except:
			ids.append(None)
	return ids

#gets Clash match list for each given accountId, returning None for accounts with no clash games
def getClashMatchlist(region,accountIds):
	matchList=[]
	for encr_id in accountIds:
		try:
			matchList.append(lw.match.matchlist_by_account(region,encr_id, '700'))
		except:
			matchList.append(None)
	return matchList

#returns list of account infos: summoner name,summoner Id, account Id
def getAccountInfo(region,mode,tier,division):
	names= getSummonersIdAndNameByLeague(region,mode,tier,division)
	ids= getAccountIdsBySummoners(region,names[:,0])
	accounts=[]
	for i in range(len(ids)): 
		accounts.append({'summonerName': names[i,0], 'summonerId': names[i,1], 'accountId': ids[i]})		
	return accounts


accounts = getAccountInfo('euw1','RANKED_SOLO_5x5', 'DIAMOND', 'I') #still to remove accounts with None values :)
clashMatchLists = getClashMatchlist('euw1', [account.get('accountId') for account in accounts])

	
	
	

