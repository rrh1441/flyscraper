import json
import scrapy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from supabase import create_client

class SupabaseWriter:
    def __init__(self, url, key, table_name):
        print(f"Initializing SupabaseWriter with URL: {url}, table: {table_name}")
        # Debug prints to verify the URL
        print("URL length:", len(url))
        print("URL content:", repr(url))
        self.supabase = create_client(url, key)
        self.table_name = table_name

    def write_record(self, record):
        try:
            print(f"Attempting to write record to Supabase: {record}")
            data = self.supabase.table(self.table_name).upsert(record).execute()
            print(f"Successfully wrote record: {record['id']}")
            print(f"Supabase response: {data}")
        except Exception as e:
            print(f"Error writing to Supabase: {e}")
            print(f"Error type: {type(e)}")

class AncSpider(scrapy.Spider):
    name = 'AncSpider'
    # Calculate timestamp using Pacific Time for reference (stored as text)
    timestemp = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%d_%b_%Y_%H_%M_%S")
    final_list = []
    custom_settings = {
        'CONCURRENT_REQUESTS': 8,
        'DOWNLOAD_DELAY': 1.5
    }
    visited_urls = []
    csrf = ''

    # Calculate 'today' and 'date_after_14_days' in Pacific Time
    today = datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    date_after_14_days = (datetime.now(ZoneInfo("America/Los_Angeles")) + timedelta(days=14)).strftime("%Y-%m-%d")

    def __init__(self, *args, **kwargs):
        super(AncSpider, self).__init__(*args, **kwargs)
        # Calculate 'tomorrow' in Pacific Time
        self.tomorrow = (datetime.now(ZoneInfo("America/Los_Angeles")) + timedelta(days=1)).strftime("%Y-%m-%d")
        self.db = SupabaseWriter(
            url="https://mqoqdddzrwvonklsprgb.supabase.co/",  # Trailing slash added
            key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xb3FkZGR6cnd2b25rbHNwcmdiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI2NjIyNDEsImV4cCI6MjA0ODIzODI0MX0.18AdLB9xAb8rN2-G9YIiyjoH-u7uaReXqbelkzZXGPI",
            table_name="tennis_courts_fly"
        )

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
        index = json.loads(response.text).get('body', {}).get('next_start_index')
        total = json.loads(response.text).get('body', {}).get('total')
        for item in json.loads(response.text).get('body', {}).get('items', []):
            new_item = {}
            new_item['id'] = item["id"]
            url = f'https://anc.apm.activecommunities.com/seattle/rest/reservation/resource/detail/{item["id"]}'
            yield scrapy.Request(url, headers=headers, callback=self.details, meta={'item': new_item})

        url = "https://anc.apm.activecommunities.com/seattle/rest/reservation/resource?locale=en-US"
        payload = (
            "{\"name\":\"\",\"attendee\":0,\"date_times\":[],\"event_type_ids\":[],"
            "\"facility_type_ids\":[39,115],\"reservation_group_ids\":[],\"amenity_ids\":[],"
            "\"facility_id\":0,\"equipment_id\":0,\"center_id\":0,\"resource_type\":0,"
            "\"client_coordinate\":\"\",\"order_by_field\":\"name\",\"order_direction\":\"asc\","
            "\"page_size\":20,\"start_index\":%s,\"search_client_id\":\"\",\"date_time_length\":null,"
            "\"full_day_booking\":false,\"center_ids\":[]}" % index
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
        if index < total:
            yield scrapy.Request(url, headers=headers, body=payload, callback=self.listing, method='POST')

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

    def dates(self, response):
        item = response.meta['item']
        data = json.loads(response.body).get('body', {}).get('details', {}).get('daily_details', [])
        available_dates = []
        for d in data:
            date = d.get('date')
            for time in d.get('times'):
                if time.get('available'):
                    available_dates.append(f'{date}  {time.get("start_time")}-{time.get("end_time")}')
        item['available_dates'] = '\n'.join(available_dates)
        # Use Pacific Time for last_updated, stored as text
        item['last_updated'] = datetime.now(ZoneInfo("America/Los_Angeles")).isoformat()
        self.db.write_record(item)
        yield item
