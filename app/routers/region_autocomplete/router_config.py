from core import common_parameters


parameters = {
    **common_parameters,
    "index_name": "gildong_auto_2",
    "source_fields": [
        "city^3",
        "district",
    ]
}