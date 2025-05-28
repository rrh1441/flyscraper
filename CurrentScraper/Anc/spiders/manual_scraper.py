# spiders/anc_spider.py  •  2025-05-26
# ---------------------------------------------------------------
#  Scrapy spider for Seattle Parks tennis-court availability
#  – writes directly to Supabase table `tennis_courts_fly`
# ---------------------------------------------------------------
import json
import os
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import scrapy
from supabase import create_client


# --------------------------------------------------------------------------
#  Small helper: make a slug we can index on
# --------------------------------------------------------------------------
def canonicalise(addr: str) -> str:
    """Normalise an address for de-duping."""
    return re.sub(r"[^a-z0-9]", "", addr.lower())


# --------------------------------------------------------------------------
#  Minimal wrapper around Supabase
# --------------------------------------------------------------------------
class SupabaseWriter:
    """Thin Supabase UPSERT wrapper with retry and basic stats."""

    def __init__(self, url: str, table_name: str) -> None:
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # read from secret
        print(f"Initializing SupabaseWriter → {url}/{table_name}")
        self.supabase = create_client(url, key)
        self.table_name = table_name
        self.ok = 0
        self.fail = 0

    def write_record(self, record: dict) -> None:
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                print(f"📝  UPSERT {record['id']}  (try {attempt}/{max_retries})")
                (
                    self.supabase
                    .table(self.table_name)
                    .upsert(record, on_conflict="id")
                    .execute()
                )
                self.ok += 1
                print(f"✅  OK  • success={self.ok}  fail={self.fail}")
                return
            except Exception as exc:
                print(f"❌  {record['id']} write error: {exc!r}")
                if attempt < max_retries:
                    time.sleep(2)
                else:
                    self.fail += 1
                    print(f"💀  giving up • success={self.ok}  fail={self.fail}")
                    raise


# --------------------------------------------------------------------------
#  Spider
# --------------------------------------------------------------------------
class ManualAncSpider(scrapy.Spider):
    name = "ManualAncSpider"

    # Pacific-time helpers
    _pt = ZoneInfo("America/Los_Angeles")

    custom_settings = {
        "CONCURRENT_REQUESTS": 8,
        "DOWNLOAD_DELAY": 1.5,
        "LOG_LEVEL": "INFO",
    }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tomorrow = (datetime.now(self._pt) + timedelta(days=1)).strftime("%Y-%m-%d")
        self.csrf: str = ""
        self.db = SupabaseWriter(
            url="https://mqoqdddzrwvonklsprgb.supabase.co",
            table_name="tennis_courts_fly",
        )

    # ----------------------------------------------------------------------
    #  1) Load account page to grab CSRF
    # ----------------------------------------------------------------------
    def start_requests(self):
        headers = {
            "Accept":
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Referer": "https://anc.apm.activecommunities.com/",
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/129.0.0.0 Safari/537.36",
        }
        url = (
            "https://anc.apm.activecommunities.com/seattle/myaccount?"
            "onlineSiteId=0&from_original_cui=true&online=true&locale=en-US"
        )
        yield scrapy.Request(url, headers=headers)

    # ----------------------------------------------------------------------
    #  2) Parse CSRF and sign in
    # ----------------------------------------------------------------------
    def parse(self, response, **_):
        self.csrf = response.xpath(
            '//script/text()'
        ).re_first(r'window.__csrfToken = "(.*)";')
        if not self.csrf:
            raise RuntimeError("CSRF token not found – login impossible")

        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json;charset=utf-8",
            "Origin": "https://anc.apm.activecommunities.com",
            "Referer":
                "https://anc.apm.activecommunities.com/seattle/signin?onlineSiteId=0",
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/129.0.0.0 Safari/537.36",
            "X-CSRF-Token": self.csrf,
            "X-Requested-With": "XMLHttpRequest",
        }

        payload = {
            "login_name": "Seattletennisguy@gmail.com",
            "password": "ThisIsMyPassword44",
            "recaptcha_response": "",
            "signin_source_app": "0",
            "custom_amount": "False",
            "from_original_cui": "true",
            "onlineSiteId": "0",
            "override_partial_error": "False",
            "params":
                "aHR0cHM6Ly9hcG0uYWN0aXZlY29tbXVuaXRpZXMuY29tL3NlYXR0bGUv"
                "QWN0aXZlTmV0X0hvbWU/RmlsZU5hbWU9YWNjb3VudG9wdGlvbnMuc2Rp"
                "JmZyb21Mb2dpblBhZ2U9dHJ1ZQ==",
            "ak_properties": None,
        }

        url = (
            "https://anc.apm.activecommunities.com/"
            "seattle/rest/user/signin?locale=en-US"
        )
        yield scrapy.Request(
            url,
            headers=headers,
            body=json.dumps(payload),
            method="POST",
            callback=self.logged_in,
        )

    # ----------------------------------------------------------------------
    #  3) First facilities listing page
    # ----------------------------------------------------------------------
    def logged_in(self, _response):
        """Kick off listing with page_size=100 for fewer calls."""
        listing_headers = {
            "Accept": "*/*",
            "Content-Type": "application/json;charset=utf-8",
            "Origin": "https://anc.apm.activecommunities.com",
            "Referer":
                "https://anc.apm.activecommunities.com/"
                "seattle/reservation/search?facilityTypeIds=39%2C115",
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/129.0.0.0 Safari/537.36",
            "X-CSRF-Token": self.csrf,
            "X-Requested-With": "XMLHttpRequest",
        }

        payload = {
            "name": "",
            "attendee": 0,
            "date_times": [],
            "event_type_ids": [],
            "facility_type_ids": [39, 115],
            "reservation_group_ids": [],
            "amenity_ids": [],
            "facility_id": 0,
            "equipment_id": 0,
            "center_id": 0,
            "resource_type": 0,
            "client_coordinate": "",
            "order_by_field": "name",
            "order_direction": "asc",
            "page_size": 100,          # 100 per page → 2 pages for 116 items
            "start_index": 0,
            "search_client_id": "",
            "date_time_length": None,
            "full_day_booking": False,
            "center_ids": [],
        }

        url = (
            "https://anc.apm.activecommunities.com/"
            "seattle/rest/reservation/resource?locale=en-US"
        )
        yield scrapy.Request(
            url,
            headers=listing_headers,
            body=json.dumps(payload),
            method="POST",
            callback=self.listing,
            meta={"headers": listing_headers, "start_index": 0},
        )

    # ----------------------------------------------------------------------
    #  4) Walk paginated list
    # ----------------------------------------------------------------------
    def listing(self, response):
        data = json.loads(response.text).get("body", {})
        headers = response.meta["headers"]
        start_index = response.meta["start_index"]

        for res in data.get("items", []):
            item_stub = {"id": res["id"]}
            detail_url = (
                "https://anc.apm.activecommunities.com/"
                f"seattle/rest/reservation/resource/detail/{res['id']}"
            )
            yield scrapy.Request(
                detail_url,
                headers=headers,
                callback=self.details,
                meta={"item": item_stub},
            )

        next_index = data.get("next_start_index")
        total = data.get("total", 0)

        if next_index is not None and next_index < total:
            payload = response.request.body  # bytes → reuse & patch index
            payload_dict = json.loads(payload)
            payload_dict["start_index"] = next_index
            next_payload = json.dumps(payload_dict)

            url = response.request.url  # same endpoint
            yield scrapy.Request(
                url,
                headers=headers,          # same header (incl. CSRF!)
                body=next_payload,
                method="POST",
                callback=self.listing,
                meta={"headers": headers, "start_index": next_index},
            )

    # ----------------------------------------------------------------------
    #  5) Detail page
    # ----------------------------------------------------------------------
    def details(self, response):
        data = (
            json.loads(response.text)
            .get("body", {})
            .get("resource_detail", {})
            .get("general_information", {})
        )

        item = response.meta["item"]
        item["title"] = data.get("facility_name", "")
        item["facility_type"] = data.get("facility_type", "")
        item["address"] = (
            f"{data.get('center_name','')}"
            f"{data.get('address1','')}"
            f"{data.get('city','')}, {data.get('state','')}, {data.get('zip_code','')}"
        ).strip()

        availability_url = (
            "https://anc.apm.activecommunities.com/"
            f"seattle/rest/reservation/resource/availability/daily/{item['id']}"
            f"?start_date={self.tomorrow}&end_date={self.tomorrow}"
            "&customer_id=0&company_id=0&event_type_id=-1&attendee=1"
        )
        headers = {
            "Accept": "*/*",
            "User-Agent":
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/129.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        }
        yield scrapy.Request(
            availability_url,
            headers=headers,
            callback=self.availability,
            meta={"item": item},
        )

    # ----------------------------------------------------------------------
    #  6) Daily availability
    # ----------------------------------------------------------------------
    def availability(self, response):
        data = json.loads(response.text).get("body", {})
        item = response.meta["item"]

        times = []
        for entry in data.get("availability_blocks", []):
            available = entry.get("available", False)
            start_time = entry.get("start_time_strf", "")
            end_time = entry.get("end_time_strf", "")

            if available and start_time and end_time:
                times.append(f"{self.tomorrow}  {start_time}-{end_time}")

        item["available_dates"] = "\n".join(times)
        item["address_slug"] = canonicalise(item["address"])

        # Write to Supabase
        self.db.write_record(item)
        yield item 