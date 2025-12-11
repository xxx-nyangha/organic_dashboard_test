import os
import requests
import json
from supabase import create_client, Client
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo



# --- 1. 설정 불러오기 ---

ACCESS_TOKEN="EAAKaZCteTM2UBQGBqipBj1HlQoZCBrwGHD2kH9SPezOxrPjlZATFZAOvAODNhZAZA2fbEpVT2IPZBbBRn9ZBvsSodS9itapatBpZCzUQXyGbTY9host2miVGEqCzuUArCZCgKq34SJom8rVZAPEVIpnoIyB6n3qaXLyuM1uL1S4vRt0I8IUKGwTYNjkDmJZC9KJxdXninjUZBTbm3CfM4"
IG_ACCOUNT_ID="17841432803341221"
SUPABASE_URL="https://lmzreioocratunlxlams.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtenJlaW9vY3JhdHVubHhsYW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ4NjQ2NTIsImV4cCI6MjA4MDQ0MDY1Mn0.4i6EZxi1-0UqqN08hPSqIOwvHSxGIuxenDTpYmL-s8M"
API_VERSION = "v24.0"

# --- 2. API 요청 준비 ---
# --- 2. 날짜 및 API 파라미터 준비 ---
kst_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday_dt = kst_now - timedelta(days=1)
date_to_insert = yesterday_dt.strftime('%Y-%m-%d')
until_dt = kst_now.replace(hour=0, minute=0, second=0, microsecond=0)
until_timestamp = int(until_dt.timestamp())

url_insights = f"https://graph.facebook.com/{API_VERSION}/{IG_ACCOUNT_ID}/insights"
daily_metrics = "total_interactions,comments,likes,reach,shares,views,profile_views"
params_daily = {
    'metric': daily_metrics, 'period': 'day', 'since': int(yesterday_dt.timestamp()), 'until': until_timestamp, 'access_token': ACCESS_TOKEN
}

url_account_info = f"https://graph.facebook.com/{API_VERSION}/{IG_ACCOUNT_ID}"
params_account_info = {
    'fields': 'followers_count,media_count', 'access_token': ACCESS_TOKEN
}


# --- 3. API 요청 보내기 ---
metrics_dict = {}
account_dict = {}

try:
    if not IG_ACCOUNT_ID: raise ValueError("IG_ACCOUNT_ID not loaded.")
    
    # 3-1. 일일 증감 지표 API 호출
    print("Requesting daily insights...")
    response_daily = requests.get(url_insights, params=params_daily)
    response_daily.raise_for_status()
    for item in response_daily.json()['data']:
        metrics_dict[item['name']] = item.get('values', [{}])[0].get('value', 0)
    print("✅ Daily Insights API Call Successful!")

    # 3-2. 계정 정보 API 호출
    print("Requesting account info...")
    response_account = requests.get(url_account_info, params=params_account_info)
    response_account.raise_for_status()
    account_dict = response_account.json()
    print("✅ Account Info API Call Successful!")

except Exception as err:
    print(f"❌ API Call Failed! Error: {err}")
    exit()


# --- 4. Supabase에 데이터 저장하기 ---
if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("❌ Supabase URL 또는 Key가 설정되지 않았습니다.")
else:
    try:
        print("\nConnecting to Supabase...")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # --- 4-1. 'ig_daily_account_metrics' 테이블에 저장 ---
        record_insights = {
            'date': date_to_insert,
            **metrics_dict  # 딕셔너리를 풀어헤쳐서 자동으로 매핑
        }
        print("\n--- Saving to 'ig_daily_account_metrics' ---")
        print(json.dumps(record_insights, indent=2))
        supabase.table("ig_daily_account_metrics").upsert(record_insights).execute()
        print("✅ Successfully saved daily metrics!")

        # --- 4-2. 'ig_account_snapshot' 테이블에 저장 ---
        record_snapshot = {
            'date': date_to_insert,
            'followers': account_dict.get('followers_count', 0),
            'media_count': account_dict.get('media_count', 0)
        }
        print("\n--- Saving to 'ig_account_snapshot' ---")
        print(json.dumps(record_snapshot, indent=2))
        supabase.table("ig_account_snapshot").insert(record_snapshot).execute()
        print("✅ Successfully saved account snapshot!")

    except Exception as e:
        print(f"❌ Failed to save data to Supabase. Error: {e}")
