"""Offline CP09 tests; assertions do not establish real Cortex fencing."""
import threading
import unittest
from nexus_sandbox.cp09_fencing_model import Fenced, SyntheticFencedStore

class TestCP09SyntheticFencing(unittest.TestCase):
    def test_takeover_rejects_stale_writer(self):
        s = SyntheticFencedStore()
        old = s.acquire()
        new = s.acquire()
        with self.assertRaises(Fenced):
            s.write(old, 0, "old", "stale")
        self.assertEqual(s.write(new, 0, "new", "fresh").value, "fresh")

    def test_delayed_old_writer_cannot_overwrite(self):
        s = SyntheticFencedStore()
        old = s.acquire()
        new = s.acquire()
        s.write(new, 0, "new", "winner")
        with self.assertRaises(Fenced):
            s.write(old, 0, "old", "loser")
        self.assertEqual(s.snapshot().value, "winner")

    def test_exact_retry_does_not_duplicate(self):
        s = SyntheticFencedStore()
        generation = s.acquire()
        first = s.write(generation, 0, "req", "payload")
        self.assertEqual(s.write(generation, 0, "req", "payload"), first)
        self.assertEqual(s.snapshot().version, 1)

    def test_conflicting_retry_rejected(self):
        s = SyntheticFencedStore()
        generation = s.acquire()
        s.write(generation, 0, "req", "payload")
        with self.assertRaises(Fenced):
            s.write(generation, 0, "req", "different")

    def test_version_conflict_rejected(self):
        s = SyntheticFencedStore()
        generation = s.acquire()
        s.write(generation, 0, "first", "one")
        with self.assertRaises(Fenced):
            s.write(generation, 0, "second", "two")

    def test_concurrent_takeover_one_generation_wins(self):
        s = SyntheticFencedStore()
        generations = []
        lock = threading.Lock()
        def acquire():
            g = s.acquire()
            with lock:
                generations.append(g)
        threads = [threading.Thread(target=acquire) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(timeout=3)
        self.assertEqual(len(set(generations)), 8)
        winner = max(generations)
        for g in generations:
            if g != winner:
                with self.assertRaises(Fenced):
                    s.write(g, 0, str(g), "stale")
        self.assertEqual(s.write(winner, 0, "winner", "ok").value, "ok")

if __name__ == "__main__":
    unittest.main()
