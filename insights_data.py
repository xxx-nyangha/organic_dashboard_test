import os
import requests
import json
from supabase import create_client, Client
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

#KST 시간 정의
kst_now = datetime.now(ZoneInfo("Asia/Seoul"))

#KST 기준 '어제' 날짜 계산
yesterday = kst_now - timedelta(days=1)
target_date_str = yesterday.strftime('%Y-%m-%d')


# --- 1. 설정 불러오기 ---

ACCESS_TOKEN="EAAKaZCteTM2UBQGBqipBj1HlQoZCBrwGHD2kH9SPezOxrPjlZATFZAOvAODNhZAZA2fbEpVT2IPZBbBRn9ZBvsSodS9itapatBpZCzUQXyGbTY9host2miVGEqCzuUArCZCgKq34SJom8rVZAPEVIpnoIyB6n3qaXLyuM1uL1S4vRt0I8IUKGwTYNjkDmJZC9KJxdXninjUZBTbm3CfM4"
IG_ACCOUNT_ID="17841432803341221"
SUPABASE_URL="https://lmzreioocratunlxlams.supabase.co"
SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxtenJlaW9vY3JhdHVubHhsYW1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ4NjQ2NTIsImV4cCI6MjA4MDQ0MDY1Mn0.4i6EZxi1-0UqqN08hPSqIOwvHSxGIuxenDTpYmL-s8M"
API_VERSION = "v24.0"

# --- 2. API 요청 준비 ---
metrics_to_fetch = [
    'total_interactions', 'comments', 'likes', 'reach', 'shares', 'views', 'profile_views'
]
metrics_string = ",".join(metrics_to_fetch)
url_insights = f"https://graph.facebook.com/{API_VERSION}/{IG_ACCOUNT_ID}/insights"
params_insights = {
    'metric': metrics_string,
    'period': 'day',
    'metric_type': 'total_value',
    'access_token': ACCESS_TOKEN
}

# <<< 수정됨: 2-2. 팔로워, 미디어 개수 요청 준비 (새로 추가)
url_account_info = f"https://graph.facebook.com/{API_VERSION}/{IG_ACCOUNT_ID}"
params_account_info = {
    'fields': 'followers_count,media_count',
    'access_token': ACCESS_TOKEN
}


# --- 3. API 요청 보내기 ---
response_data_insights = None
response_data_account = None

try:
    if not IG_ACCOUNT_ID:
        raise ValueError("IG_ACCOUNT_ID is not loaded from .env file.")

    # 3-1. 일일 인사이트 API 호출
    print(f"Requesting {len(metrics_to_fetch)} daily insights from API...")
    response_insights = requests.get(url_insights, params=params_insights)
    response_insights.raise_for_status()
    response_data_insights = response_insights.json()
    print("✅ Daily Insights API Call Successful!")

    # <<< 수정됨: 3-2. 계정 정보(팔로워 등) API 호출 (새로 추가)
    print("Requesting account info (followers, media_count) from API...")
    response_account = requests.get(url_account_info, params=params_account_info)
    response_account.raise_for_status()
    response_data_account = response_account.json()
    print("✅ Account Info API Call Successful!")

except Exception as err:
    print(f"❌ API Call Failed!")
    if isinstance(err, requests.exceptions.HTTPError):
        # 어떤 응답에서 에러가 났는지 명확히 하기 위해 err.response 사용
        print(json.dumps(err.response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"An unexpected error occurred: {err}")
    exit()

# --- 4. API 응답 데이터 파싱(Parsing)하기 ---

# 4-1. 인사이트 데이터 파싱
metrics_dict = {}
for item in response_data_insights['data']:
    metric_name = item['name']
    metric_value = item.get('total_value', {}).get('value', 0)
    metrics_dict[metric_name] = metric_value

# <<< 수정됨: 4-2. 계정 정보 데이터 파싱 (새로 추가)
followers_count = response_data_account.get('followers_count', 0)
media_count = response_data_account.get('media_count', 0)


print("\n--- Parsed Data ---")
print("Insights:", json.dumps(metrics_dict, indent=2))
print(f"Followers: {followers_count}, Media Count: {media_count}")
print("-" * 20)


# --- 5. Supabase에 저장할 최종 데이터 준비하기 ---




# <<< 수정됨: 최종 데이터 객체에 팔로워, 미디어 개수 통합
record_to_save = {
    'date': date_to_insert,
    'total_interactions': metrics_dict.get('total_interactions', 0),
    'comments': metrics_dict.get('comments', 0),
    'likes': metrics_dict.get('likes', 0),
    'reach': metrics_dict.get('reach', 0),
    'shares': metrics_dict.get('shares', 0),
    'views': metrics_dict.get('views', 0),
    'profile_views': metrics_dict.get('profile_views', 0),
    'followers': followers_count,
    'media_count': media_count
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
        
        # <<< 수정됨: 테이블 이름을 'ig_daily_account_metrics'로 통일하고 'upsert' 사용
        # upsert는 데이터가 있으면 UPDATE, 없으면 INSERT를 자동으로 해줍니다.
        result = supabase.table("ig_daily_account_metrics").upsert(record_to_save).execute()
        
        print("✅ Successfully saved data to Supabase!")
        print("Supabase 대시보드에서 'ig_daily_account_metrics' 테이블을 확인해보세요!")
    except Exception as e:
        print(f"❌ Failed to save data to Supabase.")
        print(f"Error: {e}")
