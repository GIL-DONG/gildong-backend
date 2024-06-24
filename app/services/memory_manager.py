import pytz
from datetime import datetime
from collections import defaultdict

import structlog
from toolva import Toolva
from toolva.utils import TokenLimiter

from services import ElasticsearchDataManager


logger = structlog.get_logger()


class MemoryManagerFactory:
    
    def __init__(self, config: dict):
        self.config = config
        logger.info("Initializing MemoryManagerFactory with given configuration")
        self._setup()

    def _setup(self):
        tokenizer = Toolva(
            tool="tokenization", 
            src=self.config.get("memory_tokinizer_src", "tiktoken"), 
            model=self.config.get("memory_tokinizer_model", "cl100k_base")
        )
        self.token_limiter = TokenLimiter(tokenizer=tokenizer, max_tokens=self.config.get("history_max_tokens", 1000))
        
        self.db = ElasticsearchDataManager(self.config.get("elasticsearch_host"))
        
        logger.info("Setting up MemoryManagerFactory with tokenizer and database configurations")
    
    def load(self, session_id, user_id):
        logger.info("Loading MemoryManager", session_id=session_id, user_id=user_id)
        return MemoryManager(
            db=self.db,
            index_n=self.config.get("memory_index_name"),
            token_limiter=self.token_limiter,
            session_id=session_id,
            user_id=user_id,
            user_info=self.db.fetch_userinfo(self.config.get("user_index_name"), user_id) if user_id else None
        )


class MemoryManager:

    def __init__(
        self, 
        db, 
        index_n, 
        token_limiter, 
        session_id, 
        user_id, 
        user_info=None
    ):
        logger.info("Initializing MemoryManager", user_id=user_id, session_id=session_id)
        
        self.db = db
        self.index_n = index_n
        self.token_limiter = token_limiter
        self.session_id = session_id
        self.user_id = user_id
        self.user_info = user_info
        
        self.korea_time = pytz.timezone('Asia/Seoul')
        
        self._load_data_from_db()
    
    def _load_data_from_db(self):
        logger.info("Loading conversation memory from DB", index_n=self.index_n, session_id=self.session_id)
        
        memory = self.db.fetch_memory(
            index_n=self.index_n,
            session_id=self.session_id
        )
        
        self.data = defaultdict(list)
        self.turn = 0
        history = []

        if memory:
            latest_turn = memory[-1]  # memory의 마지막 요소가 가장 최근 값
            
            self.turn = latest_turn.get("turn_id", 0)
            
            self.data['travel_info'] = latest_turn.get("travel_info", {})
            self.data['user_message'] = latest_turn.get("user_message", "")
            self.data['ai_message'] = latest_turn.get("ai_message", "")
            self.data['formatted_ai_message'] = latest_turn.get("formatted_ai_message", "")
            self.data['input_data'] = latest_turn.get("input_data", [])

            # itinerary_section 불러오기
            for data in reversed(memory):  # memory를 역순으로 반복하여 최근 데이터부터 확인
                if data.get("itinerary"):
                    self.data['itinerary_section'] = data.get("itinerary").get("itinerary_section", "")
                    self.data['itinerary_schedule'] = data.get("itinerary").get("schedule", [])
                    break
            
            # history 불러오기
            total_tokens = 0
            for data in reversed(memory[:-1]):  # 가장 최근 데이터를 제외한 memory를 역순으로 반복하여 최근 데이터부터 확인
                if data.get("summary"):
                    summary = data.get("summary")
                    summary_tokens = data.get("summary_tokens")
                    if total_tokens + summary_tokens <= self.token_limiter.max_tokens:
                        history.insert(0, summary)  # 오래된 summary부터 리스트에 추가
                        total_tokens += summary_tokens
                    else:
                        break
                else:
                    continue
        
        self.data["history"] = history
    
    def index_data(self, data, summary: str = None):
        logger.info("Indexing data", user_id=self.user_id, turn=self.turn, data=data)
        
        self.turn += 1
        
        data["user_id"] = self.user_id
        data["session_id"] = self.session_id
        data["turn_id"] = self.turn
        data["timestamp"] = datetime.now(self.korea_time).strftime('%Y-%m-%dT%H:%M:%S')

        # Index new data
        doc_id = f"{self.session_id}-{self.turn}"  # doc_id 생성
        self.db.index_memory(index_n=self.index_n, doc_id=doc_id, data=data)

        self.data["travel_info"] = data.get("travel_info", self.data.get("travel_info"))
        self.data["user_message"] = data.get("user_message")
        self.data["ai_message"] = data.get("ai_message")
        self.data['formatted_ai_message'] = data.get("formatted_ai_message")
        self.data["input_data"] = data.get("input_data")
        self.data["itinerary_section"] = data.get("itinerary", {}).get("itinerary_section", self.data.get("itinerary_section"))
        self.data["itinerary_schedule"] = data.get("itinerary", {}).get("schedule", self.data.get("itinerary_schedule"))
        
        # if summary
        if summary:
            self.data["history"].append(summary)
            logger.info("Appending summary to the history", summary=self.data["history"])
            
            if self.user_info:
                doc_id = f"{self.session_id}-{self.turn - 1}"  # doc_id 생성
                self.db.update_summary(
                    index_n=self.index_n, 
                    doc_id=doc_id, 
                    summary=summary,
                    summary_tokens=self.token_limiter.token_counter(summary)
                )
            
            if self.data["history"]:
                limited_formatted_data_list = self.token_limiter.cutoff(self.data["history"])
                logger.info(f"Number of items has been limited. Original: {len(self.data['history'])}, Now: {len(limited_formatted_data_list)}")
                self.data["history"] = limited_formatted_data_list
    
    def get_data(self):
        # If data is not available in memory, fetch it from the database.
        if not self.data:
            self._load_data_from_db()
            logger.info("Fetching data", user_id=self.user_id, session_id=self.session_id)
        
        self.data["user_info"] = self.user_info
        return self.data