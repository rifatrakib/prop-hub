from fastapi import FastAPI

from . import config

from .auth import routes as auth_routes

app = FastAPI()
app.include_router(auth_routes.router)


@app.get("/")
async def root():
    return {"message": "welcome fastapi!"}
