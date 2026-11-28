"""loader.py - 모든 화면이 같이 쓰는 데이터 불러오기 (캐시 적용)

캐시를 두 겹으로 나눈 이유:
- API 성공 결과는 하루 동안 재사용 (매번 72번 호출하지 않도록)
- API 실패(백업 사용)는 10분만 기억하고 다시 API를 시도 (실패가 하루 종일 고정되지 않도록)
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from data import BACKUP_PATH, clean, fetch_all, prepare, safe_reason


@st.cache_data(ttl=60 * 60 * 24, show_spinner="국토부 실거래 데이터를 불러오는 중입니다 (처음 한 번만 1분 정도 걸립니다)")
def fetch_api(api_key):
    """API 호출 결과. 실패하면 오류가 나고, 오류는 캐시되지 않는다."""
    return clean(fetch_all(api_key))


@st.cache_data(ttl=60 * 10, show_spinner=False)
def get_data():
    try:
        df, source = fetch_api(st.secrets["API_KEY"]), "API"
    except Exception as e:
        reason = safe_reason(e)
        print("API 호출 실패:", reason)  # 서버 로그용
        df = pd.read_csv(BACKUP_PATH, dtype={"계약년월": str})
        source = f"백업 자료, API 실패 원인: {reason}"
    return prepare(df), source, datetime.now().strftime("%Y-%m-%d %H:%M")


def data_caption(source, loaded_at, d):
    period = f"{d['계약년월'].min()[:4]}.{d['계약년월'].min()[4:]} ~ {d['계약년월'].max()[:4]}.{d['계약년월'].max()[4:]}"
    st.caption(f"데이터: 국토교통부 전월세 실거래가 ({source}) | 계약 기간 {period} | 불러온 시각 {loaded_at}")
