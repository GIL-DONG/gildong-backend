from core import common_parameters


parameters = {
    **common_parameters,
    "convo_index": "gildong_convo",
    "itinerary_index": "gildong_confirmed_itinerary", 
    "source_fields": [
        "user_id",
        "session_id",
        "itinerary",
        "timestamp"
    ]
}