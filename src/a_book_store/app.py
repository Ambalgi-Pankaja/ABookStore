import time
import uvicorn
import argparse
import os
import json
from datetime import datetime
from typing import Optional

from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi import Body, FastAPI, Query, status
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from a_book_store.utils import (
    RequestLoggerMiddleware,
    get_logger,
    calculate_record_skip,
    total_number_pages,
    get_prev_page,
    get_next_page
)
from a_book_store.config import Config
from a_book_store.models import Book, User

START_TIME = None
VERSION = "v1"
FAMILY = "generic"
SERVICE_NAME = "a_book_store"
DB_NAME = "a_book_store"
BOOK_COLLECTION = "book"
USER_COLLECTION = "user"

client: Optional[MongoClient] = None

LOG = get_logger()


def bootstrap() -> MongoClient:
    config = Config()
    mongo_client = MongoClient(config.database_usi)
    if mongo_client:
        return mongo_client
    raise PyMongoError(message="Unable to create Mongo client.")


app = FastAPI(title=SERVICE_NAME, version=VERSION)
app.middleware("http")(RequestLoggerMiddleware())
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    global START_TIME
    global client
    client = bootstrap()
    START_TIME = time.time()


@app.get("/", response_class=RedirectResponse, include_in_schema=False)
async def root():
    return RedirectResponse("/docs")


@app.get("/healthcheck")
async def ping():
    return {"Success"}


@app.post("/book")
async def add_book(book: Book = Body(default=None)):
    try:
        book_json = jsonable_encoder(book)

        inserted_book = client[DB_NAME][BOOK_COLLECTION].insert_one(book_json)

        new_book = client[DB_NAME][BOOK_COLLECTION].find_one(
            {"_id": inserted_book.inserted_id},
            {"_id": False}
        )
        if new_book:
            return JSONResponse(status_code=status.HTTP_201_CREATED, content=new_book)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTT
        )


def run():
    env_prefix = Config.Config.env_prefix.lower()
    argp = argparse.ArgumentParser(
        description="Exposes test content catalog for retrieval.",
        allow_abbrev=False,
        formatter_class=argparse.RawTextHelpFormatter
    )
    argp.add_argument(
        "--databaseuri",
        help=f"URI for mongodb.",
        default=None,
    )
    argp.add_argument(
        "--dev",
        help="use dev configs",
        action="store_true"
    )
    args = vars(argp.parse_args())

    dev = args.pop('dev')
    if dev:
        pass
    for key, value in args.items():
        if value is not None:
            os.environ[env_prefix + key.lower()] = value

        if dev:
            uvicorn.run("a_book_store.app:app")
        else:
            uvicorn.run("a_book_store.app:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    run()
