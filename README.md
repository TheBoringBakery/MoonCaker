# Clash Comp Advisor

## Purpose
Help noob players advence in their learning of drafting through personalized suggestions. Learn their weaknesses and strenghts.

## Usage
To run the dataCrawler.py, basic usage is:
```bash
pip install -r requirements.txt
python dataCrawler.py [--API-file API_FILE] [--API API]
```
Usage with a virtual environment (linux):
```bash
pip install virtualenv
python -m venv env
source ./env
pip install -r requirements.txt
python dataCrawler.py [--API-file API_FILE] [--API API]
```
Note that either the '--API-file' or the '--API' argument must be provided in order for the program to work

## Resources
Following are some data-set that might help for prototyping:
1. 2020 competitive matches https://www.kaggle.com/fernandorubiogarcia/2020-league-of-legends-competitive-games
1. Ranked games 2020 https://www.kaggle.com/gyejr95/league-of-legendslol-ranked-games-2020-ver1
1. ranked matched from 2014: https://www.kaggle.com/paololol/league-of-legends-ranked-matches
1. ranked 10.16: https://www.kaggle.com/fernandorubiogarcia/league-of-legends-high-elo-patch-1016
1. competitive 2015-18: https://www.kaggle.com/chuckephron/leagueoflegends

Idea: scrape op.gg instead of lol ??
## Roadmap
1. Language: Python
1. Decide ML method
1. Crawl the data
    1. Which data?
    1. which storage
    1. which preprocessing
1. Interface: command line
1. Architecture: how should the application present itself? desktop app? website + webapp? 
1. Interface: very simple
1. Deployment
1. Define testing phase. (alpha test??)
1. Scalability?????