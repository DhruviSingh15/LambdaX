from abc import ABC, abstractmethod

class SchedulingPolicy(ABC):
    @abstractmethod
    def on_request_arrival(self, func: dict, current_queue_length: int, pool_manager) -> None:
        """
        Called when a request arrives, before allocation.
        """
        pass
        
    @abstractmethod
    def on_background_monitor(self, func: dict, pool_manager) -> None:
        """
        Called periodically by a background daemon.
        """
        pass
        
    @abstractmethod
    def can_reap(self, func: dict, container_record: dict, current_pool_size: int, pool_manager=None) -> bool:
        """
        Returns True if the container is allowed to be reaped.
        """
        pass
