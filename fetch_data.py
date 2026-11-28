"""
fetch_data.py - 내 컴퓨터에서 한 번 실행해서
1) API 키가 제대로 작동하는지 확인하고
2) 최근 12개월 데이터를 data/backup.csv 로 저장한다 (API 장애 대비 백업)

실행: python fetch_data.py
"""
import re
from data import fetch_all, clean, BACKUP_PATH, recent_months

# secrets.toml 에서 키 읽기
text = open(".streamlit/secrets.toml", encoding="utf-8").read()
api_key = re.search(r'API_KEY\s*=\s*"([^"]+)"', text).group(1)

months = recent_months()
print(f"수집 기간: {months[0]} ~ {months[-1]}")

raw = fetch_all(api_key, months, progress=lambda i, n, msg: print(f"[{i}/{n}] {msg}"))
print("\n원본 항목 이름:", list(raw.columns))
raw.to_csv("data/raw.csv", index=False, encoding="utf-8-sig")  # 원본도 보관 (정리 방식 바꿀 때 재수집 불필요)

df = clean(raw)
df.to_csv(BACKUP_PATH, index=False, encoding="utf-8-sig")

print(f"\n저장 완료: {BACKUP_PATH}")
print(f"전체 {len(df):,}건")
print(df.groupby("유형").size())
print("\n월세 계약:", (df["월세"] > 0).sum(), "건")
print("면적 빈칸:", df["면적"].isna().sum(), "건")
