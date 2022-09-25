from ..database import MongoConnectionManager

from .schemas import User, UserInDB

auth_collection_name = "users"


def create_user(user: UserInDB):
    data = user.dict()
    with MongoConnectionManager(auth_collection_name) as conn:
        conn.insert_one(data)
    
    return User(**data)


def read_user(username):
    query = {"username": username}
    user_data = None
    with MongoConnectionManager(auth_collection_name) as conn:
        user_data = list(conn.find(query, {"_id": 0}).limit(1))
        if user_data:
            user_data = user_data[0]
    
    return user_data


def is_exist_user(username):
    query = {"username": username}
    is_exist = None
    with MongoConnectionManager(auth_collection_name) as conn:
        user_data = list(conn.find(query, {"_id": 0}))
        is_exist = True if user_data else False
    
    return is_exist


def read_user_with_id(username):
    query = {"username": username}
    user_data = None
    with MongoConnectionManager(auth_collection_name) as conn:
        user_data = list(conn.find(query).limit(1))
        if user_data:
            user_data = user_data[0]
    
    return user_data
