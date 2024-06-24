from core import common_parameters


parameters = {
    **common_parameters,
    "index_name": "gildong_1", 
    "source_fields": [
        "title",
        "overview",
        "contenttypeid",
        "addr",
        "tel",
        "zipcode",
        "url",
        "physical",
        "visual",
        "hearing"
    ]
}