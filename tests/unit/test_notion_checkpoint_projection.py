import unittest

from nexus_sandbox.notion_checkpoint_projection import Checkpoint, NotionCheckpointProjection


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.checkpoint = Checkpoint("event-1", "journal-1", "HOLD",
                                     "https://github.com/example/run/1", "abc123", "Reconcile")
        self.records = {}
        self.creates = []
        def lookup(key):
            return self.records.get(key)
        def create(key, digest, body):
            self.creates.append(key)
            self.records[key] = {"digest": digest, "body": body}
        self.lookup, self.create = lookup, create

    def test_disabled_never_reads_or_writes(self):
        def forbidden(*args):
            raise AssertionError("Must not invoke host")
        projection = NotionCheckpointProjection(find_exact=forbidden, create=forbidden)
        self.assertEqual(projection.publish(self.checkpoint), "DISABLED")

    def test_create_readback_and_replay(self):
        projection = NotionCheckpointProjection(find_exact=self.lookup,
                                                create=self.create, enabled=True)
        self.assertEqual(projection.publish(self.checkpoint), "VERIFIED")
        self.assertEqual(projection.publish(self.checkpoint), "VERIFIED")
        self.assertEqual(self.creates, ["event-1"])

    def test_lost_ack_does_not_blind_retry(self):
        def lost_ack(key, digest, body):
            self.create(key, digest, body)
            raise TimeoutError("ack lost")
        projection = NotionCheckpointProjection(find_exact=self.lookup,
                                                create=lost_ack, enabled=True)
        self.assertEqual(projection.publish(self.checkpoint), "HOLD")
        self.assertEqual(projection.publish(self.checkpoint), "VERIFIED")
        self.assertEqual(self.creates, ["event-1"])

    def test_conflict_holds(self):
        self.records["event-1"] = {"digest": "other"}
        projection = NotionCheckpointProjection(find_exact=self.lookup,
                                                create=self.create, enabled=True)
        self.assertEqual(projection.publish(self.checkpoint), "HOLD")
        self.assertEqual(self.creates, [])

    def test_outage_raises_instead_of_treating_as_absence(self):
        def outage(key):
            raise ConnectionError("Notion unavailable")
        projection = NotionCheckpointProjection(find_exact=outage,
                                                create=self.create, enabled=True)
        with self.assertRaises(ConnectionError):
            projection.publish(self.checkpoint)
        self.assertEqual(self.creates, [])


if __name__ == "__main__":
    unittest.main()
