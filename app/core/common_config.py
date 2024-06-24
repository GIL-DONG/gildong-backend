import os

from dotenv import load_dotenv


load_dotenv()

common_parameters = {
    "secret_key": os.getenv('SECRET_KEY'),
    "algorithm": "HS256",
    "refresh_token_index_name": "refresh_tokens", 
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
    "GOOGLE_CSE_ID": os.getenv('GOOGLE_CSE_ID'),
    "GOOGLE_API_KEY": os.getenv('GOOGLE_API_KEY'),
    "weather_url" : "https://apihub.kma.go.kr/api/typ01/url/",
    "Weather_APP_KEY": os.getenv('Weather_APP_KEY'),
    "Kakao_APP_KEY": os.getenv('Kakao_APP_KEY'),
    "Kakao_local_APP_KEY": os.getenv('Kakao_local_APP_KEY'),
}