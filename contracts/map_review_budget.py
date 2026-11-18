# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from decimal import Decimal
import json
import re

SOURCE = "https://api.openstreetmap.org/api/0.6/changeset/"


def pack(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def observe(changeset_id):
    response = gl.nondet.web.get(SOURCE + str(changeset_id) + ".json")
    if response.status != 200:
        raise gl.vm.UserError("CHANGESET_SOURCE_UNAVAILABLE")
    try:
        payload = json.loads(response.body, parse_float=Decimal)
        item = payload.get("changeset")
        if item is None:
            [item] = payload["changesets"]
        if type(item["id"]) is not int or item["id"] != changeset_id:
            raise ValueError("Mismatched changeset")
        if item["open"] is not False:
            raise gl.vm.UserError("CHANGESET_NOT_CLOSED")
        count = item["changes_count"]
        if type(count) is not int or not 1 <= count <= 100000:
            raise ValueError("Invalid edit count")
        bounds = []
        for field in ("min_lat", "min_lon", "max_lat", "max_lon"):
            number = item[field]
            if type(number) not in (int, Decimal):
                raise ValueError("Invalid coordinate")
            scaled = Decimal(number) * 10000000
            if not scaled.is_finite() or scaled != scaled.to_integral_value():
                raise ValueError("Unsupported coordinate precision")
            bounds.append(int(scaled))
        if not (-900000000 <= bounds[0] <= bounds[2] <= 900000000 and
                -1800000000 <= bounds[1] <= bounds[3] <= 1800000000):
            raise ValueError("Invalid bounds")
    except (KeyError, AttributeError, TypeError, ValueError, ArithmeticError):
        raise gl.vm.UserError("INVALID_CHANGESET_RECORD")
    return pack({"id": changeset_id, "bounds_e7": bounds, "changes": count})


@allow_storage
class MapReviewBudget(gl.Contract):
    campaigns: TreeMap[str, str]
    decisions: TreeMap[str, str]

    def __init__(self):
        pass

    @gl.public.view
    def read_campaign(self, owner: str, key: str) -> str:
        return self.campaigns.get(owner.lower() + "/" + key, "")

    @gl.public.view
    def read_decision(self, owner: str, key: str, changeset_id: u32) -> str:
        return self.decisions.get(owner.lower() + "/" + key + "/" + str(changeset_id), "")

    @gl.public.write
    def open_campaign(self, key: str, south: i32, west: i32, north: i32, east: i32, budget: u32) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,39}", key):
            raise gl.vm.UserError("INVALID_CAMPAIGN_KEY")
        if not (-900000000 <= south < north <= 900000000 and -1800000000 <= west < east <= 1800000000):
            raise gl.vm.UserError("INVALID_CAMPAIGN_BOUNDS")
        if not 1 <= budget <= 100000:
            raise gl.vm.UserError("INVALID_REVIEW_BUDGET")
        owner = str(gl.message.sender_address).lower()
        campaign_key = owner + "/" + key
        if campaign_key in self.campaigns:
            raise gl.vm.UserError("CAMPAIGN_ALREADY_EXISTS")
        self.campaigns[campaign_key] = pack({
            "owner": owner, "key": key, "bounds_e7": [south, west, north, east],
            "budget": int(budget), "remaining": int(budget), "admitted": [], "status": "OPEN",
        })

    @gl.public.write
    def submit_changeset(self, key: str, changeset_id: u32) -> None:
        # The maintainer alone can spend their review capacity.
        owner = str(gl.message.sender_address).lower()
        campaign_key = owner + "/" + key
        raw = self.campaigns.get(campaign_key, "")
        if not raw:
            raise gl.vm.UserError("CAMPAIGN_NOT_FOUND")
        campaign = json.loads(raw)
        if campaign["status"] != "OPEN":
            raise gl.vm.UserError("CAMPAIGN_CLOSED")
        if changeset_id == 0:
            raise gl.vm.UserError("INVALID_CHANGESET_ID")
        decision_key = campaign_key + "/" + str(changeset_id)
        if decision_key in self.decisions:
            raise gl.vm.UserError("CHANGESET_ALREADY_EVALUATED")
        observation = json.loads(gl.eq_principle.strict_eq(lambda: observe(int(changeset_id))))
        south, west, north, east = campaign["bounds_e7"]
        low_lat, low_lon, high_lat, high_lon = observation["bounds_e7"]
        if not (south <= low_lat <= high_lat <= north and west <= low_lon <= high_lon <= east):
            outcome = "OUT_OF_AREA"
        elif observation["changes"] > campaign["remaining"]:
            outcome = "OVER_BUDGET"
        else:
            outcome = "ADMITTED"
            campaign["remaining"] -= observation["changes"]
            campaign["admitted"].append(int(changeset_id))
            self.campaigns[campaign_key] = pack(campaign)
        self.decisions[decision_key] = pack(dict(observation, outcome=outcome))

    @gl.public.write
    def close_campaign(self, key: str) -> None:
        owner = str(gl.message.sender_address).lower()
        campaign_key = owner + "/" + key
        raw = self.campaigns.get(campaign_key, "")
        if not raw:
            raise gl.vm.UserError("CAMPAIGN_NOT_FOUND")
        campaign = json.loads(raw)
        if campaign["status"] != "OPEN":
            raise gl.vm.UserError("CAMPAIGN_CLOSED")
        campaign["status"] = "CLOSED"
        self.campaigns[campaign_key] = pack(campaign)
