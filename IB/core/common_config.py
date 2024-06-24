import os

from dotenv import load_dotenv


load_dotenv()

common_parameters = {
    "secret_key": os.getenv('SECRET_KEY'),
    "algorithm": "HS256",
    "refresh_token_index_name":  "refresh_tokens", 
    "elasticsearch_host": "http://211.169.248.182:12900/", 
    "embedding_src": "drive", 
    "embedding_model": "sts.klue/roberta-large.klue-nli_klue-sts.bi-nli-sts", 
    "user_index_name":  "gildong_user", 
    "memory_index_name": "gildong_convo", 
    "memory_tokinizer_src": "tiktoken", 
    "memory_tokinizer_model": "cl100k_base", 
    "summary_max_tokens": 256, 
    "history_max_tokens": 1000,
    "kakao_app_key" : os.getenv('KAKAO_APP_KEY'),
    "kakao_admin_key" : os.getenv('KAKAO_ADMIN_KEY'),
    "KAKAO_USER_INFO_URL" : "https://kapi.kakao.com/v2/user/me",
    "KAKAO_CALENDAR_URL" : "https://kapi.kakao.com/v2/api/calendar/create/event",
}