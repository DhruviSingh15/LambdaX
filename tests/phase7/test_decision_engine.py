import unittest
from unittest.mock import patch
from backend.scheduler.adaptive.decision_engine import DecisionEngine
from backend.scheduler.adaptive.action import DecisionAction

class TestDecisionEngine(unittest.TestCase):
    def setUp(self):
        # We patch DB calls so they don't hit the real DB during isolated unit tests
        self.patcher = patch('backend.scheduler.adaptive.priority_engine.db.execute_read_one')
        self.mock_db = self.patcher.start()

        def mock_read_one(query, params):
            if "avg_cold" in query:
                return {'avg_cold': 1000.0, 'avg_warm': 100.0}
            elif "avg_exec" in query:
                return {'avg_exec': 100.0}
            return {}

        self.mock_db.side_effect = mock_read_one

        self.engine = DecisionEngine()
        
        self.base_func = {
            'id': 1,
            'name': 'test_func',
            'max_containers': 5,
            'min_containers': 0,
            'memory_mb': 128,
            'sla_ms': 1000
        }

    def tearDown(self):
        self.patcher.stop()

    def test_micro_queue_decision(self):
        # Capacity exists but is completely busy. SLA is 1000ms.
        # Queue length = 2. Expected wait = 2 * 100 = 200ms.
        # Margin = 1000 - 200 = 800ms. Large positive margin!
        # Cost model evaluates: Prewarm cost vs SLA wait. Should pick wait.
        decision = self.engine.evaluate_arrival(
            func=self.base_func, 
            current_queue_length=2, 
            current_containers=3, # Not at max
            idle_containers=0, 
            predicted_demand=5.0
        )
        self.assertEqual(decision.action, DecisionAction.MICRO_QUEUE)
        self.assertEqual(decision.target_containers, 3)

    def test_emergency_reactive_decision(self):
        # SLA is 1000ms. Queue length = 12. Expected wait = 1200ms.
        # Margin = -200ms. Violated!
        # Must provision immediately.
        decision = self.engine.evaluate_arrival(
            func=self.base_func, 
            current_queue_length=12, 
            current_containers=2, 
            idle_containers=0, 
            predicted_demand=5.0
        )
        self.assertEqual(decision.action, DecisionAction.EMERGENCY_REACTIVE)
        self.assertEqual(decision.target_containers, 3)

    def test_maintain_warm_arrival(self):
        # Idle containers exist!
        decision = self.engine.evaluate_arrival(
            func=self.base_func, 
            current_queue_length=0, 
            current_containers=2, 
            idle_containers=1, 
            predicted_demand=5.0
        )
        self.assertEqual(decision.action, DecisionAction.MAINTAIN_WARM)

    def test_reclaim_background(self):
        # Low predicted demand, we have 4 containers but only need 1.
        decision = self.engine.evaluate_background(
            func=self.base_func,
            current_containers=4,
            valid_containers=4,
            idle_containers=3,
            predicted_demand=5.0 # demand 5 RPS * 0.1s = 0.5 -> desired 1 container
        )
        self.assertEqual(decision.action, DecisionAction.RECLAIM)
        self.assertEqual(decision.target_containers, 1)

    def test_prewarm_background(self):
        # High predicted demand! Need 3 containers but we have 1.
        decision = self.engine.evaluate_background(
            func=self.base_func,
            current_containers=1,
            valid_containers=1,
            idle_containers=0,
            predicted_demand=30.0 # 30 RPS * 0.1s = 3 desired containers
        )
        self.assertEqual(decision.action, DecisionAction.PREWARM)
        self.assertEqual(decision.target_containers, 3)

if __name__ == '__main__':
    unittest.main()
