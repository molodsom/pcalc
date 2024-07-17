import os

from pymongo import MongoClient

client = MongoClient(os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/'))
db = client['calculator_db']