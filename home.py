"""home.py - 첫 화면 (홈)"""
import streamlit as st

from loader import get_data, data_caption


st.title("천안 대학가 자취방 시세 체크 및 계약 안전 가이드")
st.write("국토교통부 전월세 실거래 자료를 바탕으로 천안 지역 자취방(월세, 전용 33㎡ 이하) 시세를 보여주고, "
         "계약할 때 확인해야 할 것들을 정리한 서비스입니다.")

d, source, loaded_at = get_data()

# 핵심 수치 4개
c1, c2, c3, c4 = st.columns(4)
c1.metric("분석 거래 건수", f"{len(d):,}건")
c2.metric("월세 중앙값", f"{d['월세'].median():.0f}만원")
c3.metric("보증금 중앙값", f"{d['보증금'].median():,.0f}만원")
c4.metric("월세 30만원 이하 비율", f"{(d['월세'] <= 30).mean() * 100:.1f}%")

st.subheader("메뉴 안내")
st.markdown("""
- **시세 조회**: 동네와 면적을 고르면 월세/보증금 시세와 월별 추이를 보여줍니다.
- **조건 판정**: 보고 있는 방의 조건을 넣으면 시세보다 싼지 비싼지 알려줍니다.
- **계약 가이드**: 계약 전, 당일, 후에 확인할 것과 보증금 보호 자가진단
- **지원 제도**: 청년이 받을 수 있는 월세 지원 제도 안내
""")

st.info("이 서비스의 시세는 실제 신고된 계약을 기준으로 합니다. 신고되지 않은 계약과 관리비는 반영되지 않으니 참고용으로 활용하세요.")
data_caption(source, loaded_at, d)
