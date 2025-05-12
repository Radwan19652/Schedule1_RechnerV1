class CountdownTimer:
    """
    Unabhängiger Countdown: löst on_tick(rem) jede Sekunde aus,
    und on_finish() wenn 0 erreicht ist.
    """

    def __init__(self, root, total_seconds: int,
                 on_tick, on_finish):
        self.root = root
        self.total = int(total_seconds)
        self.remaining = self.total
        self.on_tick = on_tick
        self.on_finish = on_finish
        self._job = None

    def start(self):
        self._schedule_tick()

    def _schedule_tick(self):
        if self.remaining <= 0:
            self.on_tick(0)
            self.on_finish()
            return
        self.on_tick(self.remaining)
        self.remaining -= 1
        self._job = self.root.after(1000, self._schedule_tick)

    def stop(self):
        if self._job is not None:
            self.root.after_cancel(self._job)
            self._job = None
