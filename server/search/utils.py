import numpy as np
import pandas as pd
from pymongo.errors import DuplicateKeyError

from server.database import MongoConnectionManager


def get_top_property_ids(n, df):
    """
    INPUT:
    n - (int) the number of top properties to return
    df - (pandas dataframe) df as defined at the top of the notebook

    OUTPUT:
    top_properties - (list) A list of the top 'n' property titles

    """
    # Your code here
    result = df.groupby(["property_id"])["property_id"].agg(["count"])
    result.sort_values("count", inplace=True, ascending=False)
    top_properties = result.index[0:n].tolist()
    return top_properties  # Return the top property ids


def get_user_propertys(user_id, user_item):
    """
    INPUT:
    user_id - (int) a user id
    user_item - (pandas dataframe) matrix of users by propertys:
                1's when a user has interacted with an property, 0 otherwise

    OUTPUT:
    property_ids - (list) a list of the property ids seen by the user

    Description:
    Provides a list of the property_ids have been seen by a user
    """
    user_matrix = user_item[user_item.index == user_id]
    user_propertys = user_matrix.loc[:, user_matrix.eq(1).all()]
    property_ids = user_propertys.columns.tolist()
    # convert to string
    property_ids = [str(id) for id in property_ids]
    property_ids = np.sort(property_ids)
    return property_ids  # return the ids


def find_similar_users(user_id, user_item):
    """
    INPUT:
    user_id - (int) a user_id
    user_item - (pandas dataframe) matrix of users by articles:
                1's when a user has interacted with an article, 0 otherwise

    OUTPUT:
    similar_users - (list) an ordered list where the closest users
                    (largest dot product users) are listed first

    Description:
    Computes the similarity of every pair of users based on the dot product
    Returns an ordered

    """
    # compute similarity of each user to the provided user
    provided_user = user_item[user_item.index == user_id]
    similarity_df = user_item.dot(provided_user.T)
    # sort by similarity
    sorted_df = similarity_df.sort_values(user_id, ascending=False)
    sorted_df["key"] = sorted_df.index
    sorted_df.sort_values(
        [user_id, "key"], ascending=[False, True], inplace=True
    )
    # remove the own user's id
    sorted_df = sorted_df[sorted_df.index != user_id]
    # create list of just the ids

    most_similar_users = sorted_df.index.tolist()

    # return a list of the users in order from most to least similar
    return most_similar_users


def user_user_recs(user_id, user_item, m=10):
    """
    INPUT:
    user_id - (int) a user id
    m - (int) the number of recommendations you want for the user

    OUTPUT:
    recs - (list) a list of recommendations for the user

    Description:
    Loops through the users based on closeness to the input user_id
    For each user - finds propertys the user hasn't seen before and
    provides them as recs. Does this until m recommendations are found

    Notes:
    Users who are the same closeness are chosen arbitrarily as the 'next' user

    For the user where the number of recommended propertys starts below m
    and ends exceeding m, the last items are chosen arbitrarily

    """
    similar_users = find_similar_users(user_id, user_item)
    user_property_ids = get_user_propertys(user_id, user_item)

    recs = []
    flag = False
    for current_user in similar_users:
        current_property_ids = get_user_propertys(current_user, user_item)
        for property_id in current_property_ids:
            if (
                property_id not in user_property_ids
                and property_id not in recs
            ):
                recs.append(property_id)
            if len(recs) >= m:
                flag = True
                break
        if flag:
            break
    # For the user where the number of recommended propertys starts below m
    #     and ends exceeding m, the last items are chosen arbitrarily
    property_ids = user_item.columns.tolist()
    for i in range(len(recs), m):
        if property_id not in property_ids and property_id not in recs:
            recs.append(property_id)
    return recs  # return your recommendations for this user_id


def create_user_item_matrix(df):
    """
    INPUT:
    df - pandas dataframe with article_id, user_id columns

    OUTPUT:
    user_item - user item matrix

    Description:
    Return a matrix with user ids as rows and article ids on the
    columns with 1 values where a user interacted with
    an article and a 0 otherwise
    """
    # Fill in the function here
    df = df.drop_duplicates(["property_id", "user_id"])
    user_item = pd.crosstab(df.user_id, df.property_id)
    return user_item  # return the user_item matrix


def create_like_record(user_id: str, property_id: str):
    try:
        with MongoConnectionManager("collaborative_recommendation") as conn:
            conn.insert_one({"user_id": user_id, "property_id": property_id})
            return True
    except DuplicateKeyError as e:
        print(str(e))
        return False


def read_like_record(user_id: str):
    with MongoConnectionManager("collaborative_recommendation") as conn:
        data = list(conn.find({"user_id": user_id}, {"_id": 0}))

    response = {"property_id": [doc["property_id"] for doc in data]}
    return response


def delete_like_record(user_id: str, property_id: str):
    with MongoConnectionManager("collaborative_recommendation") as conn:
        conn.delete_one({"user_id": user_id, "property_id": property_id})
        return True


def get_collaborative_recommendation_data():
    with MongoConnectionManager("collaborative_recommendation") as conn:
        data = list(conn.find({}))

    return data


def reupload_collaborative_recommedation_data(data):
    with MongoConnectionManager("generated_recommendation") as conn:
        conn.delete_many({})
        print("old data deleted")
        conn.insert_many(data)
        print("new data uploaded")


def read_single_property_data(property_id: str):
    with MongoConnectionManager("real_estate_details") as conn:
        data = list(conn.find({"id": property_id}, {"_id": 0}))[0]

    return data


def read_liked_property_details(user_id: str):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$lookup": {
                "from": "real_estate_details",
                "localField": "property_id",
                "foreignField": "id",
                "as": "result",
            }
        },
        {"$project": {"_id": 0, "result._id": 0}},
    ]

    with MongoConnectionManager("collaborative_recommendation") as conn:
        data = list(conn.aggregate(pipeline))

    response = [doc["result"][0] for doc in data]
    return response
