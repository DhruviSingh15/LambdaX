from backend.scheduler.base_policy import SchedulingPolicy

class ReactivePolicy(SchedulingPolicy):
    def on_request_arrival(self, func: dict, current_queue_length: int, pool_manager) -> None:
        """
        Reactive does nothing proactively.
        """
        pass
        
    def on_background_monitor(self, func: dict, pool_manager) -> None:
        """
        Reactive does nothing in the background.
        """
        pass
        
    def can_reap(self, func: dict, container_record: dict, current_pool_size: int, pool_manager=None) -> bool:
        """
        Reactive allows reaping any idle container that exceeded timeout.
        """
        return True
