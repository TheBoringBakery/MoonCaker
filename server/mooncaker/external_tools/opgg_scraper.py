from enum import Enum, auto
import requests
from bs4 import BeautifulSoup

#possible regions: euw, na, jp, ...
query_url = lambda region, summoner_name: f'https://{region}.op.gg/summoner/champions/userName={summoner_name}'

class STAT_ITEM(Enum):
    CHAMPION = auto()
    PLAYED = auto()
    WIN_RATE = auto()
    KILLS = auto()
    DEATHS = auto()
    ASSISTS = auto()
    GOLD = auto()
    CS = auto()

def summoner_stats(region, summoner_name):
    """Given a summoner name and its region returns key stats by scraping op.gg

    Args:
        region (str): a valid lol region, examples are 'euw', 'eune', 'na', etc.
        summoner_name (str): the summoner name

    Returns:
        dict: a list of dict, each dict is relative to a champion and its keys are the values of STAT_ITEM
    """
    stats = []
    response = requests.get(query_url(region, summoner_name))
    if response.status_code >= 300:
        print(f'Got bad status code: {response.status_code}, the content is: {response.text}')
        return None
    whole_page = BeautifulSoup(response.text, 'html.parser')
    champion_table = whole_page.find('tbody')

    #adds name
    for champion in champion_table.find_all('td', class_="ChampionName Cell"):
        stats.append({STAT_ITEM.CHAMPION: champion.get_text().strip()})

    #add playes and win rate
    for index, win_ratio in enumerate(champion_table.find_all('td', class_="RatioGraph Cell")):
        played = 0
        wins = win_ratio.find('div', class_="Text Left")
        if wins: #None check #todo
            wins = int(wins.get_text()[0: -1])
            played += wins #remove terminating W or L (string is in the format '10W')
        else:
            wins = 0
        losses = win_ratio.find('div', class_="Text Right")
        if losses:
            played += int(losses.get_text()[0: -1])
        win_rate = wins / played * 100
        stats[index][STAT_ITEM.PLAYED] = played
        stats[index][STAT_ITEM.WIN_RATE] = win_rate

    #add kda
    for index, kda in enumerate(champion_table.find_all('div', class_="KDA")):
        kda = [float(x.get_text()) for x in kda.find_all('span')]
        stats[index][STAT_ITEM.KILLS] = kda[0]
        stats[index][STAT_ITEM.DEATHS] = kda[1]
        stats[index][STAT_ITEM.ASSISTS] = kda[2]

    #add gold, cs
    index = 0
    for td_index, elem in enumerate(champion_table.find_all('td', class_="Value Cell")):
        if td_index % 10 == 0:
            stats[index][STAT_ITEM.GOLD] = int(''.join(elem.get_text().strip().split(',')))
        if td_index % 10 == 1:
            stats[index][STAT_ITEM.CS] = float(elem.get_text().split(' ')[0].strip())
            index += 1
    
    return stats

if __name__ == "__main__":
    print(summoner_stats('euw', 'feka7'))