import time
import math
from backend.scheduler.mpc.mpc_config import MPCConfig
from backend.scheduler.mpc.mpc_state import MPCState
from backend.scheduler.mpc.mpc_actions import MPCAction, MPCActionType
from backend.scheduler.adaptive.decision import Decision
from backend.scheduler.adaptive.action import DecisionAction

class MPCController:
    def __init__(self, config: MPCConfig):
        self.config = config
        
    def _generate_candidate_actions(self, current_warm: int, max_containers: int) -> list[MPCAction]:
        actions = [MPCAction(MPCActionType.MAINTAIN)]
        
        max_prewarm = min(self.config.max_prewarm_per_step, self.config.max_start_rate)
        max_possible = max(0, max_containers - current_warm)
        for i in range(1, min(max_prewarm, max_possible) + 1):
            actions.append(MPCAction(MPCActionType.PREWARM, i))
            
        for i in range(1, 3):
            actions.append(MPCAction(MPCActionType.RECLAIM, i))
            
        return actions

    def optimize_action(self, state: MPCState) -> Decision:
        best_cost = float('inf')
        best_action = MPCAction(MPCActionType.MAINTAIN)
        
        # DFS function
        def dfs(depth, current_warm, current_queue, accumulated_cost, first_action):
            nonlocal best_cost, best_action
            
            if depth == self.config.horizon:
                if accumulated_cost < best_cost:
                    best_cost = accumulated_cost
                    best_action = first_action
                return
                
            if accumulated_cost >= best_cost:
                return
                
            # If predictor didn't provide enough steps, pad with 0
            demand_rps = state.predicted_demand[depth] if depth < len(state.predicted_demand) else 0.0
            
            actions = self._generate_candidate_actions(current_warm, state.max_containers)
            for action in actions:
                next_warm = current_warm
                if action.action_type == MPCActionType.PREWARM:
                    next_warm = min(state.max_containers, current_warm + action.count)
                elif action.action_type == MPCActionType.RECLAIM:
                    idle = max(0, current_warm - state.busy_containers)
                    reclaimed = min(action.count, idle)
                    next_warm = current_warm - reclaimed
                    
                # Capacity this step
                if state.estimated_execution_latency > 0:
                    # latency is in ms, convert to seconds
                    exec_sec = state.estimated_execution_latency / 1000.0
                    capacity = next_warm * (self.config.step_seconds / exec_sec)
                else:
                    capacity = next_warm * 10.0 # fallback
                
                incoming = demand_rps * self.config.step_seconds
                total_work = current_queue + incoming
                
                if total_work > capacity:
                    next_queue = total_work - capacity
                else:
                    next_queue = 0
                    
                cost_c = next_warm * self.config.step_seconds
                
                if next_queue > 0:
                    if capacity > 0:
                        avg_queue_time = (next_queue / capacity) * self.config.step_seconds
                    else:
                        # infinite queue time if no containers
                        avg_queue_time = next_queue * self.config.step_seconds * 100 
                else:
                    avg_queue_time = 0
                    
                latency_l = avg_queue_time * 1000 + state.estimated_execution_latency * 1000
                sla_v = max(0, latency_l - state.sla_target)
                queue_q = next_queue
                
                step_cost = (
                    self.config.cost_weight * cost_c +
                    self.config.latency_weight * latency_l +
                    self.config.sla_weight * sla_v +
                    self.config.queue_weight * queue_q
                )
                
                next_first_action = first_action if depth > 0 else action
                
                dfs(depth + 1, next_warm, next_queue, accumulated_cost + step_cost, next_first_action)

        dfs(0, state.warm_containers, state.queued_requests, 0, MPCAction(MPCActionType.MAINTAIN))
        
        target = state.warm_containers
        dec_action = DecisionAction.MAINTAIN_WARM
        
        if best_action.action_type == MPCActionType.PREWARM:
            target = state.warm_containers + best_action.count
            dec_action = DecisionAction.PREWARM
        elif best_action.action_type == MPCActionType.RECLAIM:
            target = max(state.busy_containers, state.warm_containers - best_action.count)
            dec_action = DecisionAction.RECLAIM
            
        predicted_demand = state.predicted_demand[0] if state.predicted_demand else 0.0
            
        return Decision(
            action=dec_action,
            target_containers=target,
            reason="Lowest predicted cost under MPC trajectory search",
            confidence=1.0,
            predicted_demand=predicted_demand,
            sla_margin=0.0,
            expected_wait_ms=0.0,
            estimated_cost=best_cost,
            timestamp=time.time()
        )
