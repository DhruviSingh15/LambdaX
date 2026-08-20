from backend.scheduler.base_policy import SchedulingPolicy

class ThresholdPolicy(SchedulingPolicy):
    def on_request_arrival(self, func: dict, current_queue_length: int, pool_manager) -> None:
        """
        Check if current_queue_length > queue_threshold.
        If so, proactively provision a new container if below max_containers.
        """
        queue_threshold = func.get('queue_threshold', 0)
        if current_queue_length > queue_threshold:
            # We must be careful not to exceed max_containers,
            # which pool_manager.provision_async should check.
            pool_manager.provision_async(func['name'])
        
    def on_background_monitor(self, func: dict, pool_manager) -> None:
        """
        If queue builds up slowly or continuously stays above threshold,
        the background monitor can also trigger provisions.
        """
        queue_threshold = func.get('queue_threshold', 0)
        current_queue_length = pool_manager.get_current_queue_length(func['id'])
        
        if current_queue_length > queue_threshold:
            pool_manager.provision_async(func['name'])
        
    def can_reap(self, func: dict, container_record: dict, current_pool_size: int, pool_manager=None) -> bool:
        """
        Threshold policy uses max_warm_containers as the baseline.
        """
        target_warm = func.get('max_warm_containers', 0)
        return current_pool_size > target_warm
