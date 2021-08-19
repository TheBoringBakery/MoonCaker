BIG_REGIONS = ['europe', 'americas', 'asia']
REGIONS = ['euw1', 'eun1', 'jp1', 'kr', 'na1', 'br1']
# league api wants region=euw1,... while matchv5 wants region=europe,...
REGION2BIG_REGION = {'euw1': 'europe',
                     'eun1': 'europe',
                     'jp1': 'asia',
                     'kr': 'asia',
                     'na1': 'americas',
                     'br1': 'americas'}
TIERS = ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', 'IRON']
DIVISIONS = ['I', 'II', 'III', 'IV']

LOG_FILENAME = "mooncaker.log"
LOGGER_NAME = "mooncaker.logger"
