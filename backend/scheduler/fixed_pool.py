from backend.scheduler.base_policy import SchedulingPolicy

class FixedPoolPolicy(SchedulingPolicy):
    def on_request_arrival(self, func: dict, current_queue_length: int, pool_manager) -> None:
        """
        Fixed pool relies on background monitor to maintain pool.
        However, if request arrival needs it, standard allocation takes over.
        """
        pass
        
    def on_background_monitor(self, func: dict, pool_manager) -> None:
        """
        Ensures min_containers are always provisioned.
        """
        min_containers = func.get('min_containers', 0)
        if min_containers <= 0:
            return
            
        current_valid = pool_manager.get_valid_container_count(func['id'])
        if current_valid < min_containers:
            # Provision missing containers
            missing = min_containers - current_valid
            for _ in range(missing):
                pool_manager.provision_async(func['name'])
        
    def can_reap(self, func: dict, container_record: dict, current_pool_size: int, pool_manager=None) -> bool:
        """
        Fixed pool never reaps as long as it's at or below max_warm_containers.
        """
        target = func.get('max_warm_containers', 0)
        return current_pool_size > target
