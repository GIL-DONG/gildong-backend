from toolva import Toolva

from core.common_config import common_parameters


class SingletonRetriever:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonRetriever, cls).__new__(cls)
            cls._instance.initialize_retriever()
        return cls._instance

    def initialize_retriever(self):
        self.retriever = Toolva(
            tool="semantic_search",
            src="es",
            model={
                "host_n": common_parameters.get("elasticsearch_host"),
                "http_auth": None,
                "encoder_key": {
                    "src": common_parameters.get("embedding_src"),
                    "model": common_parameters.get("embedding_model")
                }
            },
            async_mode=True
        )
        
    def get_retriever(self):
        return self.retriever