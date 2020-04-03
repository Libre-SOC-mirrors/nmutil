class StepLimiter:
    def __init__(self, limit=100000):
        self.limit = limit
        self.step_count = 0
        assert self.step_count < self.limit, "step count limit reached"

    def step(self):
        self.step_count += 1
        assert self.step_count < self.limit, "step count limit reached"

    def __iter__(self):
        return self

    def __next__(self):
        self.step()
        return None
