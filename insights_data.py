import os
import requests
import json
from supabase import create_client, Client
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# --- 0. 환경 변수 로드 ---
load_dotenv(dotenv_path="instagram.env")

# --- 1. 설정 불러오기 ---
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
IG_ACCOUNT_ID = os.getenv("IG_ACCOUNT_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_VERSION = "v24.0"

# --- 2. 날짜 및 API 파라미터 준비 ---
kst_now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday_dt = kst_now - timedelta(days=1)
today_dt = kst_now

date_to_insert = yesterday_dt.strftime('%Y-%m-%d')
since_date_str = date_to_insert
until_date_str = today_dt.strftime('%Y-%m-%d')

url_insights = f"https://graph.facebook.com/{API_VERSION}/{IG_ACCOUNT_ID}/insights"

# --- 2-1. 일일 인사이트 요청 (metric_type 제거!) ---
daily_metrics = "total_interactions,comments,likes,reach,shares,views,profile_views"
params_daily = {
    'metric': daily_metrics,
    'period': 'day',
    'since': since_date_str,
    'until': until_date_str,
    # 'metric_type': 'total_value', <<< 이 줄을 완전히 삭제!
    'access_token': ACCESS_TOKEN
}

# --- 2-2. 계정 정보 요청 ---
url_account_info = f"https://graph.facebook.com/{API_VERSION}/{IG_ACCOUNT_ID}"
params_account_info = {
    'fields': 'followers_count,media_count',
    'access_token': ACCESS_TOKEN
}


# --- 3. API 요청 보내기 ---
metrics_dict = {}
account_dict = {}
try:
    if not IG_ACCOUNT_ID: raise ValueError("IG_ACCOUNT_ID not loaded.")
    
    print("Requesting daily insights...")
    response_daily = requests.get(url_insights, params=params_daily)
    response_daily.raise_for_status()
    
    # --- 파싱 로직 수정! ---
    for item in response_daily.json()['data']:
        # 'values' 리스트의 첫 번째 항목에서 'value'를 가져옵니다.
        metrics_dict[item['name']] = item.get('values', [{}])[0].get('value', 0)
    print("✅ Daily Insights API Call Successful!")

    print("Requesting account info...")
    response_account = requests.get(url_account_info, params=params_account_info)
    response_account.raise_for_status()
    account_dict = response_account.json()
    print("✅ Account Info API Call Successful!")

except Exception as err:
    print(f"❌ API Call Failed!")
    if isinstance(err, requests.exceptions.HTTPError):
        print(json.dumps(err.response.json(), indent=2, ensure_ascii=False))
    else:
        print(f"An unexpected error occurred: {err}")
    exit()

# --- 4. Supabase에 데이터 저장하기 ---
# (이 부분은 수정할 필요 없이 완벽합니다. 그대로 두세요.)
if not all([SUPABASE_URL, SUPABASE_KEY]):
    print("❌ Supabase URL 또는 Key가 설정되지 않았습니다.")
else:
    try:
        print("\nConnecting to Supabase...")
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        record_insights = {
            'date': date_to_insert,
            'total_interactions': metrics_dict.get('total_interactions', 0),
            'comments': metrics_dict.get('comments', 0),
            'likes': metrics_dict.get('likes', 0),
            'reach': metrics_dict.get('reach', 0),
            'shares': metrics_dict.get('shares', 0),
            'views': metrics_dict.get('views', 0),
            'profile_views': metrics_dict.get('profile_views', 0),
        }
        print("\n--- Saving to 'ig_daily_account_metrics' ---")
        print(json.dumps(record_insights, indent=2))
        supabase.table("ig_daily_account_metrics").upsert(record_insights).execute()
        print("✅ Successfully saved daily metrics!")

        today_date_to_insert = kst_now.strftime('%Y-%m-%d')
        record_snapshot = {
            'date': today_date_to_insert,
            'followers': account_dict.get('followers_count', 0),
            'media_count': account_dict.get('media_count', 0)
        }
        print("\n--- Saving to 'ig_account_snapshot' ---")
        print(json.dumps(record_snapshot, indent=2))
        supabase.table("ig_account_snapshot").insert(record_snapshot).execute()
        print("✅ Successfully saved account snapshot!")

    except Exception as e:
        print(f"❌ Failed to save data to Supabase. Error: {e}")

