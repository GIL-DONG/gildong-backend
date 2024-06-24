from argparse import ArgumentParser, RawTextHelpFormatter
from fastapi import FastAPI
import uvicorn
from routers import image_search
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)


# Define FastAPI app
app = FastAPI()

# Include Routers
app.include_router(image_search.router)


# Command line arguments parser
def get_args():
    parser = ArgumentParser(description='Analysis API for "Date Map ChatBot" project', formatter_class=RawTextHelpFormatter)
    parser.add_argument('-fh', '--host', metavar='host', default="0.0.0.0", help="API Host")
    parser.add_argument('-fp', '--port', metavar='port', type=int, default=5043, help="API Port")
    return parser.parse_args()

# Main Execution
if __name__ == "__main__":
    args = get_args()
    uvicorn.run(app='__main__:app', host=args.host, port=args.port)