import json
from types import SimpleNamespace
import unittest
from host import UserError, load_contract


class CampaignTest(unittest.TestCase):
    def setUp(self):
        self.owner = "0x" + "1" * 40
        self.sender = SimpleNamespace(sender_address=self.owner)
        self.items = {
            1:dict(id=1, open=False, changes_count=3, min_lat=0.5, min_lon=0, max_lat=1, max_lon=1),
            2:dict(id=2, open=False, changes_count=2, min_lat=0, min_lon=0, max_lat=1, max_lon=1),
            3:dict(id=3, open=False, changes_count=1, min_lat=0, min_lon=0, max_lat=1.0000001, max_lon=1),
        }
        self.contract = load_contract("map_review_budget.py", "MapReviewBudget", self.fetch, self.sender)
        self.contract.open_campaign("scope", 0, 0, 10000000, 10000000, 4)

    def fetch(self, url):
        item = self.items.get(int(url.rsplit("/", 1)[-1].removesuffix(".json")))
        return SimpleNamespace(status=200 if item else 404, body=json.dumps({"changeset":item}))

    def campaign(self):
        return json.loads(self.contract.read_campaign(self.owner, "scope"))

    def test_boundary_and_capacity(self):
        for id, expected in [(1, "ADMITTED"), (2, "OVER_BUDGET"), (3, "OUT_OF_AREA")]:
            self.contract.submit_changeset("scope", id)
            decision = json.loads(self.contract.read_decision(self.owner, "scope", id))
            self.assertEqual(decision["outcome"], expected)
        self.assertEqual(self.campaign()["remaining"], 1)
        self.assertEqual(self.campaign()["admitted"], [1])

    def test_replay_and_close(self):
        self.contract.submit_changeset("scope", 1)
        with self.assertRaisesRegex(UserError, "CHANGESET_ALREADY_EVALUATED"):
            self.contract.submit_changeset("scope", 1)
        self.contract.close_campaign("scope")
        with self.assertRaisesRegex(UserError, "CAMPAIGN_CLOSED"):
            self.contract.submit_changeset("scope", 2)
        self.assertEqual(self.campaign()["status"], "CLOSED")
        self.assertEqual(self.campaign()["remaining"], 1)

    def test_open_and_malformed_records_do_not_spend(self):
        self.items[1]["open"] = True
        with self.assertRaisesRegex(UserError, "CHANGESET_NOT_CLOSED"):
            self.contract.submit_changeset("scope", 1)
        self.items[1].update(open=False, min_lon=None)
        with self.assertRaisesRegex(UserError, "INVALID_CHANGESET_RECORD"):
            self.contract.submit_changeset("scope", 1)
        with self.assertRaisesRegex(UserError, "CHANGESET_SOURCE_UNAVAILABLE"):
            self.contract.submit_changeset("scope", 99)
        self.assertEqual(self.campaign()["remaining"], 4)
        self.assertEqual(self.contract.read_decision(self.owner, "scope", 1), "")

    def test_other_wallet_cannot_spend_or_close(self):
        self.sender.sender_address = "0x" + "2" * 40
        with self.assertRaisesRegex(UserError, "CAMPAIGN_NOT_FOUND"):
            self.contract.submit_changeset("scope", 1)
        with self.assertRaisesRegex(UserError, "CAMPAIGN_NOT_FOUND"):
            self.contract.close_campaign("scope")
