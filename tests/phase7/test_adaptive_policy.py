import unittest
from unittest.mock import MagicMock, patch
from backend.scheduler.adaptive.adaptive_policy import AdaptivePolicy
from backend.scheduler.adaptive.action import DecisionAction

class TestAdaptivePolicy(unittest.TestCase):
    def setUp(self):
        # Patch DB to prevent real writes during tests
        self.patcher_db = patch('backend.scheduler.adaptive.adaptive_policy.db')
        self.mock_db = self.patcher_db.start()
        
        self.mock_predictor = MagicMock()
        self.mock_predictor.predict.return_value = 5.0
        self.policy = AdaptivePolicy(predictor=self.mock_predictor)
        
        self.mock_pool_manager = MagicMock()
        self.mock_pool_manager.get_container_count.return_value = 2
        self.mock_pool_manager.get_idle_container_count.return_value = 1
        self.mock_pool_manager.get_valid_container_count.return_value = 2

        self.func = {
            'id': 1,
            'name': 'test_func',
            'max_containers': 5,
            'min_containers': 0,
            'memory_mb': 128,
            'sla_ms': 1000
        }

    def tearDown(self):
        self.patcher_db.stop()

    def test_on_request_arrival(self):
        # With idle containers, it should maintain warm
        self.policy.decision_engine.evaluate_arrival = MagicMock()
        self.policy.decision_engine.evaluate_arrival.return_value.action = DecisionAction.MAINTAIN_WARM
        
        action = self.policy.on_request_arrival(self.func, queue_length=0, pool_manager=self.mock_pool_manager)
        
        self.assertEqual(action, DecisionAction.MAINTAIN_WARM)
        self.assertTrue(self.mock_db.execute_write.called)

    def test_fallback_on_exception(self):
        # If decision engine throws exception, should fallback to EMA behavior
        self.policy.decision_engine.evaluate_arrival = MagicMock(side_effect=Exception("Test Error"))
        
        # Mock predictor to say we need 3 containers, but we have 2, so it should SCALE_UP
        self.policy.predictor_manager.get_desired_capacity = MagicMock(return_value=3)
        
        action = self.policy.on_request_arrival(self.func, queue_length=0, pool_manager=self.mock_pool_manager)
        
        self.assertEqual(action, DecisionAction.SCALE_UP)

    def test_on_background_monitor_prewarm(self):
        self.policy.decision_engine.evaluate_background = MagicMock()
        mock_decision = MagicMock()
        mock_decision.action = DecisionAction.PREWARM
        mock_decision.target_containers = 4
        self.policy.decision_engine.evaluate_background.return_value = mock_decision
        
        self.policy.on_background_monitor(self.func, self.mock_pool_manager)
        
        # Valid is 2, Target is 4, Shortage is 2. Should call provision_async twice.
        self.assertEqual(self.mock_pool_manager.provision_async.call_count, 2)

    def test_can_reap(self):
        self.policy.decision_engine.evaluate_background = MagicMock()
        mock_decision = MagicMock()
        mock_decision.action = DecisionAction.RECLAIM
        mock_decision.target_containers = 1 # Target 1, Valid 2 -> Can reap
        self.policy.decision_engine.evaluate_background.return_value = mock_decision
        
        can = self.policy.can_reap({}, self.func, self.mock_pool_manager)
        self.assertTrue(can)

if __name__ == '__main__':
    unittest.main()
