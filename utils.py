import random
import string
from typing import List, Union
import pymongo
from pymongo import MongoClient
import config
import time

client = MongoClient(config.MONGO_CONNECTION_STRING)
db = client[config.MONGO_DB]


# Exceptions

class QuoteNotFound(Exception):
    pass


class ForeignType(Exception):
    pass


class MissingField(Exception):
    pass


# Object models

class Quote:
    def __init__(self, messages: list):
        self.created_timestamp = int(time.time())
        self.id = self.generate_id()
        self.messages = [Message(i) for i in messages]

    def generate_id(self):
        """Generates a unique ID for new quotes"""
        unique = False
        while not unique:
            uid = ''.join(
                random.choice(
                    string.ascii_lowercase + string.digits
                ) for i in range(7)
            )
            data = db.quotes.find_one({'id': uid})
            if not data:
                self.id = uid

    def to_dict(self):
        return {
            'created_timestamp': self.created_timestamp,
            'id': self.id,
            'messages': [i.to_dict() for i in self.messages]
        }


class Message:
    def __init__(self, data):
        self.content = data['content']
        self.author = Author(data['author'])
        self.timestamp = data['timestamp']

    def to_dict(self):
        return {
            'content': self.content,
            'author': self.author.to_dict(),
            'timestamp': self.timestamp
        }


class Author:
    def __init__(self, data):
        self.avatar_url = data['avatar_url']
        self.colour = data['colour']
        self.id = data['id']
        self.username = data['username']

    def to_dict(self):
        return {
            'avatar_url': self.avatar_url,
            'colour': self.colour,
            'id': self.id,
            'username': self.username
        }


def get_random_quotes(n_quotes: int) -> List[dict]:
    return db.quotes.find(limit=n_quotes)


def get_quote_by_id(quote_id: str) -> dict:
    quote = db.quotes.find_one({{
        "id": {
            "$regex": f"^{quote_id}$",
            "$options": "i"
        }}})
    if not quote:
        raise QuoteNotFound()


def search(search_term: str) -> List[dict]:
    search_term = search_term.lower()
    quotes = [
        db.quotes.find(query)
        for query in (
            {"messages.content": {"$regex": f"{search_term}", "$options": "i"}},
            {"messages.author.id": {"$regex": f"^{search_term}$", "$options": "i"}},
            {"messages.author.username": {"$regex": f"{search_term}", "$options": "i"}},
        )
    ]
    if not quotes:
        raise QuoteNotFound
    return sorted(list(set(quotes)), key='created_timestamp', reverse=True)


def add_quote(data: list) -> dict:
    """Upload quote to the DB"""
    # Generate quote image
    # Upload image
    # Generate quote object
    quote_object = Quote(data)
    # Add quote to DB
    db.quotes.insert(quote_object.to_dict())
    # Return quote object
    return quote_object


def delete_quote(quote_id: str):
    """Remove quote from DB"""
    quote = db.quotes.find({"id": quote_id})
    if not quote:
        raise QuoteNotFound()
    db.quotes.delete_one({"id": quote_id})


def check_request(data: list):
    """Validates the JSON schema of quotes to be uploaded"""
    def str_check(x): return type(x) is str
    message_keys = {
        'timestamp': lambda x: type(x) is int,
        'content': str_check,
        'author': lambda x: type(x) is dict
    }
    author_keys = {
        'avatar_url': str_check,
        'colour': lambda x: type(x) is int and 0 <= x >= 16777215,
        'username': str_check,
        'id': str_check
    }
    for message in data:
        for field in message_keys:
            if field not in message:
                raise MissingField
            if not message_keys[field](message[field]):
                raise ForeignType

        author = message['author']
        for field in author_keys:
            if field not in author:
                raise MissingField
            if not author_keys[field](author[field]):
                raise ForeignType


def is_authorized(token: str) -> bool:
    """Checks auth token against DB"""
    check = db.keys.find_one({"token": token, "active": True})
    if check:
        return True
    return False
