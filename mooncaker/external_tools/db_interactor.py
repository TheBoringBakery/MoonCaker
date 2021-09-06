"""
    This file is responsible for the interaction with the mongo db
"""
from pymongo import MongoClient
from . import REGIONS, TIERS, DIVISIONS
import os


class Database():

    def __init__(self, db_url=None):
        """
        Initializes the object by connecting to the Mongo DB if a url is given
        otherwise it connects to a mock of a Mongo DB (testing only)

        Args:
            db_url (str, optional): The url on which to find the Mongo DB. Defaults to None.
        """
        if db_url is not None:
            self.db_url = db_url
            self.db = MongoClient(db_url, connect=False).get_database("mooncaker")
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

    def set_rediti(self):
        """
        If the collection used to track the crawler region, tier, division is empty
        it gets initialized
        """
        if self.db_rediti.count_documents({}) == 0:
            comb = [{'region': reg,
                     'tier': tier,
                     'division': div,
                     'page': 1,
                     'crawled': False}
                    for reg in REGIONS
                    for tier in TIERS
                    for div in DIVISIONS]
            self.db["ReDiTi"].insert_many(comb)

    def reset_rediti(self):
        """
        Resets the tracking of the crawling process
        """
        self.db_rediti.drop()
        self.set_rediti()

    def ranks2crawl(self):
        """
        A generator that yields the ranks that needs to be crawled

        Yields:
            (tuple): a tuple with the _id, region, tier, division and page to crawl
        """
        for elem in self.to_crawl:
            yield elem['_id'], elem['region'], elem['tier'], elem['division'], elem['page']

    def mark_as_crawled(self, id):
        self.db_rediti.update_one({'_id': id}, {'$set': {'crawled': True}})

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
        not_pres = [g_id for g_id in match_list
                    if not self.db_matches.count_documents({"_id": g_id}) > 0]
        not_pres = list(dict.fromkeys(not_pres))
        return not_pres

    def count_matches(self):
        return self.db_matches.count_documents({})

    def get_rediti(self):
        return self.db_rediti.find({}, {'_id': 0})

    def create_matches_csv(self):
        command_mongoexport = 'mongoexport --uri=' + self.db_url + '/mooncaker --collection=matches --type=csv --fields=_id,region,duration,patch,winner,team1,team2 --out=matches.csv' 
        os.system('rm matches.csv')
        os.system(command_mongoexport)