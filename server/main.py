from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .auth import routes as auth_routes
from .search import routes as search_routes

app = FastAPI()
app.include_router(auth_routes.router)
app.include_router(search_routes.router)

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    app_name = config.read_config("app_name")
    return {"message": f"welcome to {app_name}!"}
