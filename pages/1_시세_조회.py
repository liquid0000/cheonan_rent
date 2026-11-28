"""시세 조회 화면"""
import pandas as pd
import streamlit as st

from data import AREA_LABELS, MIN_COUNT
from loader import get_data, data_caption

st.set_page_config(page_title="시세 조회", layout="wide")
st.title("시세 조회")
d, source, loaded_at = get_data()

# --- 1) 동네별 비교 (거래가 충분한 곳만) ---
st.subheader("동네별 월세 중앙값")
summary = (d.groupby(["구", "지역"])
             .agg(거래건수=("월세", "size"), 월세중앙값=("월세", "median"),
                  보증금중앙값=("보증금", "median"), 면적중앙값=("면적", "median"))
             .reset_index())
enough = summary[summary["거래건수"] >= MIN_COUNT].sort_values("거래건수", ascending=False)
st.bar_chart(enough.set_index("지역")["월세중앙값"], y_label="월세 중앙값 (만원)")
st.caption(f"거래 {MIN_COUNT}건 이상인 지역만 표시")

# --- 2) 지역 선택 ---
st.subheader("동네 자세히 보기")
order = summary.sort_values("거래건수", ascending=False)
options = [f"{r.지역} ({r.구}, {r.거래건수}건)" for r in order.itertuples()]
choice = st.selectbox("동네 선택", options)
region = choice.split(" (")[0]
band = st.radio("면적", ["전체"] + AREA_LABELS, horizontal=True)

sel = d[d["지역"] == region]
if band != "전체":
    sel = sel[sel["면적구간"] == band]

if len(sel) == 0:
    st.warning("해당 조건의 거래가 없습니다.")
    st.stop()
if len(sel) < MIN_COUNT:
    st.warning(f"거래가 {len(sel)}건뿐이라 시세가 정확하지 않을 수 있습니다.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("거래 건수", f"{len(sel):,}건")
c2.metric("월세 중앙값", f"{sel['월세'].median():.0f}만원")
c3.metric("월세 범위 (중간 50%)", f"{sel['월세'].quantile(.25):.0f}~{sel['월세'].quantile(.75):.0f}만원")
c4.metric("보증금 중앙값", f"{sel['보증금'].median():,.0f}만원")

left, right = st.columns(2)
with left:
    st.markdown("**월세 분포** (5만원 단위)")
    bins = (sel["월세"] // 5 * 5).astype(int)
    dist = bins.value_counts().sort_index()
    dist.index = [f"{i}~{i + 4}" for i in dist.index]
    st.bar_chart(dist, y_label="거래 건수")
with right:
    st.markdown("**월별 거래 건수와 월세 중앙값**")
    monthly = sel.groupby("계약년월").agg(거래건수=("월세", "size"), 월세중앙값=("월세", "median"))
    monthly.index = [f"{m[:4]}.{m[4:]}" for m in monthly.index]
    st.line_chart(monthly["월세중앙값"], y_label="월세 중앙값 (만원)")
    st.bar_chart(monthly["거래건수"], y_label="거래 건수")

st.markdown("**주택 유형별**")
st.dataframe(sel.groupby("유형").agg(거래건수=("월세", "size"), 월세중앙값=("월세", "median"),
                                    보증금중앙값=("보증금", "median")), width="stretch")
data_caption(source, loaded_at, d)
