import numpy as np
import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Body
from fastapi.encoders import jsonable_encoder
from sentence_transformers import SentenceTransformer, util

from server.database import MongoConnectionManager
from server.search import utils
from server.search.schemas import Like

recommendation_collection_name = "collaborative_recommendation"
gen_reco_collection_name = "generated_recommendation"
property_collection_name = "real_estate_details"
router = APIRouter()

# be very cautious to use these
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
train = pd.read_csv("final.csv")


def check_new_user(user_id):
    with MongoConnectionManager(recommendation_collection_name) as conn:
        return list(conn.find({"user_id": user_id}))


def read_data():
    with MongoConnectionManager(recommendation_collection_name) as conn:
        user__red_data = list(conn.find({}, {"_id": 0}))
        df = pd.DataFrame(user__red_data)
        return df


def get_user_recommendation(user_id):
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
        {
            "$project": {
                "_id": 0,
                "result._id": 0,
                "property_id": 0,
            }
        },
    ]
    with MongoConnectionManager(gen_reco_collection_name) as conn:
        user__red_data = list(conn.aggregate(pipeline))
        return user__red_data[0]["result"]


def prepare_scores(text):
    global train
    global model
    data = train.copy()

    embedding_1 = model.encode(text, convert_to_tensor=True)
    for id_n in data["id"]:
        text2 = data.loc[data["id"] == id_n, "description"].tolist()[0]
        embedding_2 = model.encode(text2, convert_to_tensor=True)
        score = util.pytorch_cos_sim(embedding_1, embedding_2)
        data.loc[data["id"] == id_n, "score"] = float(score)

    return data


# TODO 2: Call preperare_recommendation()
# take data from collaborative_recommendation collection as dfc


def preperare_recommendation():
    dfc = pd.DataFrame(utils.get_collaborative_recommendation_data())
    user_item = utils.create_user_item_matrix(dfc)
    li = []
    # generate recommendation for all users
    user_id_list = dfc.user_id.unique()
    for user_id in user_id_list:
        recs = utils.user_user_recs(user_id, user_item, 10)
        li.append({"user_id": user_id, "property_id": recs})

    utils.reupload_collaborative_recommedation_data(li)


def get_new_user_recommendation():
    pipeline = [
        {"$group": {"_id": "$property_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
        {
            "$lookup": {
                "from": "real_estate_details",
                "localField": "_id",
                "foreignField": "id",
                "as": "result",
            }
        },
        {"$project": {"count": 0, "result._id": 0}},
    ]
    # get data from mongodb
    with MongoConnectionManager(recommendation_collection_name) as conn:
        user__red_data = list(conn.aggregate(pipeline))

    response = [doc["result"][0] for doc in user__red_data]
    return response


@router.get("/search/", tags=["search"])
async def get_prediction(text: str):
    data = prepare_scores(text)
    result = (
        data.sort_values("score", ascending=False)
        .drop(columns="score")
        .head(10)
        .to_dict("records")
    )
    return jsonable_encoder(result)


@router.get("/stats/", tags=["search"])
async def get_statistics(text: str):
    data = prepare_scores(text)
    data = data[data["score"] > 0.1]

    fields = ["Price", "Landsize", "Rooms"]
    index = ["Regionname"]
    aggregations = [np.mean, np.max, np.min, np.std]

    response = {}
    for field in fields:
        res = pd.pivot_table(
            data, values=field, index=index, aggfunc=aggregations, margins=True
        )

        res = res.droplevel(1, axis=1)
        res = res.round(2).replace({np.nan: None, pd.NA: None})
        response[field] = res.to_dict(orient="index")
    return response


@router.get("/recommendation/", tags=["machine learning"])
async def get_recommendation(user_id: str, background_tasks: BackgroundTasks):
    # check new user or old user
    # if new user do ranking based recommendation
    if not check_new_user(user_id):
        response = get_new_user_recommendation()
    else:
        # else do collaborative recommendation
        response = get_user_recommendation(user_id)

    background_tasks.add_task(preperare_recommendation)
    return response


@router.post("/recommendation/", tags=["machine learning"])
async def update_recommendation(background_tasks: BackgroundTasks):
    background_tasks.add_task(preperare_recommendation)
    return {"message": "recommendation calculation in progress"}


@router.get("/like/", tags=["property"])
async def read_liked_property(user_id: str):
    response = utils.read_like_record(user_id)
    return response


@router.post("/like/", tags=["property"])
async def user_liked_property(data: Like, background_tasks: BackgroundTasks):
    success = utils.create_like_record(data.user_id, data.property_id)
    if success:
        response = {"success": True, "message": "reaction stored"}
    else:
        response = {"success": False, "message": "unique constraint failed"}

    background_tasks.add_task(preperare_recommendation)
    return response


@router.delete("/like/", tags=["property"])
async def user_disliked_property(data: Like = Body()):
    success = utils.delete_like_record(data.user_id, data.property_id)
    if success:
        response = {"success": True, "message": "reaction deleted"}
    else:
        response = {"success": False, "message": "something went wrong"}

    return response


@router.get("/property/", tags=["property"])
async def read_property_details(property_id: str):
    response = utils.read_single_property_data(property_id)
    return response


@router.get("/bookmarked/", tags=["property"])
async def read_used_likes(user_id: str):
    response = utils.read_liked_property_details(user_id)
    return response
