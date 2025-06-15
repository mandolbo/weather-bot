import requests
import datetime
import os
from pytz import timezone
from dotenv import load_dotenv

# .env 파일에서 API 키와 Webhook URL을 로드
load_dotenv()
SERVICE_KEY = os.environ["SERVICE_KEY"]  # 기상청 API 키
SLACK_HOOK = os.environ["SLACK_HOOK"]    # Slack Webhook URL

# 서울 격자 좌표 (nx, ny)
NX, NY = 60, 127

# 1) Base Time 계산 함수
#    - KST 기준 현재 시각(now_kst) 이전에 발표된 가장 최근 예보 시각을 찾음
#    - 기상청은 매 3시간 단위(0200, 0500, ...)로 예보를 발표함
#    - 발표 전(02시 이전)일 경우 어제 23시 예보 사용

def get_base_time(now_kst):
    times = ["0200", "0500", "0800", "1100", "1400", "1700", "2000", "2300"]
    candidates = []
    for t in times:
        hh, mm = int(t[:2]), int(t[2:])
        dt = datetime.datetime.combine(
            now_kst.date(),
            datetime.time(hh, mm),
            tzinfo=now_kst.tzinfo
        )
        candidates.append(dt)

    valid = [dt for dt in candidates if dt <= now_kst]
    if valid:
        return max(valid).strftime("%H%M")

    # 새벽 02시 이전에는 어제 23시 예보 사용
    yesterday_23 = datetime.datetime.combine(
        now_kst.date() - datetime.timedelta(days=1),
        datetime.time(23, 0),
        tzinfo=now_kst.tzinfo
    )
    return yesterday_23.strftime("%H%M")

# 2) 현재 시각을 UTC에서 KST로 변환
utc_now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
kst_timezone = timezone('Asia/Seoul')
now_kst = utc_now.astimezone(kst_timezone)

# 3) 발표 날짜와 시간 계산
base_time = get_base_time(now_kst)
base_date = now_kst.strftime("%Y%m%d")  # YYYYMMDD 형식

# 4) 기상청 단기예보 API 호출
url = (
    "https://apihub.kma.go.kr/api/typ02/openApi/"
    "VilageFcstInfoService_2.0/getVilageFcst"
)
params = {
    "authKey": SERVICE_KEY,
    "pageNo": 1,
    "numOfRows": 1000,
    "dataType": "JSON",
    "base_date": base_date,
    "base_time": base_time,
    "nx": NX,
    "ny": NY,
}
resp = requests.get(url, params=params, timeout=10)
resp.raise_for_status()
items = resp.json()["response"]["body"]["items"]["item"]

# 5) 받은 데이터를 (category, fcstTime) 키로 매핑
forecast = { (it["category"], it["fcstTime"]): it["fcstValue"] for it in items }

# 6) 시간대별 예보 시각 모음
period_times = {
    "오전": ["0800", "0900", "1000", "1100"],  # 8시~11시
    "오후": ["1200", "1300", "1400", "1500", "1600", "1700"],  # 12시~17시
    "저녁": ["1800", "1900", "2000", "2100", "2200", "2300"],  # 18시~23시
}

# 7) 우산 판단 함수
#    - PTY(강수 형태)와 PCP(강수량)를 우선 고려
#    - PTY가 0이 아니고 실제 강수량 > 0일 때만 우산 필요
#    - 그 외 POP/PCP 기준으로 보수적 판단

def need_umbrella(pop, pty, pcp):
    if pty != "0" and pcp > 0:      # 실제 비/눈 예보 + 강수량
        return True
    if pop >= 70:                     # 강수 확률 70% 이상
        return True
    if pcp >= 1.0:                    # 강수량 1mm 이상
        return True
    return False

# 8) PTY/SKY 우선순위 정의 (낮을수록 우선)
PTY_PRIORITY = {"1":1, "2":1, "3":1, "4":1, "5":2, "6":2, "7":2, "0":99}
SKY_PRIORITY = {"4":1, "3":2, "2":3, "1":4}

# 9) 결과 집계 및 메시지 조립
results = {}
for label, times_list in period_times.items():
    temps, pops, pcps, ptys, skys = [], [], [], [], []
    for t in times_list:
        temps.append(float(forecast.get(("TMP", t), 0)))
        pops.append(int(forecast.get(("POP", t), 0)))
        raw = forecast.get(("PCP", t), "강수없음")
        if raw in ("강수없음","적설없음","-",None,""):
            pcps.append(0.0)
        elif "mm 미만" in raw:             # 예: "1mm 미만"
            pcps.append(0.5)               # 대표값 0.5mm
        elif "~" in raw:                  # 예: "1~4.9"
            low, high = map(float, raw.split("~"))
            pcps.append((low+high)/2)
        else:
            try:
                pcps.append(float(raw))
            except ValueError:
                pcps.append(0.0)
        ptys.append(forecast.get(("PTY", t), "0"))
        skys.append(forecast.get(("SKY", t), "1"))

    avg_temp = sum(temps)/len(temps)
    max_pop  = max(pops)
    max_pcp  = max(pcps)
    final_pty = sorted(ptys, key=lambda x: PTY_PRIORITY.get(x,99))[0]
    final_sky = sorted(skys, key=lambda x: SKY_PRIORITY.get(x,4))[0]

    print(f"{label} 집계 – 기온={avg_temp:.1f}°C, POP={max_pop}%, PCP={max_pcp}mm, PTY={final_pty}, SKY={final_sky}")

    umbrella = "☔ 우산 챙기세요!" if need_umbrella(max_pop, final_pty, max_pcp) else ""

    if final_pty != "0":
        desc_map = {"1":"비","2":"비/눈","3":"눈","4":"소나기","5":"빗방울","6":"이슬비/눈날림","7":"눈날림"}
        desc = f"{desc_map.get(final_pty,'알 수 없음')} (강수확률 {max_pop}% )"
    else:
        sky_map = {"1":"맑음","2":"구름 조금","3":"구름 많음","4":"흐림"}
        desc = f"{sky_map.get(final_sky,'흐림')} (비 올 가능성 {max_pop}% )" if max_pop>=50 else sky_map.get(final_sky,'흐림')

    def outfit(temp):
        if temp >= 28:
            return "🥵 매우 더움 → 민소매, 반팔·반바지, 원피스"
        elif temp >= 23:
            return "☀️ 더움 → 반팔, 얇은 셔츠, 반바지, 면바지"
        elif temp >= 20:
            return "🌤 따뜻 → 얇은 가디건, 긴팔 면바지, 청바지"
        elif temp >= 17:
            return "🍃 선선 → 얇은 니트, 맨투맨, 가디건, 청바지"
        elif temp >= 12:
            return "🍂 시원 → 자켓, 가디건, 야상, 청바지, 면바지"
        elif temp >= 9:
            return "🍁 서늘 → 자켓, 트렌치코트, 야상, 니트, 청바지, 스타킹"
        elif temp >= 5:
            return "🧣 쌀쌀 → 코트, 가죽자켓, 히트텍, 니트, 레깅스"
        else:
            return "❄️ 매우 추움 → 패딩, 두꺼운 코트, 목도리, 기모제품"

    results[label] = {
        "temp": avg_temp,
        "pop": max_pop,
        "desc": desc,
        "outfit": outfit(avg_temp),
        "umbrella": umbrella,
    }

# 10) Slack 메시지 전송
today_str = now_kst.strftime("%m월 %d일 (%a)")
lines = [f"*{today_str} 서울 날씨 예보*"]
for lbl, info in results.items():
    lines.append(
        f"{lbl} *{info['temp']:.1f}°C* ... {info['desc']}\n"
        f"> 옷차림: {info['outfit']} {info['umbrella']}"
    )
text = "\n\n".join(lines)
requests.post(SLACK_HOOK, json={"text": text})
print("슬랙으로 예보 전송 완")
print("DEBUG ▶", now_kst, base_date, base_time)