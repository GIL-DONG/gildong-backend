from toolva.utils import ChatSummarizer

from core.common_config import common_parameters


class SingletonSummarizer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonSummarizer, cls).__new__(cls)
            cls._instance.initialize_summarizer()
        return cls._instance

    def initialize_summarizer(self):
        self.summarizer = ChatSummarizer(
            max_tokens=common_parameters.get("summary_max_tokens", 256),
            async_mode=True
        )
        
    def get_summarizer(self):
        return self.summarizer