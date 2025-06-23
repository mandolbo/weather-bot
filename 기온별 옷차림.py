###############################################################################
# 0. 비밀 환경변수(.env) 불러오기
#    - override=True  : 이미 등록된 환경변수도 .env 값으로 덮어쓴다
###############################################################################
from dotenv import load_dotenv
import os, requests, datetime, pathlib
from pytz import timezone

BASE_DIR = pathlib.Path(__file__).resolve().parent   # 스크립트 폴더
load_dotenv(BASE_DIR / ".env")      # 상대경로 → 경로 노출 없음
# load_dotenv(override=True) ← 필요할 때만 덮어쓰기

SERVICE_KEY = os.environ["SERVICE_KEY"]
SLACK_HOOK  = os.environ["SLACK_HOOK"]       # Slack Webhook URL

# (선택) 키 길이 확인용
# print("KEY LEN =", len(SERVICE_KEY), SERVICE_KEY[:8]+"...")

###############################################################################
# 1. 기본 상수 – 서울 격자 좌표
###############################################################################
NX, NY = 60, 127       # 종로구. 다른 지역은 값만 바꾸면 된다.

###############################################################################
# 2. base_time 계산 함수
###############################################################################
def ultra_base(now: datetime.datetime) -> str:
    """
    초단기 실황/예보용 base_time (HH30)
    - 45분 이전 호출 → 직전 HH30
    - 45분 이후 호출 → 현재 HH30
    """
    tgt = now - datetime.timedelta(hours=1) if now.minute < 45 else now
    return tgt.strftime("%H") + "30"

def village_base(now: datetime.datetime) -> str:
    """
    단기(동네) 예보용 base_time (HH00)
    - 02·05·08·11·14·17·20·23 시 중 가장 최근
    """
    slots = [2,5,8,11,14,17,20,23]
    h = max(s for s in slots if s <= now.hour)
    return f"{h:02d}00"

###############################################################################
# 3. 기상청 OPEN API 호출 함수 (공통)
###############################################################################
def fetch_kma(path:str, base_date:str, base_time:str) -> list[dict]:
    """
    path : getUltraSrtNcst / getUltraSrtFcst / getVilageFcst
    typ02 포털은 파라미터명이 authKey !!!
    성공 → item 리스트 반환, 실패 → 슬랙 경보 후 빈 리스트
    """
    url = (f"https://apihub.kma.go.kr/api/typ02/openApi/"
           f"VilageFcstInfoService_2.0/{path}")

    params = {
        "authKey":  SERVICE_KEY,   # ← 구버전은 serviceKey, 신버전은 authKey
        "dataType": "JSON",
        "numOfRows": 1000,
        "pageNo": 1,
        "base_date": base_date,
        "base_time": base_time,
        "nx": NX, "ny": NY,
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()                       # HTTP 오류 → 예외
        return r.json()["response"]["body"]["items"]["item"]
    except Exception as e:
        warn = f":rotating_light: KMA API 오류 · {path} · {e}"
        print(warn)
        requests.post(SLACK_HOOK, json={"text": warn})
        return []                                  # 비어 있으면 후속 로직이 건너뜀

###############################################################################
# 4. 현재 시각(한국) 및 base_time 계산
###############################################################################
KST = timezone("Asia/Seoul")
now = datetime.datetime.now(KST)

base_date = now.strftime("%Y%m%d")    # 오늘 날짜(YYYYMMDD)
u_base    = ultra_base(now)           # 초단기용 HH30
v_base    = village_base(now)         # 단기용   HH00

###############################################################################
# 5. API 세 번 호출
###############################################################################
ncst   = fetch_kma("getUltraSrtNcst", base_date, u_base)   # 실황 (지금)
ultra  = fetch_kma("getUltraSrtFcst", base_date, u_base)   # 30분 간격 6h
village= fetch_kma("getVilageFcst",   base_date, v_base)   # 3시간 간격 24h

###############################################################################
# 6. (category, date, time) → value 딕셔너리로 병합
#    실황은 obsrValue, 예보는 fcstValue 필드 사용
###############################################################################
fore: dict[tuple[str,str,str], str] = {}
for item in (ncst + ultra + village):
    d = item.get("fcstDate", item["baseDate"])   # 실황은 baseDate
    t = item.get("fcstTime", item["baseTime"])   # 실황은 baseTime
    val = item.get("fcstValue", item.get("obsrValue"))
    if val is not None:
        fore[(item["category"], d, t)] = val

###############################################################################
# 7. 오늘·내일 날짜 배열 / 조회 헬퍼
###############################################################################
tomorrow = (now + datetime.timedelta(days=1)).strftime("%Y%m%d")
DATES = [base_date, tomorrow]

def pick(cat:str, hhmm:str, default=None):
    """cat·시간 → 오늘→내일 순으로 찾기"""
    for d in DATES:
        v = fore.get((cat, d, hhmm))
        if v is not None:
            return v
    return default

###############################################################################
# 8. 시간대 구간 정의
###############################################################################
periods = {
    "오전":  [f"{h:02d}00" for h in range(8, 13)],
    "오후":  [f"{h:02d}00" for h in range(13, 18)],
    "저녁":  [f"{h:02d}00" for h in range(18, 24)],
}

###############################################################################
# 9. 우산·하늘·옷차림 보조 데이터
###############################################################################
PTY = {"0":"", "1":"비", "2":"비/눈", "3":"눈", "4":"소나기",
       "5":"빗방울", "6":"빗방울/눈날림", "7":"눈날림"}
SKY = {"1":"맑음", "2":"구름 조금", "3":"구름 많음", "4":"흐림"}

def need_umbrella(pop:int, pty:str, rn1:float) -> bool:
    return (pty!="0") or (rn1>=1.0) or (pop>=60)

def outfit(temp:float)->str:
    if temp>=28: return "🥵 민소매·반팔"
    if temp>=23: return "☀️ 반팔, 얇은 셔츠"
    if temp>=20: return "🌤 얇은 가디건"
    if temp>=17: return "🍃 맨투맨, 가디건"
    if temp>=12: return "🍂 자켓, 니트"
    if temp>= 5: return "🧣 코트, 히트텍"
    return        "❄️ 패딩, 목도리"

###############################################################################
# 10. 시간대별 계산 & Slack 메시지 조립
###############################################################################
lines=[]
for label, times in periods.items():
    temps, pops, rn1s, ptys, skys = [], [], [], [], []

    for t in times:
        temp = pick("TMP", t) or pick("T1H", t)   # TMP(3h) 우선, 없으면 T1H(1h/실황)
        if temp is None:
            continue

        pop  = int(pick("POP", t, 0))
        pty  = pick("PTY", t, "0")
        sky  = pick("SKY", t, "1")
        rn1_raw = pick("RN1", t, "0")

        # RN1 문자열 → mm 숫자
        if rn1_raw in ("강수없음","-",""): rn1=0.0
        elif "mm 미만" in str(rn1_raw):    rn1=0.5
        else:                              rn1=float(rn1_raw)

        temps.append(float(temp)); pops.append(pop)
        rn1s.append(rn1); ptys.append(pty); skys.append(sky)

    if not temps:            # 해당 구간에 아무 데이터도 없으면 건너뜀
        continue

    avg_temp = sum(temps)/len(temps)
    max_pop  = max(pops)
    max_rn1  = max(rn1s)
    final_pty= sorted(ptys, key=lambda x:(x=="0", x))[0]
    final_sky= SKY[sorted(skys)[0]]

    desc = PTY[final_pty] if final_pty!="0" else final_sky
    umb  = "☔ 우산!" if need_umbrella(max_pop, final_pty, max_rn1) else ""

    lines.append(
        f"{label} *{avg_temp:.1f}°C* · {desc} (강수확률 {max_pop}%)\n"
        f"> 옷차림 : {outfit(avg_temp)} {umb}"
    )

###############################################################################
# 11. Slack 전송
###############################################################################
if lines:
    title = f"*{now.strftime('%m월 %d일 (%a)')} 서울 날씨*"
    message_text=f"@channel {title}\n\n" + "\n\n".join(lines)
    payload = {"text": message_text}
    requests.post(SLACK_HOOK, json=payload)
    print("✅ Slack 전송 완료")
else:
    warn=":warning: 예보 데이터가 없어 메시지를 보내지 못했습니다."
    print(warn); requests.post(SLACK_HOOK, json={"text":warn})

###############################################################################
# (끝) – 하루 한 번 크론/작업스케줄러/깃허브액션 등에 올리면
#        최신 서울 예보를 슬랙으로 자동 알림받을 수 있습니다.
###############################################################################
