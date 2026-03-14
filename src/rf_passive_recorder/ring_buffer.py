from __future__ import annotations

import threading

import numpy as np


class ComplexRingBuffer:
    def __init__(self, sample_rate_sps: int, ring_buffer_ms: int):
        self.capacity = int(sample_rate_sps * ring_buffer_ms / 1000)
        self._buf = np.zeros(self.capacity, dtype=np.complex64)
        self._write = 0
        self._count = 0
        self._dropped_chunks = 0
        self._lock = threading.Lock()

    @property
    def dropped_chunks(self) -> int:
        return self._dropped_chunks

    def append(self, samples: np.ndarray) -> None:
        arr = np.asarray(samples, dtype=np.complex64)
        n = len(arr)
        with self._lock:
            if n >= self.capacity:
                self._buf[:] = arr[-self.capacity :]
                self._write = 0
                self._count = self.capacity
                self._dropped_chunks += 1
                return
            end = self._write + n
            if end <= self.capacity:
                self._buf[self._write : end] = arr
            else:
                pivot = self.capacity - self._write
                self._buf[self._write :] = arr[:pivot]
                self._buf[: n - pivot] = arr[pivot:]
            self._write = end % self.capacity
            self._count = min(self.capacity, self._count + n)

    def snapshot_last(self, sample_count: int) -> tuple[np.ndarray, bool]:
        with self._lock:
            actual = min(sample_count, self._count)
            dropped = actual < sample_count
            start = (self._write - actual) % self.capacity
            if actual == 0:
                return np.zeros(0, dtype=np.complex64), True
            if start + actual <= self.capacity:
                out = self._buf[start : start + actual].copy()
            else:
                out = np.concatenate((self._buf[start:], self._buf[: (start + actual) % self.capacity])).copy()
            return out, dropped
