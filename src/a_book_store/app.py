import time
import uvicorn
import argparse
import os
import json
from datetime import datetime
from typing import Optional
from bson import json_util


from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi import Body, FastAPI, Query, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from a_book_store.utils import (
    RequestLoggerMiddleware,
    get_logger,
    calculate_record_skip,
)
from a_book_store.config import Config
from a_book_store.models import Book, User, Token
from a_book_store.password_management import (
    authenticate_user,
    create_access_token,
    get_current_user,
)

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
    mongo_client = MongoClient(config.database_uri)
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


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=60)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/book")
async def add_book(
    book: Book = Body(default=None), current_user: User = Depends(get_current_user)
):
    try:
        book_json = jsonable_encoder(book)

        inserted_book = client[DB_NAME][BOOK_COLLECTION].insert_one(book_json)

        new_book = client[DB_NAME][BOOK_COLLECTION].find_one(
            {"_id": inserted_book.inserted_id}, {"_id": False}
        )
        if new_book:
            return JSONResponse(status_code=status.HTTP_201_CREATED, content=new_book)
    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTPExceptions
    except Exception as exc:
        # Handle general exceptions and raise 500 internal server error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occurred while creating the book with {exc}",
        )


@app.get("/book")
async def get_books(
    page: int = Query(1, description="Page number"),
    page_size: int = Query(10, description="Number of items per page"),
    title: Optional[str] = Query(None, description="Title of the book"),
    author: Optional[str] = Query(None, description="Author of the book"),
    published_year: Optional[str] = Query(
        None, description="Published year of the book"
    ),
    genre: Optional[str] = Query(None, description="Genre of the book"),
    max_price: Optional[float] = Query(None, description="Max price of the book"),
):
    try:
        queries = []
        if title is not None:
            queries.append({"title": title})
        if author is not None:
            queries.append({"author": author})
        if published_year is not None:
            queries.append({"published_year": published_year})
        if genre is not None:
            queries.append({"genre": genre})
        if max_price is not None:
            queries.append({"price": {"$lt": max_price}})
        final_query = {}
        if queries:
            final_query = {"$and": queries}
        offset = calculate_record_skip(page=page, page_size=page_size)
        limit = page_size
        result = list(
            client[DB_NAME][BOOK_COLLECTION]
            .find(final_query, {"_id": False})
            .skip(offset)
            .limit(limit)
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(result))
        )
    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTPExceptions
    except Exception as exc:
        # Handle general exceptions and raise 500 internal server error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occurred while getting the books with {exc}",
        )


@app.patch(
    "/book/{title}",
    response_model=Book,
    response_description="Patch partial Book details",
    description="Patch Book details for given book title",
)
def patch_book(
    title: str,
    book: Book = Body(default=None),
    current_user: User = Depends(get_current_user),
):
    try:
        current_book = client[DB_NAME][BOOK_COLLECTION].find_one(
            {"title": title}, {"_id": False}
        )
        # If the book is not found, raise 404
        if not current_book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No book found with title '{title}'",
            )
        # Convert current book to the Book model
        current_book_model = Book(**jsonable_encoder(current_book))

        # Get the updated fields and apply them to the current book
        update_book = book.dict(exclude_unset=True)
        update_book_result = current_book_model.copy(update=update_book)

        # Convert the updated model back to JSON and add last_modified_at timestamp
        update_book_json = jsonable_encoder(update_book_result)
        update_book_json.update({"last_modified_at": f"{datetime.now()}"})

        # Update the book in the database
        update_result = client[DB_NAME][BOOK_COLLECTION].update_one(
            {"title": title}, {"$set": update_book_json}
        )
        # Check if the update was successful
        if update_result.modified_count == 1:
            updated_result = client[DB_NAME][BOOK_COLLECTION].find_one(
                {"title": title}, {"_id": False}
            )
            return JSONResponse(status_code=status.HTTP_200_OK, content=updated_result)
        else:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content="No updates made. The data is already up to date.",
            )
    except HTTPException as http_exc:
        raise http_exc  # Reraise HTTPExceptions
    except Exception as exc:
        # Handle general exceptions and raise 500 internal server error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error occurred while updating book with title '{title}': {exc}",
        )


@app.delete("/book/{title}")
def delete_book(title: str, current_user: User = Depends(get_current_user)):
    try:
        delete_result = client[DB_NAME][BOOK_COLLECTION].delete_one({"title": title})
        if delete_result.deleted_count == 1:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=f"Book with title {title} has been deleted",
            )
        else:
            # If no book was found with the provided title
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No book found with title '{title}'",
            )
    except Exception as exc:
        # Catch any other exceptions and return a server error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the book: {exc}",
        )


def run():
    env_prefix = Config.Config.env_prefix.lower()
    argp = argparse.ArgumentParser(
        description="Exposes test content catalog for retrieval.",
        allow_abbrev=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    argp.add_argument(
        "--databaseuri",
        help="URI for mongodb.",
        default=None,
    )
    argp.add_argument("--dev", help="use dev configs", action="store_true")
    args = vars(argp.parse_args())

    dev = args.pop("dev")
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
