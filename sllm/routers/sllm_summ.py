from toolva import Toolva
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter()

log = structlog.get_logger()

class Message(BaseModel):
    user_message: str
    ai_message: str

class SllmSumm:
    _instance = None  # Singleton instance

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SllmSumm, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, tool="sllm", adaptor=["summ"], temperature=0.01, num_beams=5, no_repeat_ngram_size=5):
        if self._initialized:
            return
        self.temperature = temperature
        self.num_beams = num_beams
        self.no_repeat_ngram_size = no_repeat_ngram_size
        self._setup(tool, adaptor)
        self._initialized = True

    def _setup(self, tool, adaptor):
        self.sllm = Toolva(tool=tool, adaptor=adaptor)

    def load(self, user_message, ai_message):
        input_data = f"-user: {user_message}\n-chatbot: {ai_message}"
        try:
            return self.sllm["summ"](input=input_data, 
                                     temperature=self.temperature, 
                                     num_beams=self.num_beams, 
                                     no_repeat_ngram_size=self.no_repeat_ngram_size)
        except Exception as e:
            log.error("Failed to load model", exception=str(e))
            raise HTTPException(status_code=500, detail="Failed to process the request")

model_instance = SllmSumm()

# Include Routers
@router.post("/sllm/summ")
async def sllm_summ(message: Message):
    try:
        return model_instance.load(message.user_message, message.ai_message)
    except HTTPException as e:
        log.error("API error", status_code=e.status_code, detail=e.detail)
        raise e
