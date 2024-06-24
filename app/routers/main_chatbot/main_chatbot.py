import uuid
from typing import Union, Optional, List

import structlog
from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
 
from core import InstanceManager, get_user_id
from routers.main_chatbot.router_config import parameters
from services import TIGAgentFactory
 

logger = structlog.get_logger()
router = APIRouter()


class Message(BaseModel):
    session_id: Optional[str] = None
    question: str
    image_name: Optional[str] = None


class Response(BaseModel):
    response: Union[str, dict]


bot = TIGAgentFactory(parameters).load()
instance = InstanceManager()

@router.post("/chatbot/main", response_class=StreamingResponse)
async def main_chatbot(request: Request, message: Message):
    auth_header = request.headers.get("Authorization")
    user_id = get_user_id(auth_header) if auth_header else None
    session_id = message.session_id or str(uuid.uuid4())  # session_id가 없으면(첫 대화) 새 uuid를 생성
    
    logger.info("Request received for main_chatbot", user_id=user_id, session_id=session_id, message=message)
    
    memory = instance.get_instance(session_id, user_id)
    
    result = bot.run(memory, message.question, message.image_name)
    
    return StreamingResponse(result, media_type='text/event-stream')