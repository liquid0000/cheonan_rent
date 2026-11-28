"""조건 판정 화면: 내가 보고 있는 방이 시세보다 싼지 비싼지"""
import streamlit as st

from data import reference_group, judge
from loader import get_data, data_caption

st.set_page_config(page_title="조건 판정", layout="wide")
st.title("내 조건 판정")
st.write("보고 있는 방의 조건을 입력하면, 같은 동네 비슷한 면적의 실제 거래와 비교합니다.")
d, source, loaded_at = get_data()

order = d["지역"].value_counts().index.tolist()
with st.form("input"):
    c1, c2 = st.columns(2)
    region = c1.selectbox("동네", order)
    area = c2.number_input("전용면적 (㎡)", min_value=5.0, max_value=33.0, value=23.0, step=0.5,
                           help="원룸은 보통 16-25㎡ 정도입니다. 1평은 약 3.3㎡")
    c3, c4 = st.columns(2)
    deposit = c3.number_input("보증금 (만원)", min_value=0, max_value=5000, value=300, step=50)
    rent = c4.number_input("월세 (만원)", min_value=1, max_value=200, value=40, step=1)
    submitted = st.form_submit_button("판정하기")

if submitted:
    group, desc = reference_group(d, region, area)
    verdict, p25, p75, pct = judge(rent, group)

    color = {"저렴": "green", "적정": "blue", "비쌈": "red"}[verdict]
    st.markdown(f"### 판정 결과: :{color}[{verdict}]")
    st.write(f"비교 대상: **{desc}**, 실거래 {len(group):,}건")

    c1, c2, c3 = st.columns(3)
    c1.metric("내 월세", f"{rent}만원")
    c2.metric("비교 대상 월세 중앙값", f"{group['월세'].median():.0f}만원",
              delta=f"{rent - group['월세'].median():+.0f}만원", delta_color="inverse")
    c3.metric("나보다 싼 거래 비율", f"{pct:.0f}%")

    st.write(f"비교 대상 중간 50%의 월세는 **{p25:.0f}-{p75:.0f}만원**입니다. "
             f"{p25:.0f}만원 이하면 저렴, {p75:.0f}만원 이상이면 비쌈으로 판정합니다.")

    dep_med = group["보증금"].median()
    if deposit < dep_med / 2:
        st.info(f"보증금이 비교 대상 중앙값({dep_med:,.0f}만원)보다 많이 낮습니다. 보증금이 낮으면 월세가 높은 경우가 많으니 함께 고려하세요.")
    elif deposit > dep_med * 2:
        st.info(f"보증금이 비교 대상 중앙값({dep_med:,.0f}만원)보다 많이 높습니다. 보증금이 높은 만큼 월세가 낮아야 정상입니다. "
                "보증금이 클수록 '계약 가이드'의 보증금 보호 자가진단을 꼭 확인하세요.")

    st.caption("판정은 월세만 기준으로 하며, 관리비, 옵션, 건물 상태는 반영되지 않습니다.")
data_caption(source, loaded_at, d)
