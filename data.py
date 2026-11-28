"""
data.py - 국토교통부 전월세 실거래 API에서 데이터를 받아와 정리하는 파일

흐름: API 호출(유형 3개 x 구 2개 x 12개월) -> XML 해석 -> 표(DataFrame)로 합치기 -> 숫자 정리
API가 실패하면 data/backup.csv(미리 받아둔 백업)를 대신 사용한다.
"""
import os
import time
import xml.etree.ElementTree as ET
from datetime import date

import pandas as pd
import requests

# ---------------------------------------------------------------
# 1. 기본 설정
# ---------------------------------------------------------------
BASE_URL = "https://apis.data.go.kr/1613000"

# 주택 유형별 API 주소 (공공데이터포털에서 활용신청한 3개)
APIS = {
    "연립다세대": "RTMSDataSvcRHRent/getRTMSDataSvcRHRent",
    "오피스텔": "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",
    "단독다가구": "RTMSDataSvcSHRent/getRTMSDataSvcSHRent",
}

# 천안시 구 코드 (법정동코드 앞 5자리)
REGIONS = {"44131": "동남구", "44133": "서북구"}

BACKUP_PATH = os.path.join(os.path.dirname(__file__), "data", "backup.csv")

# API마다 면적 항목 이름이 다를 수 있어서, 있는 것을 순서대로 찾아 쓴다
AREA_CANDIDATES = ["excluUseAr", "totalFloorAr", "contractArea", "dealArea"]


def recent_months(n=12):
    """오늘 기준으로 '다 끝난' 최근 n개월을 YYYYMM 문자열 목록으로 돌려준다.
    (이번 달은 신고가 아직 다 안 들어와서 제외)"""
    y, m = date.today().year, date.today().month
    out = []
    for _ in range(n):
        m -= 1
        if m == 0:
            y, m = y - 1, 12
        out.append(f"{y}{m:02d}")
    return sorted(out)


# ---------------------------------------------------------------
# 2. API 한 번 호출 (유형 1개, 구 1개, 1개월)
# ---------------------------------------------------------------
def fetch_one(api_key, kind, lawd_cd, ym):
    """한 달치 데이터를 받아서 dict 목록으로 돌려준다.
    한 번에 최대 1000건씩 받을 수 있어서, 더 많으면 다음 페이지를 이어서 받는다."""
    rows, page = [], 1
    while True:
        params = {
            "serviceKey": api_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": ym,
            "numOfRows": 1000,
            "pageNo": page,
        }
        res = requests.get(f"{BASE_URL}/{APIS[kind]}", params=params, timeout=30)
        res.raise_for_status()
        try:
            root = ET.fromstring(res.content)
        except ET.ParseError:
            # XML이 아닌 응답(예: 'Unauthorized' 같은 일반 문자)이 온 경우
            raise RuntimeError(f"API 응답 형식 오류: {res.text[:60]}")

        # 결과 코드 확인 (정상: 000 또는 00)
        code = root.findtext(".//resultCode")
        if code not in ("000", "00"):
            # 키 오류 등은 형식이 다른 오류 응답(returnAuthMsg)으로 오기도 해서 둘 다 확인
            msg = root.findtext(".//resultMsg") or root.findtext(".//returnAuthMsg")
            raise RuntimeError(f"API 오류 {code or root.findtext('.//returnReasonCode')}: {msg}")

        # <item> 하나가 거래 1건. 안의 항목을 그대로 dict로 만든다
        for item in root.iter("item"):
            r = {child.tag: (child.text or "").strip() for child in item}
            r["유형"] = kind
            r["구"] = REGIONS[lawd_cd]
            rows.append(r)

        total = int(root.findtext(".//totalCount") or 0)
        if page * 1000 >= total:
            break
        page += 1
    return rows


# ---------------------------------------------------------------
# 3. 전체 수집 (3 x 2 x 12 = 72번 호출)
# ---------------------------------------------------------------
def fetch_all(api_key, months=None, progress=None):
    months = months or recent_months()
    raw = []
    jobs = [(k, c, m) for k in APIS for c in REGIONS for m in months]
    for i, (kind, code, ym) in enumerate(jobs, 1):
        raw += fetch_one(api_key, kind, code, ym)
        if progress:
            progress(i, len(jobs), f"{kind} {REGIONS[code]} {ym}")
        time.sleep(0.1)  # 서버에 부담 주지 않게 살짝 쉬기
    return pd.DataFrame(raw)


# ---------------------------------------------------------------
# 4. 정리: 필요한 열만 한글 이름으로 남기고 숫자로 바꾸기
# ---------------------------------------------------------------
def to_number(s):
    """'1,000' 같은 문자를 숫자 1000으로 바꾼다 (빈칸은 NaN)"""
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def pick_area(df):
    """면적 열 합치기: 연립다세대/오피스텔은 excluUseAr(전용면적),
    단독다가구는 totalFloorAr(계약면적)에 값이 들어있어서, 행마다 있는 값을 채워 넣는다"""
    area = pd.Series(float("nan"), index=df.index)
    for c in AREA_CANDIDATES:
        if c in df.columns:
            area = area.fillna(to_number(df[c]))
    return area


def clean(df):
    out = pd.DataFrame({
        "유형": df["유형"],
        "구": df["구"],
        "동": df["umdNm"].str.strip(),
        "면적": pick_area(df),
        "보증금": to_number(df["deposit"]),        # 단위: 만원
        "월세": to_number(df["monthlyRent"]),      # 단위: 만원
        "계약년월": df["dealYear"].str.zfill(4) + df["dealMonth"].str.zfill(2),
        "계약일": to_number(df["dealDay"]),
        "건축년도": to_number(df["buildYear"]) if "buildYear" in df else pd.NA,
        "계약구분": df["contractType"] if "contractType" in df else "",
    })
    return out


# ---------------------------------------------------------------
# 5. 화면에서 쓰는 함수: API 시도 -> 실패 시 백업
# ---------------------------------------------------------------
def load_data(api_key):
    """정리된 전체 데이터와 출처('API' 또는 '백업')를 돌려준다."""
    try:
        df = clean(fetch_all(api_key))
        return df, "API"
    except Exception as e:  # 네트워크 장애, 키 오류 등
        reason = safe_reason(e)
        print("API 호출 실패:", reason)
        if os.path.exists(BACKUP_PATH):
            return pd.read_csv(BACKUP_PATH, dtype={"계약년월": str}), f"백업 자료, API 실패 원인: {reason}"
        raise


def safe_reason(e):
    """실패 원인을 화면에 보여줄 수 있는 형태로 줄인다.
    requests 오류 메시지에는 API 키가 들어간 주소가 포함되므로 메시지 전체는 절대 쓰지 않는다."""
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        return f"HTTP {e.response.status_code}"
    if isinstance(e, RuntimeError):      # 직접 만든 오류 (키가 들어있지 않음)
        return str(e)
    return type(e).__name__              # 예: ConnectTimeout, ConnectionError


def monthly_rent_small(df, max_area=33, max_deposit=5000):
    """자취방 기준 데이터만 남긴다:
    월세 계약(월세 > 0), 전용 33㎡ 이하(원룸~1.5룸), 보증금 5천만원 이하(이상치 제외)"""
    d = df[(df["월세"] > 0) & (df["면적"] <= max_area) & (df["보증금"] <= max_deposit)]
    return d.copy()


# ---------------------------------------------------------------
# 6. 분석용 가공: 지역(동/읍면)과 면적 구간 붙이기
# ---------------------------------------------------------------
AREA_BANDS = [0, 20, 33]                     # 면적 구간 경계 (㎡)
AREA_LABELS = ["20㎡ 이하 (좁은 원룸)", "20-33㎡ (원룸, 1.5룸)"]
MIN_COUNT = 30                               # 판정에 필요한 최소 거래 건수


def prepare(df):
    """자취방 기준으로 거른 뒤, 분석에 쓸 열을 붙인다.
    - 지역: '성환읍 성월리'처럼 리까지 나오는 읍면은 '성환읍'으로 묶음 (리 단위는 거래가 너무 적어서)
    - 면적구간: 20㎡ 이하 / 20-33㎡"""
    d = monthly_rent_small(df)
    d["지역"] = d["동"].str.split().str[0]
    d["면적구간"] = pd.cut(d["면적"], AREA_BANDS, labels=AREA_LABELS)
    return d


def area_label(area):
    return AREA_LABELS[0] if area <= AREA_BANDS[1] else AREA_LABELS[1]


# ---------------------------------------------------------------
# 7. 조건 판정: 비교 대상을 고르고 내 월세가 어디쯤인지 계산
# ---------------------------------------------------------------
def reference_group(d, region, area):
    """판정에 쓸 비교 집단을 고른다. 건수가 MIN_COUNT 미만이면 범위를 넓힌다.
    1순위: 같은 지역 + 같은 면적구간 / 2순위: 같은 지역 전체 / 3순위: 같은 구 + 같은 면적구간"""
    band = area_label(area)
    same_region = d[d["지역"] == region]
    g = same_region[same_region["면적구간"] == band]
    if len(g) >= MIN_COUNT:
        return g, f"{region}, {band}"
    if len(same_region) >= MIN_COUNT:
        return same_region, f"{region} 전체 (면적별 거래가 적어 면적 구분 없이 비교)"
    gu = same_region["구"].iloc[0] if len(same_region) else None
    g = d[(d["구"] == gu) & (d["면적구간"] == band)] if gu else d[d["면적구간"] == band]
    return g, f"{gu or '천안'} 전체, {band} ({region}은 거래가 적어 범위를 넓혀 비교)"


def judge(rent, group):
    """하위 25% 이하면 저렴, 상위 25% 이상이면 비쌈, 그 사이는 적정"""
    p25, p75 = group["월세"].quantile(0.25), group["월세"].quantile(0.75)
    pct = (group["월세"] < rent).mean() * 100        # 나보다 싼 거래의 비율
    if rent <= p25:
        verdict = "저렴"
    elif rent >= p75:
        verdict = "비쌈"
    else:
        verdict = "적정"
    return verdict, p25, p75, pct
