"""app.py - 시작 파일: 메뉴(왼쪽 사이드바) 구성만 담당한다
st.navigation을 쓰면 메뉴 이름을 파일 이름 대신 원하는 이름(홈 등)으로 정할 수 있다"""
import streamlit as st

st.set_page_config(page_title="천안 자취방 시세 체크", layout="wide")

pg = st.navigation([
    st.Page("home.py", title="홈", default=True),
    st.Page("pages/1_시세_조회.py", title="시세 조회"),
    st.Page("pages/2_조건_판정.py", title="조건 판정"),
    st.Page("pages/3_계약_가이드.py", title="계약 가이드"),
    st.Page("pages/4_지원_제도.py", title="지원 제도"),
])
pg.run()
