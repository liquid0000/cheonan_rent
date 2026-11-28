"""loader.py - 모든 화면이 같이 쓰는 데이터 불러오기 (캐시 적용)"""
from datetime import datetime

import streamlit as st

from data import load_data, prepare


@st.cache_data(ttl=60 * 60 * 24, show_spinner="국토부 실거래 데이터를 불러오는 중입니다 (처음 한 번만 1분 정도 걸립니다)")
def get_data():
    """API로 받은 데이터를 하루 동안 저장해두고 재사용한다 (매번 72번 호출하지 않도록)"""
    df, source = load_data(st.secrets["API_KEY"])
    return prepare(df), source, datetime.now().strftime("%Y-%m-%d %H:%M")


def data_caption(source, loaded_at, d):
    period = f"{d['계약년월'].min()[:4]}.{d['계약년월'].min()[4:]} ~ {d['계약년월'].max()[:4]}.{d['계약년월'].max()[4:]}"
    st.caption(f"데이터: 국토교통부 전월세 실거래가 ({source}) | 계약 기간 {period} | 불러온 시각 {loaded_at}")
