import uvicorn
from a_book_store.config import Config
import argparse
import os


def main():
    env_prefix = Config.Config.env_prefix.lower()

    argp = argparse.ArgumentParser(
        description="Exposes catalog for retrieval",
        allow_abbrev=False,
        formatter_class=argparse.RawTextHelpFormatter
    )
    argp.add_argument(
        "--database-uri",
        help=f"URI for mongodb. This can also be specified \n via the {env_prefix}database_uri environment variable.",
        default=None
    )
    args = vars(argp.parse_args())

    for key, value in args.items():
        if value is not None:
            os.environ[env_prefix + key.lower()] = value

    uvicorn.run("a_book_store.app:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
