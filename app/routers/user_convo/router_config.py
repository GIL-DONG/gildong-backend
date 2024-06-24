from core import common_parameters


parameters = {
    **common_parameters,
    "index_name": "gildong_convo", 
    "source_fields": [
        "turn_id",
        "timestamp",
        "user_message",
        "formatted_ai_message",
        "image_name"
    ]
}