# spiders/anc_spider.py  –  full version, no lines omitted
import json
import os
import re
import scrapy
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client


# --------------------------------------------------------------------------
#  Small helper: make a slug we can index on
# --------------------------------------------------------------------------
def canonicalise(addr: str) -> str:
    return re.sub(r"[^a-z0-9]", "", addr.lower())


# --------------------------------------------------------------------------
#  Minimal wrapper around Supabase
# --------------------------------------------------------------------------
class SupabaseWriter:
    def __init__(self, url, table_name):
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # ← read from secret
        print(f"Initializing SupabaseWriter with URL: {url}, table: {table_name}")
        self.supabase = create_client(url, key)
        self.table_name = table_name
        self.write_success_count = 0
        self.write_failure_count = 0

    def write_record(self, record):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"📝 Writing record {record['id']} (attempt {attempt + 1}/{max_retries})")
                
                data = (
                    self.supabase
                    .table(self.table_name)
                    .upsert(record, on_conflict="id")       # real UPSERT
                    .execute()
                )
                
                self.write_success_count += 1
                print(f"✅ SUCCESS #{self.write_success_count}: {record['id']}")
                print(f"📊 Stats: {self.write_success_count} success, {self.write_failure_count} failures")
                return  # Success - exit retry loop
                
            except Exception as e:
                print(f"❌ Error writing record {record['id']} (attempt {attempt + 1}): {e}")
                print(f"Error type: {type(e)}")
                
                if attempt < max_retries - 1:
                    print(f"Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    # Final attempt failed
                    self.write_failure_count += 1
                    print(f"💀 FINAL FAILURE #{self.write_failure_count}: {record['id']}")
                    print(f"📊 Stats: {self.write_success_count} success, {self.write_failure_count} failures")
                    
                    # CRITICAL: Re-raise the exception so Scrapy knows it failed
                    raise


# --------------------------------------------------------------------------
#  Spider
# --------------------------------------------------------------------------
class AncSpider(scrapy.Spider):
    name = 'AncSpider'

    # Pacific-time helpers
    _pt = ZoneInfo("America/Los_Angeles")
    timestemp = datetime.now(_pt).strftime("%d_%b_%Y_%H_%M_%S")
    today = datetime.now(_pt).strftime("%Y-%m-%d")
    date_after_14_days = (datetime.now(_pt) + timedelta(days=14)).strftime("%Y-%m-%d")

    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 1.5
    }

    visited_urls = []
    csrf = ''

    def __init__(self, *args, **kwargs):
        super(AncSpider, self).__init__(*args, **kwargs)
        self.tomorrow = (datetime.now(self._pt) + timedelta(days=1)).strftime("%Y-%m-%d")
        self.db = SupabaseWriter(
            url="https://mqoqdddzrwvonklsprgb.supabase.co",
            table_name="tennis_courts"  # Now writing to production table
        )

    # ----------------------------------------------------------------------
    #  1) Load account page to grab CSRF
    # ----------------------------------------------------------------------
    def start_requests(self):
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Connection': 'keep-alive',
            'Referer': 'https://anc.apm.activecommunities.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-site',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        url = 'https://anc.apm.activecommunities.com/seattle/myaccount?onlineSiteId=0&from_original_cui=true&online=true&locale=en-US'
        yield scrapy.Request(url, headers=headers)

    # ----------------------------------------------------------------------
    #  2) Parse CSRF and sign in
    # ----------------------------------------------------------------------
    def parse(self, response, **kwargs):
        self.csrf = response.xpath('//script/text()').re_first('window.__csrfToken = "(.*)";')
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json;charset=utf-8',
            'Origin': 'https://anc.apm.activecommunities.com',
            'Referer': ('https://anc.apm.activecommunities.com/seattle/signin?onlineSiteId=0'
                        '&from_original_cui=true&override_partial_error=False&custom_amount=False'
                        '&params=aHR0cHM6Ly9hcG0uYWN0aXZlY29tbXVuaXRpZXMuY29tL3NlYXR0bGUvQWN0aXZlTmV0X0hvbWU'
                        '%2FRmlsZU5hbWU9YWNjb3VudG9wdGlvbnMuc2RpJmZyb21Mb2dpblBhZ2U9dHJ1ZQ%3D%3D'),
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'X-CSRF-Token': self.csrf,
            'X-Requested-With': 'XMLHttpRequest',
            'page_info': '{"page_number":1,"total_records_per_page":20}',
            'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        payload = (
            "{\"login_name\":\"Seattletennisguy@gmail.com\",\"password\":\"ThisIsMyPassword44\","
            "\"recaptcha_response\":\"\",\"signin_source_app\":\"0\",\"custom_amount\":\"False\","
            "\"from_original_cui\":\"true\",\"onlineSiteId\":\"0\",\"override_partial_error\":\"False\","
            "\"params\":\"aHR0cHM6Ly9hcG0uYWN0aXZlY29tbXVuaXRpZXMuY29tL3NlYXR0bGUvQWN0aXZlTmV0X0hvbWU/"
            "RmlsZU5hbWU9YWNjb3VudG9wdGlvbnMuc2RpJmZyb21Mb2dpblBhZ2U9dHJ1ZQ==\",\"ak_properties\":null}"
        )
        url = 'https://anc.apm.activecommunities.com/seattle/rest/user/signin?locale=en-US'
        yield scrapy.Request(url, headers=headers, body=payload, callback=self.loggedin, method='POST')

    # ----------------------------------------------------------------------
    #  3) Hit the resource listing endpoint
    # ----------------------------------------------------------------------
    def loggedin(self, response):
        url = "https://anc.apm.activecommunities.com/seattle/rest/reservation/resource?locale=en-US"
        payload = (
            "{\"name\":\"\",\"attendee\":0,\"date_times\":[],\"event_type_ids\":[],"
            "\"facility_type_ids\":[39,115],\"reservation_group_ids\":[],\"amenity_ids\":[],"
            "\"facility_id\":0,\"equipment_id\":0,\"center_id\":0,\"resource_type\":0,"
            "\"client_coordinate\":\"\",\"order_by_field\":\"name\",\"order_direction\":\"asc\","
            "\"page_size\":20,\"start_index\":0,\"search_client_id\":\"\",\"date_time_length\":null,"
            "\"full_day_booking\":false,\"center_ids\":[]}"
        )
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json;charset=utf-8',
            'Origin': 'https://anc.apm.activecommunities.com',
            'Referer': ('https://anc.apm.activecommunities.com/seattle/reservation/search?'
                        'facilityTypeIds=39%2C115&resourceType=0&equipmentQty=0'),
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/129.0.0.0 Safari/537.36',
            'X-CSRF-Token': self.csrf,
            'X-Requested-With': 'XMLHttpRequest',
            'page_info': '{"page_number":1,"total_records_per_page":20}',
            'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        yield scrapy.Request(url, headers=headers, body=payload, callback=self.listing, method='POST')

    # ----------------------------------------------------------------------
    #  4) Walk paginated list
    # ----------------------------------------------------------------------
    def listing(self, response):
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
            'Referer': 'https://anc.apm.activecommunities.com/seattle/reservation/search/detail/1146',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/129.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'page_info': '{"page_number":1,"total_records_per_page":20}',
            'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        body = json.loads(response.text).get('body', {})
        index = body.get('next_start_index')
        total = body.get('total')
        for item in body.get('items', []):
            new_item = {'id': item['id']}
            url = f'https://anc.apm.activecommunities.com/seattle/rest/reservation/resource/detail/{item["id"]}'
            yield scrapy.Request(url, headers=headers, callback=self.details, meta={'item': new_item})

        if index < total:
            url = "https://anc.apm.activecommunities.com/seattle/rest/reservation/resource?locale=en-US"
            payload = (
                "{\"name\":\"\",\"attendee\":0,\"date_times\":[],\"event_type_ids\":[],"
                "\"facility_type_ids\":[39,115],\"reservation_group_ids\":[],\"amenity_ids\":[],"
                "\"facility_id\":0,\"equipment_id\":0,\"center_id\":0,\"resource_type\":0,"
                "\"client_coordinate\":\"\",\"order_by_field\":\"name\",\"order_direction\":\"asc\","
                "\"page_size\":20,\"start_index\":%s,\"search_client_id\":\"\",\"date_time_length\":null,"
                "\"full_day_booking\":false,\"center_ids\":[]}" % index
            )
            yield scrapy.Request(url, headers=headers, body=payload, callback=self.listing, method='POST')

    # ----------------------------------------------------------------------
    #  5) Detail page
    # ----------------------------------------------------------------------
    def details(self, response):
        data = json.loads(response.text).get('body', {}).get('resource_detail').get('general_information', {})
        item = response.meta['item']
        item['title'] = data.get('facility_name', '')
        item['facility_type'] = data.get('facility_type', '')
        item['address'] = f'{data["center_name"]} {data["address1"]} {data["city"]}, {data["state"]}, {data["zip_code"]}'
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,de;q=0.8',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
            'Referer': 'https://anc.apm.activecommunities.com/seattle/reservation/search/detail/1146',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/129.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            'page_info': '{"page_number":1,"total_records_per_page":20}',
            'sec-ch-ua': '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        url = (f'https://anc.apm.activecommunities.com/seattle/rest/reservation/resource/availability/daily/{item["id"]}'
               f'?start_date={self.tomorrow}&end_date={self.tomorrow}&customer_id=0&company_id=0&event_type_id=-1&attendee=1')
        yield scrapy.Request(url, headers=headers, callback=self.dates, meta={'item': item})

    # ----------------------------------------------------------------------
    #  6) Availability slots  ➜ write
    # ----------------------------------------------------------------------
    def dates(self, response):
        item = response.meta['item']
        data = json.loads(response.body).get('body', {}).get('details', {}).get('daily_details', [])
        available_dates = []
        for d in data:
            date = d.get('date')
            for time in d.get('times', []):
                if time.get('available'):
                    available_dates.append(f'{date}  {time.get("start_time")}-{time.get("end_time")}')
        item['available_dates'] = '\n'.join(available_dates)
        item['last_updated'] = datetime.now(self._pt).isoformat()
        item['canonical_addr'] = canonicalise(item['address'])

        # This will now properly fail if Supabase write fails
        self.db.write_record(item)
        yield item