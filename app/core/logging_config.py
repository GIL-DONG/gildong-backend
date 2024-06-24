import os
import sys
import re
import uuid
import pytz
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from contextvars import ContextVar


request_id_var = ContextVar("request_id")  # declare a ContextVar object


class KSTFormatter(logging.Formatter):
    converter = datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        dt = dt.astimezone(pytz.timezone('Asia/Seoul'))
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())  # generate request_id

        # Storing request_id in contextvars
        request_id_var.set(request_id)

        response = await call_next(request)
        return response


def add_request_id(_, __, event_dict):
    # get request_id from contextvars and add to event_dict
    event_dict["request_id"] = request_id_var.get()
    return event_dict


def setup_logging(log_dir):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    calling_file = os.path.basename(sys.argv[0])
    file_name = os.path.splitext(calling_file)[0]

    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = KSTFormatter(log_format)

    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, f'log-{file_name}.log'),
        when="midnight",
        interval=1,
        backupCount=7
    )
    file_handler.suffix = "_%Y-%m-%d.log"
    file_handler.extMatch = re.compile(r"_\d{4}-\d{2}-\d{2}\.log$")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.addHandler(file_handler)
    uvicorn_logger.setLevel(logging.INFO)
    
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    uvicorn_access_logger.addHandler(file_handler)
    uvicorn_access_logger.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(logging.INFO)

    structlog.configure(
        processors=[
            add_request_id,  # custom processor to add request_id
            structlog.stdlib.add_log_level,
            structlog.processors.JSONRenderer(ensure_ascii=False)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )