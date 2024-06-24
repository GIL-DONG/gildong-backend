from core import common_parameters


parameters = {
    **common_parameters,
    "index_name": "gildong_user",
    "source_fields": [
        "userID",
        "user_name",
        "user_photo"
    ]
}