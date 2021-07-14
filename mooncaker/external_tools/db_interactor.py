"""
    This file is responsible for the interaction with the mongo db
"""
from pymongo import MongoClient
from external_tools import REGIONS, TIERS, DIVISIONS


class Database():

    def __init__(self, db_url=None):
        if db_url is not None:
            self.db = MongoClient(db_url, connect=True).get_database("mooncaker")
            self.db_matches = self.db.get_collection("matches")
            self.db_rediti = self.db.get_collection("ReDiTi")

            self.set_rediti()
            self.to_crawl = [elem for elem in self.db_rediti.find({'crawled': False})]
            if not self.to_crawl:
                # nothing to crawl, reset rediti
                self.reset_rediti()
                self.to_crawl = [elem for elem in self.db_rediti.find({'crawled': False})]
        else:
            # No db, testing functionality
            import mongomock
            self.db = mongomock.MongoClient().db
            self.db_matches = self.db.collection
            self.db_rediti = self.db.collection
            import random
            region = random.choice(REGIONS)
            tier = random.choice(TIERS)
            division = random.choice(DIVISIONS)
            self.to_crawl = [{'_id': 101010,
                              'region': region,
                              'tier': tier,
                              'division': division,
                              'page': 1}]

    def reset_rediti(self):
        self.db_rediti.drop()
        self.set_rediti()

    def set_rediti(self):
        if self.db_rediti.count_documents([]) == 0:
            comb = [{'region': reg,
                     'tier': tier,
                     'division': div,
                     'page': 1,
                     'crawled': False}
                    for reg in REGIONS
                    for tier in TIERS
                    for div in DIVISIONS]
            self.db["ReDiTi"].insert_many(comb)

    def ranks2crawl(self):
        for elem in self.to_crawl:
            yield elem['_id'], elem['region'], elem['tier'], elem['division'], elem['page']
            self.db_rediti.update_one({'_id': elem['_id']}, {'$set': {'crawled': True}})

    def insert_match_page(self, id, match_docs, page):
        self.db_matches.insert_many(match_docs)
        self.db_rediti.update_one({'_id': id}, {'$set': {'page': page}})

    def filter_match_duplicates(self, match_list):
        """
            Clean match lists by removing duplicated games, both present inside the list and the database

            Parameters:
            match_lists(List[Dict]): List of clash games for each account

            Returns:
            List[Dict]: list of clash games ids
        """
        # match_list = [match for matches in match_lists for match in matches]
        # game_ids = [match.get('gameId') for match in match_list]
        # game_ids = list(dict.fromkeys(game_ids))
        not_pres = [g_id for g_id in match_list
                    if not self.db_matches.count_documents({"_id": g_id}) > 0]  # todo: explicit integer comparison
        not_pres = list(dict.fromkeys(not_pres))
        return not_pres
