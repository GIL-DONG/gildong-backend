import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

parameters = {
    "planner_ai_model": "gpt-4-0613",
    "planner_template": os.path.join(BASE_DIR, "strategy_planner.json"),
    "planner_max_tokens": 256,
    "planner_temperature": 0.,
    "planner_top_p": 1.0,
    "planner_frequency_penalty": 0., 
    "planner_presence_penalty": 0.,
    "first_message": (
        "안녕하세요 AI 여행 플래너 '길동이'입니다. "
        "가고 싶은 여행지나 이번 여행에서 즐기고 싶은 특별한 테마가 있다면 말씀해주세요!"
    ),
    "generator_ai_model": "gpt-4-0613",
    "generator_template": os.path.join(BASE_DIR, "itinerary_generator.json"),
    "generator_max_tokens": 1500,
    "generator_temperature": 0.,
    "generator_top_p": 1.0,
    "generator_frequency_penalty": 0., 
    "generator_presence_penalty": 0., 
    "error_message": (
        "현재 시스템에 문제가 발생하여 정상적인 서비스 제공이 어렵습니다. "
        "잠시 후 다시 시도해 주시거나 다른 질문을 해주시기 바랍니다. "
        "불편을 드려 대단히 죄송합니다. 감사합니다."
    ),
    "image_retriever": {
        "url": "http://211.169.248.182:5043/search_image"
    },
    "travel_destination_retriever": {
        "index_name": "gildong_1", 
        "vector_field": "sbert_vector", 
        "max_tokens": 3500, 
        "key_field": "title", 
        "value_fields": [
            "contenttypeid", 
            "overview_summ", 
            "physical_en", 
            "visual_en", 
            "hearing_en"
        ],
        "source_fields": [
            "title", 
            "contenttypeid", 
            "overview_summ", 
            "physical_en", 
            "visual_en", 
            "hearing_en", 
            "location",
            "url"
        ]
    }
}