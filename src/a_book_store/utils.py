import logging
import platform
import sys
import time
import math
from starlette.requests import Request


class RequestLoggerMiddleware:
    def __init__(self):
        self._logger = get_logger()

    async def __call__(self, request: Request, call_next):
        request_source = f"{request.client.host}: {request.method} @ {request.base_url} {request.scope['path']}"
        self._logger.info(f"Received request from {request_source}")
        start_time = time.perf_counter()
        response = await call_next(request)
        stop_time = time.perf_counter()
        self._logger.info(
            f"Finished request from {request_source}; took {round(stop_time - start_time, 3)} seconds"
        )
        return response


def get_telemetry(name, version, family, start_time):
    return {
        "microservice_name": name,
        "microservice_version": version,
        "microservice_family": family,
        "os_version": platform.platform(),
        "uptime_in_secs": int(time.time() - start_time),
        "hit_number": 0
    }


def get_logger() -> logging.Logger:
    logger = logging.getLogger(__name__)
    if len(logger.handlers) == 0:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)-15s %(name)s %(levelname)-8s %(message)s"
        )
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


def calculate_record_skip(page: int, page_size: int) -> int:
    """
    This method is used for pagination
    :param page:
    :param page_size:
    :return:
    """
    return (page - 1) * page_size


def total_number_pages(total_items: int, limit: int) -> int:
    """
    This method will return total number of pages for given page size
    :param total_items:
    :param limit:
    :return:
    """
    total_pages = math.ceil(total_items/limit)
    return total_pages

def has_next(page, total_pages):
    """
    Method to return True if next page exists
    :param page:
    :param total_pages:
    :return:
    """
    return page < total_pages

def has_prev(page):
    """"
    Method to return True if prev page exists
    """
    return page > 1

def get_prev_page(page):
    if has_prev(page):
        prev_page = page - 1
    else:
        prev_page = page
    return prev_page


def get_next_page(page, total_pages):
    if has_next(page=page, total_pages=total_pages):
        next_page = page + 1
    else:
        next_page = page
    return next_page
