import os
import requests
import json
from supabase import create_client, Client
from datetime import datetime, timedelta

# --- 1. 설정 불러오기 ---

ACCESS_TOKEN="EAAKaZCteTM2UBQGBqipBj1HlQoZCBrwGHD2kH9SPezOxrPjlZATFZAOvAODNhZAZA2fbEpVT2IPZBbBRn9ZBvsSodS9itapatBpZCzUQXyGbTY9host2miVGEqCzuUArCZCgKq34SJom8rVZAPEVIpnoIyB6n3qaXLyuM1uL1S4vRt0I8IUKGwTYNjkDmJZC9KJxdXninjUZBTbm3CfM4"
IG_ACCOUNT_ID="17841432803341221"
SUPABASE_URL="https://lmzreioocratunlxlams.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtenJlaW9vY3JhdHVubHhsYW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ4NjQ2NTIsImV4cCI6MjA4MDQ0MDY1Mn0.4i6EZxi1-0UqqN08hPSqIOwvHSxGIuxenDTpYmL-s8M"
API_VERSION = "v24.0"

# --- 2. API 요청 준비 ---
metrics_to_fetch = [
    'total_interactions',
    'comments',
    'likes',
    'reach',
    'shares',
    'views',
    'profile_views'
]
metrics_string = ",".join(metrics_to_fetch)

url = f"https://graph.facebook.com/{API_VERSION}/{IG_ACCOUNT_ID}/insights"
params = {
    'metric': metrics_string,
    'period': 'day',
    'metric_type': 'total_value',
    'access_token': ACCESS_TOKEN
}

# --- 3. API 요청 보내기 ---
print(f"Requesting {len(metrics_to_fetch)} reliable daily metrics from API...")
response_data = None
try:
    # URL과 ID가 제대로 로드되었는지 한번 더 확인
    if not IG_ACCOUNT_ID:
        raise ValueError("IG_ACCOUNT_ID is not loaded from .env file. Please check the variable name.")

    response = requests.get(url, params=params)
    response.raise_for_status()
    response_data = response.json()
    print("✅ API Call Successful!")

except Exception as err:
    print(f"❌ API Call Failed!")
    # 에러가 requests.exceptions.HTTPError 일 경우, 더 상세한 정보를 출력
    if isinstance(err, requests.exceptions.HTTPError):
        print(json.dumps(err.response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"An unexpected error occurred: {err}")
    exit()

# --- 4. API 응답 데이터 파싱(Parsing)하기 ---
metrics_dict = {}
for item in response_data['data']:
    metric_name = item['name']
    metric_value = item.get('total_value', {}).get('value', 0)
    metrics_dict[metric_name] = metric_value

print("\n--- Parsed Data ---")
print(json.dumps(metrics_dict, indent=2))
print("-" * 20)

# --- 5. Supabase에 저장할 최종 데이터 준비하기 ---
yesterday = datetime.now() - timedelta(days=1)
date_to_insert = yesterday.strftime('%Y-%m-%d')

record_to_save = {
    'date': date_to_insert,
    'total_interactions': metrics_dict.get('total_interactions', 0),
    'comments': metrics_dict.get('comments', 0),
    'likes': metrics_dict.get('likes', 0),
    'reach': metrics_dict.get('reach', 0),
    'shares': metrics_dict.get('shares', 0),
    'views': metrics_dict.get('views', 0),
    'profile_views': metrics_dict.get('profile_views', 0)
}

print("\n--- Data to Save in Supabase ---")
print(json.dumps(record_to_save, indent=2))

print("-" * 20)

# --- 6. Supabase에 데이터 저장하기 ---
if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("❌ Supabase URL 또는 Key가 설정되지 않았습니다. ")
else:
    try:
        print("\nConnecting to Supabase...")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = supabase.table("ig_daily_account_metrics").upsert(record_to_save).execute()
        print("✅ Successfully saved data to Supabase!")
        print("Supabase 대시보드에서 'daily_account_metrics' 테이블을 확인해보세요!")
    except Exception as e:
        print(f"❌ Failed to save data to Supabase.")
        print(f"Error: {e}")
