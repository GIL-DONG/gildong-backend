from typing import Optional

from core import common_parameters
from services import MemoryManagerFactory


class InstanceManager:
    
    def __init__(self):
        self.memory = MemoryManagerFactory(common_parameters)
        self.instances = {}
        self.user_statuses = {}

    def get_instance(self, session_id, user_id: Optional[str] = None):
        if (session_id in self.user_statuses and self.user_statuses[session_id] != user_id) or session_id not in self.instances:
            memory_manager = self.memory.load(session_id, user_id)
            self.instances[session_id] = memory_manager
            self.user_statuses[session_id] = user_id
        
        return self.instances[session_id]