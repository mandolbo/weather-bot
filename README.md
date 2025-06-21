# 📊 DART 재무제표 분석 플랫폼

한국 기업의 재무제표를 분석하고 AI 기반 인사이트를 제공하는 웹 애플리케이션입니다.

## 🎯 소개
**Apple 디자인 스타일의 스마트 재무분석 플랫폼**
- DART API를 활용한 실시간 재무제표 데이터 조회
- AI(Gemini) 기반 지능형 재무분석 
- 분기별/다년도 비교 분석 및 시각화
- 반응형 모던 UI/UX (한글 완전 지원)

## ✨ 주요 기능

### 📊 재무제표 분석
- 🏢 **기업 검색**: 한국 상장기업 실시간 검색
- 📈 **재무제표 분석**: 재무상태표, 손익계산서, 현금흐름표, 자본변동표
- 🔍 **별도/연결 재무제표 비교**: 실제 데이터 차이 확인 가능
- 📊 **분기별/연도별 비교**: 시계열 데이터 분석

### 🤖 AI 분석 기능
- 🤖 **AI 재무분석**: Gemini AI 기반 전문적 분석

### 📈 시각화 기능
- **다양한 차트**: 막대, 선형, 도넛 차트 지원
- **한글 단위 표시**: 조, 억, 만원 단위 자동 변환
- **인터랙티브 UI**: Apple 스타일 카드 기반 인터페이스

## 🛠 기술 스택
- **Backend**: Python Flask, SQLite
- **Frontend**: Vanilla JavaScript, Chart.js
- **API**: DART OpenAPI, Google Gemini AI
- **Design**: Apple Design System (SF Pro Display, iOS Colors)

## 📁 프로젝트 구조
```
├─ app.py                    # Flask 메인 서버
├─ get_financial_data.py     # DART API 연동 모듈
├─ build_corpcode_db.py      # 기업코드 DB 구축
├─ corpcode.db              # SQLite 기업코드 데이터베이스
├─ .env                     # 환경변수 (API 키 관리)
├─ requirements.txt         # Python 패키지 목록
├─ templates/
│    └─ index.html          # 메인 웹 인터페이스
└─ README.md               # 프로젝트 문서
```

## 🚀 설치 및 실행

### 로컬 실행

```bash
# 저장소 클론
git clone <repository-url>
cd python-project

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 API 키 설정

# 데이터베이스 생성
python build_corpcode_db.py

# 애플리케이션 실행
python app.py
```

### 환경변수 설정 (.env 파일)

```env
# DART API 키 (필수)
OPEN_DART_API_KEY=your_dart_api_key

# Gemini AI API 키 (선택사항 - AI 분석 기능용)
GEMINI_API_KEY=your_gemini_api_key
```

## 🌐 **완전 무료 배포 가이드** 💰

### 🏆 **1순위: Render (추천!)**

**✅ 완전 무료, 신용카드 불필요**
- 무료 한도: 월 750시간 (24시간 운영 가능)
- 자동 SSL, 커스텀 도메인 지원
- 자동 배포, 로그 확인 쉬움

#### 📋 Render 배포 단계:
1. **[Render 가입](https://render.com)** (무료, 신용카드 불필요)
2. **"New Web Service"** 클릭
3. **GitHub 저장소 연결**
4. **설정값 입력:**
   ```
   Name: dart-financial-analysis (원하는 이름)
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python app.py
   ```
5. **Environment Variables 추가:**
   ```
   OPEN_DART_API_KEY = your_dart_api_key
   GEMINI_API_KEY = your_gemini_api_key  
   PORT = 10000
   ```
6. **"Create Web Service"** 클릭
7. **배포 완료!** (약 5-10분 소요)

### 🥈 **2순위: Replit**

**✅ 코드 편집 + 배포 동시 가능**
- 무료 한도: Always On 기능 제한적
- 브라우저에서 코드 편집 가능
- 즉시 배포 및 테스트

#### 📋 Replit 배포 단계:
1. **[Replit 가입](https://replit.com)** (무료)
2. **"Import from GitHub"** 선택
3. **저장소 URL 입력**
4. **Secrets 탭에서 환경변수 추가:**
   ```
   OPEN_DART_API_KEY = your_dart_api_key
   GEMINI_API_KEY = your_gemini_api_key
   ```
5. **Run 버튼 클릭**
6. **자동 배포 완료!**

### 🥉 **3순위: PythonAnywhere**

**✅ Python 전용 호스팅**
- 무료 한도: 1개 웹앱, 제한적 CPU
- Python 개발환경 최적화
- 간단한 설정

#### 📋 PythonAnywhere 배포 단계:
1. **[PythonAnywhere 가입](https://www.pythonanywhere.com)** (무료)
2. **"Web" 탭에서 "Add a new web app"**
3. **Flask 선택**
4. **GitHub에서 코드 가져오기**
5. **환경변수 설정**
6. **웹앱 활성화**

## 💡 **완전 무료 플랫폼 비교표**

| 플랫폼 | 가격 | 장점 | 단점 | 추천도 |
|--------|------|------|------|---------|
| **Render** | 🆓 완전무료 | SSL, 도메인, 750시간 | 30일 비활성시 삭제 | ⭐⭐⭐⭐⭐ |
| **Replit** | 🆓 무료/유료 | 코드편집 가능 | Always On 제한 | ⭐⭐⭐⭐ |
| **PythonAnywhere** | 🆓 무료/유료 | Python 최적화 | CPU 제한 심함 | ⭐⭐⭐ |

## 🎯 **초보자 추천 순서**

### **Step 1: Render로 시작** (가장 쉬움)
- 회원가입 → GitHub 연결 → 환경변수 설정 → 배포 완료
- **소요시간: 10분**

### **Step 2: 도메인 확인**
- `https://your-app-name.onrender.com` 형태로 배포됨
- SSL 인증서 자동 적용됨

### **Step 3: 테스트**
- 기업 검색 테스트
- AI 분석 기능 테스트
- 별도/연결 재무제표 비교 테스트

## 📋 API 키 발급 방법

### DART API 키
1. [DART 홈페이지](https://opendart.fss.or.kr) 접속
2. 회원가입 및 로그인
3. API 키 발급 신청
4. 승인 후 사용 (보통 1-2일 소요)

### Gemini API 키
1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. Google 계정으로 로그인
3. API 키 생성
4. 즉시 사용 가능

## 🚨 **무료 배포 시 주의사항**

### 1. **Render 무료 플랜 제한**
- 30일간 미사용 시 서비스 자동 삭제
- 해결책: 월 1회 이상 접속하기

### 2. **환경변수 필수 설정**
- `OPEN_DART_API_KEY` 없으면 기업 검색 불가
- `GEMINI_API_KEY` 없으면 AI 분석 불가

### 3. **성능 최적화**
- 무료 플랜은 성능 제한 있음
- 동시 사용자 10명 이하 권장

## 🐛 트러블슈팅

### 1. 배포 실패 시
- 환경변수 확인
- requirements.txt 파일 확인
- 로그에서 오류 메시지 확인

### 2. 사이트 접속 안 될 때
- PORT 환경변수 확인 (Render: 10000)
- app.py의 포트 설정 확인

### 3. 기능 작동 안 할 때
- API 키 올바른지 확인
- 로그에서 에러 메시지 확인

## 📞 지원

문제 발생 시 GitHub Issues에 등록해주세요.

## 📄 라이선스

MIT License

---

**🎉 완전 무료 배포 성공 체크리스트**
- [ ] Render 회원가입 완료
- [ ] GitHub 저장소 연결 완료
- [ ] 환경변수 설정 완료 (DART + Gemini API 키)
- [ ] 배포 완료 및 URL 확인
- [ ] 기업 검색 기능 테스트 완료
- [ ] AI 분석 기능 테스트 완료
- [ ] 별도/연결 재무제표 비교 기능 테스트 완료 