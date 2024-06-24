from argparse import ArgumentParser, RawTextHelpFormatter

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from core import setup_logging, LoggingMiddleware
from routers import (
    data_detail, 
    user_convo, 
    user_itinerary, 
    user_login, 
    refresh_token, 
    region_autocomplete, 
    main_chatbot, 
    member_chatbot, 
    STT, 
    image_upload
)


# Setup Logging
setup_logging("logs")

# Define FastAPI app
app = FastAPI()

# Middleware for CORS
all_origins = ["http://localhost:5173", "https://gildong.site"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=all_origins, # 모든 origin 허용 ["*"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LoggingMiddleware)

# Include Routers
app.include_router(data_detail.router)
app.include_router(main_chatbot.router)
app.include_router(member_chatbot.router)
app.include_router(user_convo.router)
app.include_router(user_itinerary.router)
app.include_router(user_login.router)
app.include_router(region_autocomplete.router)
app.include_router(refresh_token.router)
app.include_router(image_upload.router)
app.include_router(STT.router)

@app.get("/")
def read_root():
    return {"message": "API is ready!"}

# Command line arguments parser
def get_args():
    parser = ArgumentParser(description='Analysis API for "Gildong ChatBot" project', formatter_class=RawTextHelpFormatter)
    parser.add_argument('-fh', '--host', metavar='host', default="0.0.0.0", help="API Host")
    parser.add_argument('-fp', '--port', metavar='port', type=int, default=5041, help="API Port")
    return parser.parse_args()

# Main Execution
if __name__ == "__main__":
    args = get_args()
    uvicorn.run(app='__main__:app', host=args.host, port=args.port)