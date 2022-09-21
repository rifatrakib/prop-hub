from fastapi import FastAPI

from . import config


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "welcome fastapi!"}
