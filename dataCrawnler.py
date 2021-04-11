RIOT_API_KEY = ""

#retrieve api key from file
with open("APIkey.txt", 'r') as api_file:
    RIOT_API_KEY = api_file.readline()

#to something with the api key