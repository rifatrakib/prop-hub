from pymongo import MongoClient
from .config import read_config


class MongoConnectionManager():
    def __init__(self, collection):
        self.client = MongoClient(read_config("mongo_connection_uri"))
        self.database = read_config("database_name")
        self.collection = collection
    
    def __enter__(self):
        self.database = self.client[self.database]
        self.collection = self.database[self.collection]
        return self.collection
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.client.close()
