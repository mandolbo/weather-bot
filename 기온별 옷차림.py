import requests, datetime,os

from dotenv import load_dotenv
load_dotenv()                         # 실제 로드

# 사용자 설정 
SERVICE_KEY = os.environ["SERVICE_KEY"]  # 기상청 API


HOOK = os.environ["SLACK_HOOK"] # Slack hook




# 서울 격자 좌표 (nx, ny)
NX, NY = 60, 127

# Base Time 계산 함수 (가장 최근 예보 발표 시각 설정)
def get_base_time(now):
    # 기상청 단기예보 발표 시각(매 3시간 단위)
    times = ["0200","0500","0800","1100","1400","1700","2000","2300"]
    candidates = []
    for t in times:
        hh, mm = int(t[:2]), int(t[2:])
        dt = datetime.datetime.combine(now.date(), datetime.time(hh,mm))
        candidates.append(dt)
    # 지금(now) 이전 중 가장 큰 시각
    valid = [dt for dt in candidates if dt <= now]
    if valid:
        return max(valid).strftime("%H%M")
    # 만약 새벽 02시 발표 전이라면, 어제 23시 발표 사용
    yesterday_23 = datetime.datetime.combine(now.date()-datetime.timedelta(days=1), datetime.time(23,0))
    return yesterday_23.strftime("%H%M")

# 예보 API 호출 및 데이터 파싱
now = datetime.datetime.now()
base_time = get_base_time(now)
base_date = now.strftime("%Y%m%d")

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

resp = requests.get(url, params=params, timeout=10 )
resp.raise_for_status()
items = resp.json()["response"]["body"]["items"]["item"]


# (category, fcstTime) → value 맵 생성
forecast = { (it["category"], it["fcstTime"] ): it["fcstValue"] for it in items}


# 시간대별 예보 가져오기1
periods = {
    "오전" : "0800",
    "오후" : "1400",
    "저녁" : "2000"
}

## 우산 판단 함수
def need_umbrella(pop,pty,pcp):
#비, 눈, 예보 + 실제 강수량 값이 3mm 이상상 있을 때만 우산 필요
    if pty != "0" and pcp >= 3.0 :
      return True
# 비 안 와도 확률이 50%이상이면
    if pop >= 50 and pcp >= 3.0 :
        return True
    return False

# 시간대별 예보 가져오기2
results = {}
for label, t in periods.items():
    TEMP = float(forecast.get(("TMP", t),0)) # 예측 기온
    POP = int(forecast.get(("POP",t),0)) # 강수 확률(%)
    PTY = forecast.get(("PTY",t),"0") # 강수 형태 코드
    SKY = forecast.get(("SKY", t), "1") # 하늘 상태 코드

    PCP_RAW = forecast.get(("PCP",t), "강수없음") #강수량 rawdata 코드
    PCP = 0.0 if PCP_RAW in ("강수없음", "적설없음") else float(PCP_RAW) # 강수량 : 강수X, 적설 X => 0.0 이외엔 실수화

    print(f"{label} 예보 – POP={POP}%  PTY={PTY}  SKY={SKY}  PCP={PCP}")


    ##1 우산 안내
    umbrella = "☔ 우산 챙기세요!" if need_umbrella(POP,PTY,PCP) else ""

    ##2 날씨 설명 결정
    if PTY != "0": #비 or 눈이 오는 경우
        desc = {"1":"비", "2":"눈", "3":"진눈깨비"}.get(PTY,"소나기") #1,2,3 이외 기본값을 "소나기"로 설정
    else: # 비 or 눈이 안오는 경우
        desc = {"1":"맑음","3":"구름 많음"}.get(SKY,"흐림")
    
    ##3 옷차림 추천 함수
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
        


    
    

    results[label]={
        "temp": TEMP,
        "pop": POP,
        "desc": desc,
        "outfit": outfit(TEMP),
        "umbrella": umbrella
    }


# Slack 메시지 조립 & 전송
today= now.strftime("%m월 %d일 (%a)")
lines = [f"*{today} 서울 날씨 예보*"] # f-string 문법구조로 문자열 내부에 변수를 넣을 수 있는 기능함
for label, info in results.items():
    lines.append(
        f"{label} *{info['temp']:.1f}°C* ... {info['desc']}\n"
        f"> 옷차림: {info['outfit']} {info['umbrella']}"
    )
    

    
text = "\n\n".join(lines)

requests.post(HOOK, json={"text":text})
print("슬랙으로 예보 전송 완")



