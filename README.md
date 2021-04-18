# Clash Comp Advisor

# Purpose
Help noob players advence in their learning of drafting through personalized suggestions. Learn their weaknesses and strenghts.

# Usage
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

# Roadmap
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