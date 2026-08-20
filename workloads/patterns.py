from abc import ABC, abstractmethod
import time
import math
import numpy as np

class WorkloadPattern(ABC):
    def __init__(self, duration_seconds: int):
        self.duration_seconds = duration_seconds
        
    @abstractmethod
    def get_requests_per_second(self, elapsed_time: float) -> int:
        """Returns the number of requests to fire at this exact second."""
        pass

class ConstantWorkload(WorkloadPattern):
    def __init__(self, duration_seconds: int, rps: int):
        super().__init__(duration_seconds)
        self.rps = rps

    def get_requests_per_second(self, elapsed_time: float) -> int:
        if elapsed_time > self.duration_seconds:
            return 0
        return self.rps

class BurstyWorkload(WorkloadPattern):
    def __init__(self, duration_seconds: int, baseline_rps: int, burst_rps: int, burst_duration_seconds: int, burst_interval_seconds: int):
        super().__init__(duration_seconds)
        self.baseline_rps = baseline_rps
        self.burst_rps = burst_rps
        self.burst_duration_seconds = burst_duration_seconds
        self.burst_interval_seconds = burst_interval_seconds
        self.cycle_length = self.burst_interval_seconds + self.burst_duration_seconds

    def get_requests_per_second(self, elapsed_time: float) -> int:
        if elapsed_time > self.duration_seconds:
            return 0
        
        # Calculate where we are in the current cycle
        cycle_position = elapsed_time % self.cycle_length
        
        if cycle_position < self.burst_interval_seconds:
            return self.baseline_rps
        else:
            return self.burst_rps

class PeriodicWorkload(WorkloadPattern):
    def __init__(self, duration_seconds: int, min_rps: int, max_rps: int, period_seconds: int):
        super().__init__(duration_seconds)
        self.min_rps = min_rps
        self.max_rps = max_rps
        self.period_seconds = period_seconds

    def get_requests_per_second(self, elapsed_time: float) -> int:
        if elapsed_time > self.duration_seconds:
            return 0
            
        # Using a sine wave starting at the bottom (-pi/2) to smoothly oscillate
        normalized_sin = (math.sin((elapsed_time * 2 * math.pi / self.period_seconds) - (math.pi / 2)) + 1) / 2
        rps = self.min_rps + (self.max_rps - self.min_rps) * normalized_sin
        return int(round(rps))

class PoissonWorkload(WorkloadPattern):
    def __init__(self, duration_seconds: int, lam: float):
        super().__init__(duration_seconds)
        self.lam = lam

    def get_requests_per_second(self, elapsed_time: float) -> int:
        if elapsed_time > self.duration_seconds:
            return 0
            
        # Draw from a Poisson distribution where lambda (lam) is the expected requests per second
        return np.random.poisson(self.lam)
