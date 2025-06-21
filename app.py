from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
from get_financial_data import get_financial_data
import requests
from datetime import date
import json
import os

# 환경변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ 환경변수 파일(.env)을 성공적으로 로드했습니다.")
except Exception as e:
    print(f"⚠️ 환경변수 파일 로드 실패: {e}")

# Gemini AI 설정
try:
    import google.generativeai as genai
    
    # 환경변수에서 API 키 가져오기
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        AI_ENABLED = True
        print("✅ Gemini AI가 성공적으로 초기화되었습니다.")
    else:
        model = None
        AI_ENABLED = False
        print("⚠️ GEMINI_API_KEY가 .env 파일에 설정되지 않았습니다. AI 분석 기능이 비활성화됩니다.")
        
except ImportError as e:
    model = None
    AI_ENABLED = False
    print(f"⚠️ Google Generative AI 패키지를 찾을 수 없습니다: {e}")
    print("   pip install google-generativeai 명령어로 설치해주세요.")
except Exception as e:
    model = None
    AI_ENABLED = False
    print(f"❌ Gemini AI 초기화 중 오류 발생: {e}")

app = Flask(__name__)
CORS(app)  # CORS 지원
DB_PATH = 'corpcode.db'

# 재무제표 계정 순서 정의 (공시 순서 반영)
ACCOUNT_ORDER = {
    'BS': {
        '자산': [
            '자산총계', '자산총액',
            '유동자산', '유동자산계',
            '현금및현금성자산', '현금및현금성자산계',
            '단기금융상품', '단기금융상품계',
            '당기손익-공정가치측정금융자산',
            '기타포괄손익-공정가치측정금융자산',
            '매출채권', '매출채권및기타채권', '매출채권계',
            '재고자산', '재고자산계',
            '기타유동자산',
            '매각예정자산',
            '비유동자산', '비유동자산계',
            '장기금융상품',
            '관계기업투자', '관계기업및공동기업투자',
            '유형자산', '유형자산계',
            '사용권자산',
            '투자부동산',
            '무형자산', '무형자산계',
            '이연법인세자산',
            '기타비유동자산'
        ],
        '부채': [
            '부채총계', '부채총액',
            '유동부채', '유동부채계',
            '매입채무', '매입채무및기타채무',
            '단기차입금',
            '유동성장기부채',
            '당기법인세부채',
            '기타유동부채',
            '매각예정부채',
            '비유동부채', '비유동부채계',
            '장기차입금',
            '리스부채',
            '장기매입채무및기타채무',
            '이연법인세부채',
            '퇴직급여충당부채',
            '기타비유동부채'
        ],
        '자본': [
            '자본총계', '자본총액',
            '지배기업소유주지분',
            '자본금',
            '자본잉여금',
            '기타포괄손익누계액',
            '이익잉여금',
            '비지배지분'
        ]
    },
    'IS': {
        '매출': [
            '매출액', '수익(매출액)',
            '매출원가',
            '매출총이익', '매출총손익'
        ],
        '영업손익': [
            '판매비와관리비',
            '영업이익', '영업이익(손실)'
        ],
        '영업외손익': [
            '금융수익',
            '금융비용',
            '기타수익',
            '기타비용',
            '종속기업,관계기업및공동기업투자손익',
            '법인세비용차감전순이익', '법인세비용차감전순손익'
        ],
        '법인세및순손익': [
            '법인세비용',
            '당기순이익', '당기순이익(손실)',
            '지배기업소유주지분',
            '비지배지분'
        ],
        '포괄손익': [
            '기타포괄손익',
            '총포괄손익'
        ]
    },
    'CF': {
        '영업활동': [
            '영업활동현금흐름',
            '당기순이익',
            '조정항목',
            '영업자산부채의변동'
        ],
        '투자활동': [
            '투자활동현금흐름',
            '단기금융상품의순증감',
            '장기금융상품의순증감',
            '유형자산의취득',
            '유형자산의처분'
        ],
        '재무활동': [
            '재무활동현금흐름',
            '단기차입금의순증감',
            '장기차입금의차입',
            '장기차입금의상환',
            '배당금지급'
        ],
        '현금및현금성자산': [
            '현금및현금성자산의순증감',
            '기초현금및현금성자산',
            '기말현금및현금성자산'
        ]
    },
    'SCE': {
        '자본변동': [
            '기초자본',
            '당기순이익',
            '기타포괄손익',
            '총포괄손익',
            '자본거래',
            '기말자본'
        ]
    }
}

# 분기 코드 매핑
QUARTER_CODES = {
    'Q1': '11013',  # 1분기
    'Q2': '11012',  # 반기
    'Q3': '11014',  # 3분기  
    'Q4': '11011'   # 연간
}

# 숫자 단위 변환 함수
def format_amount(amount):
    """숫자를 읽기 쉬운 한글 단위로 변환"""
    try:
        num = int(amount)
        if abs(num) >= 1000000000000:  # 조 단위
            return f"{num / 1000000000000:.1f}조"
        elif abs(num) >= 100000000:  # 억 단위
            return f"{num / 100000000:.0f}억"
        elif abs(num) >= 10000:  # 만 단위
            return f"{num / 10000:.0f}만"
        else:
            return f"{num:,}"
    except:
        return "0"

# 계정 순서 정렬 함수 (개선된 버전)
def sort_accounts(data, sj_div):
    if sj_div not in ACCOUNT_ORDER:
        return data
    
    order_config = ACCOUNT_ORDER[sj_div]
    sorted_data = {}
    
    # 정의된 순서대로 정렬
    for category, accounts in order_config.items():
        for account in accounts:
            # 정확한 매칭과 부분 매칭 모두 고려
            for key in data.keys():
                if key == account or account in key or key in account:
                    if key not in sorted_data:  # 중복 방지
                        sorted_data[key] = data[key]
    
    # 나머지 계정들 추가 (정의되지 않은 새로운 계정들)
    for key, value in data.items():
        if key not in sorted_data:
            sorted_data[key] = value
            
    return sorted_data

# Gemini AI 분석 함수
def analyze_financial_data(corp_name, year, data_dict):
    """Gemini AI를 사용한 재무제표 분석"""
    print(f"🤖 AI 분석 요청: {corp_name} ({year}년)")
    
    if not AI_ENABLED:
        print("❌ AI 기능이 비활성화되어 있습니다.")
        return "AI 분석 기능이 현재 비활성화되어 있습니다. .env 파일에 GEMINI_API_KEY를 설정해주세요."
    
    if not model:
        print("❌ Gemini 모델이 초기화되지 않았습니다.")
        return "Gemini AI 모델이 초기화되지 않았습니다. API 키를 확인해주세요."
    
    try:
        print(f"📊 분석 데이터 처리 중...")
        # 분석할 데이터 준비
        analysis_data = {}
        for statement, data in data_dict.items():
            if data and len(data) > 0:
                # 주요 계정만 선별
                key_accounts = {}
                for account, amount in list(data.items())[:10]:  # 상위 10개 계정
                    key_accounts[account] = format_amount(amount)
                analysis_data[statement] = key_accounts
        
        # 프롬프트 생성
        prompt = f"""
다음은 {corp_name}의 {year}년 재무제표 데이터입니다. 
이 데이터를 기반으로 종합적인 재무분석을 해주세요.

재무데이터:
{json.dumps(analysis_data, ensure_ascii=False, indent=2)}

다음 항목들을 포함하여 분석해주세요:
1. 재무상태 분석 (자산, 부채, 자본 구조)
2. 수익성 분석
3. 안정성 분석
4. 주요 재무지표의 의미
5. 투자자 관점에서의 종합 평가

분석 결과를 한국어로 쉽고 명확하게 설명해주세요. 
전문용어는 간단히 설명을 덧붙여주세요.
"""

        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"AI 분석 중 오류가 발생했습니다: {str(e)}"

# 고급 AI 분석 함수들
def analyze_financial_ratios(corp_name, year, data_dict):
    """재무비율 분석"""
    if not AI_ENABLED or not model:
        return "AI 분석 기능이 비활성화되어 있습니다."
    
    try:
        bs_data = data_dict.get('BS', {})
        is_data = data_dict.get('IS', {})
        cf_data = data_dict.get('CF', {})
        
        # 주요 재무비율 계산
        ratios = calculate_financial_ratios(bs_data, is_data, cf_data)
        
        prompt = f"""
{corp_name}의 {year}년 재무비율 분석을 해주세요.

계산된 주요 재무비율:
{json.dumps(ratios, ensure_ascii=False, indent=2)}

다음 관점에서 분석해주세요:
1. 유동성 비율 (유동비율, 당좌비율 등)
2. 수익성 비율 (ROE, ROA, 영업이익률 등)
3. 안정성 비율 (부채비율, 자기자본비율 등)
4. 활동성 비율 (총자산회전율 등)
5. 업계 평균과의 비교 관점
6. 투자자 관점에서의 평가

한국어로 상세하고 실용적인 분석을 제공해주세요.
"""
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"재무비율 분석 중 오류: {str(e)}"

def analyze_financial_trends(corp_name, multi_year_data):
    """추세 분석"""
    if not AI_ENABLED or not model:
        return "AI 분석 기능이 비활성화되어 있습니다."
    
    try:
        prompt = f"""
{corp_name}의 다년도 재무 추세 분석을 해주세요.

연도별 데이터:
{json.dumps(multi_year_data, ensure_ascii=False, indent=2)}

다음 관점에서 분석해주세요:
1. 매출 성장 추세
2. 수익성 변화 패턴
3. 자산 규모 변화
4. 부채 수준 변화
5. 현금흐름 패턴
6. 향후 전망 및 주의사항

숫자의 증감률과 함께 그 의미를 해석해주세요.
"""
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"추세 분석 중 오류: {str(e)}"

def analyze_investment_perspective(corp_name, year, comprehensive_data):
    """투자 관점 분석"""
    if not AI_ENABLED or not model:
        return "AI 분석 기능이 비활성화되어 있습니다."
    
    try:
        prompt = f"""
{corp_name}의 {year}년 재무제표를 투자자 관점에서 종합 분석해주세요.

종합 재무 데이터:
{json.dumps(comprehensive_data, ensure_ascii=False, indent=2)}

다음 관점에서 분석해주세요:
1. 투자 매력도 평가 (5점 만점)
2. 강점과 약점 분석
3. 주요 리스크 요인
4. 성장 가능성 평가
5. 배당 정책 및 주주 환원
6. 경쟁사 대비 포지션
7. 투자 권고 의견 (매수/보유/매도)

실용적이고 객관적인 투자 분석을 제공해주세요.
"""
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"투자 분석 중 오류: {str(e)}"

def analyze_with_custom_prompt(corp_name, year, financial_data, prompt):
    """커스텀 프롬프트를 사용한 AI 분석"""
    try:
        # 재무데이터를 텍스트로 변환
        data_summary = f"""
{corp_name} ({year}년) 재무 데이터:

재무상태표:
"""
        bs_data = financial_data.get('BS', {})
        for account, value in list(bs_data.items())[:20]:  # 상위 20개 항목
            data_summary += f"- {account}: {value:,}원\n"
        
        data_summary += "\n포괄손익계산서:\n"
        is_data = financial_data.get('IS', {})
        for account, value in list(is_data.items())[:20]:  # 상위 20개 항목
            data_summary += f"- {account}: {value:,}원\n"
        
        # Gemini AI 모델에 분석 요청
        full_prompt = f"{prompt}\n\n{data_summary}\n\n위 데이터를 바탕으로 분석해주세요."
        
        response = model.generate_content(full_prompt)
        return response.text
        
    except Exception as e:
        print(f"커스텀 프롬프트 분석 오류: {str(e)}")
        return f"AI 분석 중 오류가 발생했습니다: {str(e)}"

def calculate_financial_ratios(bs_data, is_data, cf_data):
    """재무비율 계산 함수"""
    ratios = {}
    
    try:
        # 재무상태표 주요 항목
        total_assets = get_account_value(bs_data, ['자산총계', '자산총액'])
        current_assets = get_account_value(bs_data, ['유동자산', '유동자산계'])
        current_liabilities = get_account_value(bs_data, ['유동부채', '유동부채계'])
        total_liabilities = get_account_value(bs_data, ['부채총계', '부채총액'])
        total_equity = get_account_value(bs_data, ['자본총계', '자본총액', '지배기업소유주지분'])
        
        # 손익계산서 주요 항목
        revenue = get_account_value(is_data, ['매출액', '수익(매출액)'])
        operating_income = get_account_value(is_data, ['영업이익', '영업이익(손실)'])
        net_income = get_account_value(is_data, ['당기순이익', '당기순이익(손실)', '지배기업소유주지분'])
        
        # 유동성 비율
        if current_liabilities > 0:
            ratios['유동비율'] = round((current_assets / current_liabilities) * 100, 2)
        
        # 수익성 비율
        if total_assets > 0:
            ratios['ROA'] = round((net_income / total_assets) * 100, 2)
        
        if total_equity > 0:
            ratios['ROE'] = round((net_income / total_equity) * 100, 2)
            ratios['자기자본비율'] = round((total_equity / total_assets) * 100, 2)
        
        if revenue > 0:
            ratios['영업이익률'] = round((operating_income / revenue) * 100, 2)
            ratios['순이익률'] = round((net_income / revenue) * 100, 2)
            ratios['총자산회전율'] = round(revenue / total_assets, 2)
        
        # 안정성 비율
        if total_equity > 0:
            ratios['부채비율'] = round((total_liabilities / total_equity) * 100, 2)
        
        return ratios
        
    except Exception as e:
        print(f"재무비율 계산 오류: {e}")
        return {}

def get_account_value(data, account_names):
    """계정명으로 값 찾기"""
    for account in account_names:
        for key, value in data.items():
            if account in key:
                return abs(int(value)) if value else 0
    return 0

# 회사명으로 회사코드 검색
@app.route('/api/search_corp', methods=['GET'])
def search_corp():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': '회사명을 입력하세요.', 'results': []}), 400
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT corp_code, corp_name, stock_code FROM corpcode WHERE corp_name LIKE ? LIMIT 10", (f'%{name}%',))
        results = [
            {'corp_code': row[0], 'corp_name': row[1], 'stock_code': row[2]} for row in c.fetchall()
        ]
        conn.close()
        return jsonify({'results': results, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e), 'results': [], 'success': False}), 500

# 최신 연도 자동 탐색 함수
def get_latest_year(corp_code, reprt_code):
    this_year = date.today().year
    for year in range(this_year, this_year-5, -1):
        try:
            data = get_financial_data(corp_code, str(year), reprt_code)
            if data and data.get('list'):
                return str(year)
        except:
            continue
    return '2023'

# 당기/전기 비교 데이터 조회 API
@app.route('/api/compare/current-previous', methods=['GET'])
def compare_current_previous():
    corp_code = request.args.get('corp_code')
    year = request.args.get('year', str(date.today().year))
    sj_div = request.args.get('sj_div', 'BS')
    fs_div = request.args.get('fs_div', 'CFS')
    reprt_code = request.args.get('reprt_code', '11011')
    
    if not corp_code:
        return jsonify({'error': '회사코드가 필요합니다', 'success': False}), 400
    
    try:
        current_year = int(year)
        previous_year = current_year - 1
        
        comparison_data = {}
        
        # 당기 데이터
        try:
            current_data = get_financial_data(corp_code, str(current_year), reprt_code, fs_div)
            if current_data and current_data.get('status') == '000':
                filtered_items = [item for item in current_data.get('list', []) if item.get('sj_div') == sj_div.upper()]
                processed_data = {}
                for item in filtered_items:
                    account_name = item.get('account_nm', '')
                    amount_str = item.get('thstrm_amount', '0').replace(',', '') or '0'
                    try:
                        amount = int(amount_str)
                        processed_data[account_name] = amount
                    except:
                        processed_data[account_name] = 0
                comparison_data[f'{current_year}년(당기)'] = sort_accounts(processed_data, sj_div)
        except:
            comparison_data[f'{current_year}년(당기)'] = {}
        
        # 전기 데이터
        try:
            previous_data = get_financial_data(corp_code, str(previous_year), reprt_code, fs_div)
            if previous_data and previous_data.get('status') == '000':
                filtered_items = [item for item in previous_data.get('list', []) if item.get('sj_div') == sj_div.upper()]
                processed_data = {}
                for item in filtered_items:
                    account_name = item.get('account_nm', '')
                    amount_str = item.get('thstrm_amount', '0').replace(',', '') or '0'
                    try:
                        amount = int(amount_str)
                        processed_data[account_name] = amount
                    except:
                        processed_data[account_name] = 0
                comparison_data[f'{previous_year}년(전기)'] = sort_accounts(processed_data, sj_div)
        except:
            comparison_data[f'{previous_year}년(전기)'] = {}
        
        # 증감률 계산
        growth_analysis = {}
        current_data_dict = comparison_data.get(f'{current_year}년(당기)', {})
        previous_data_dict = comparison_data.get(f'{previous_year}년(전기)', {})
        
        for account in current_data_dict.keys():
            if account in previous_data_dict:
                current_val = current_data_dict[account]
                previous_val = previous_data_dict[account]
                
                if previous_val != 0:
                    growth_rate = ((current_val - previous_val) / abs(previous_val)) * 100
                    increase_amount = current_val - previous_val
                    growth_analysis[account] = {
                        'growth_rate': round(growth_rate, 1),
                        'increase_amount': increase_amount,
                        'current': current_val,
                        'previous': previous_val
                    }
        
        return jsonify({
            'current_year': current_year,
            'previous_year': previous_year,
            'sj_div': sj_div.upper(),
            'fs_div': fs_div,
            'data': comparison_data,
            'growth_analysis': growth_analysis,
            'success': True
        })
        
    except Exception as e:
        return jsonify({
            'error': f'당기/전기 비교 분석 오류: {str(e)}',
            'success': False
        }), 500

# AI 분석 API (기본)
@app.route('/api/ai-analysis/<analysis_type>', methods=['POST'])
def ai_analysis_by_type(analysis_type):
    """통합 AI 분석 API"""
    try:
        data = request.get_json()
        corp_name = data.get('corp_name', '선택된 기업')
        corp_code = data.get('corp_code', '')
        year = data.get('year', '2024')
        financial_data = data.get('financial_data', {})
        fs_div = data.get('fs_div', 'CFS')
        prompt = data.get('prompt', '')
        
        # 재무제표 구분 한글명
        fs_div_name = '연결재무제표' if fs_div == 'CFS' else '별도재무제표'
        
        print(f"🤖 AI 분석 API 호출:")
        print(f"   - 분석타입: {analysis_type}")
        print(f"   - 기업명: {corp_name}")
        print(f"   - 기업코드: {corp_code}")
        print(f"   - 연도: {year}")
        print(f"   - 재무제표구분: {fs_div} ({fs_div_name})")
        
        # AI 기능 사용 가능 여부 체크
        if not AI_ENABLED:
            return jsonify({
                'analysis': f'AI 분석 기능이 비활성화되어 있습니다. .env 파일에 GEMINI_API_KEY를 설정해주세요.',
                'success': False,
                'ai_enabled': False,
                'corp_name': corp_name,
                'year': year,
                'fs_div': fs_div
            }), 200
        
        # 분석 타입별 처리
        if analysis_type == 'ratios':
            if prompt:
                analysis_result = analyze_with_custom_prompt(corp_name, year, financial_data, prompt)
            else:
                analysis_result = analyze_financial_ratios(corp_name, year, financial_data)
        elif analysis_type == 'trends':
            if prompt:
                analysis_result = analyze_with_custom_prompt(corp_name, year, financial_data, prompt)
            else:
                multi_year_data = data.get('multi_year_data', financial_data)
                analysis_result = analyze_financial_trends(corp_name, multi_year_data)
        elif analysis_type == 'investment':
            if prompt:
                analysis_result = analyze_with_custom_prompt(corp_name, year, financial_data, prompt)
            else:
                comprehensive_data = data.get('comprehensive_data', financial_data)
                analysis_result = analyze_investment_perspective(corp_name, year, comprehensive_data)
        elif analysis_type == 'comprehensive':
            if prompt:
                analysis_result = analyze_with_custom_prompt(corp_name, year, financial_data, prompt)
            else:
                # 모든 분석 수행
                basic_analysis = analyze_financial_data(corp_name, year, financial_data)
                ratios_analysis = analyze_financial_ratios(corp_name, year, financial_data)
                analysis_result = f"{basic_analysis}\n\n{ratios_analysis}"
        else:
            # 기본 분석
            analysis_result = analyze_financial_data(corp_name, year, financial_data)
        
        print(f"✅ AI 분석 완료: {corp_name} ({analysis_type})")
        
        return jsonify({
            'analysis': analysis_result,
            'analysis_type': analysis_type,
            'success': True,
            'ai_enabled': True,
            'corp_name': corp_name,
            'year': year,
            'fs_div': fs_div,
            'fs_div_name': fs_div_name
        })
        
    except Exception as e:
        print(f"❌ AI 분석 오류 ({analysis_type}): {str(e)}")
        return jsonify({
            'error': f'AI 분석 오류: {str(e)}',
            'analysis_type': analysis_type,
            'success': False,
            'ai_enabled': AI_ENABLED,
            'corp_name': data.get('corp_name', '알 수 없음') if 'data' in locals() else '알 수 없음'
        }), 500

# 분기별 데이터 조회 API (개선된 버전)
@app.route('/api/quarterly/<sj_div>', methods=['GET'])
def quarterly_data(sj_div):
    corp_code = request.args.get('corp_code')
    year = request.args.get('year', str(date.today().year))
    fs_div = request.args.get('fs_div', 'CFS')
    
    print(f"📊 분기별 데이터 요청: {corp_code}, {year}년, {sj_div}, {fs_div}")
    
    if not corp_code:
        return jsonify({'error': '회사코드가 필요합니다', 'success': False}), 400
    
    try:
        quarterly_data = {}
        successful_quarters = 0
        
        for quarter, reprt_code in QUARTER_CODES.items():
            print(f"🔍 {quarter} 데이터 조회 시작...")
            try:
                raw_data = get_financial_data(corp_code, year, reprt_code, fs_div)
                
                if raw_data and raw_data.get('status') == '000':
                    filtered_items = [item for item in raw_data.get('list', []) if item.get('sj_div') == sj_div.upper()]
                    print(f"✅ {quarter} 필터링된 항목 수: {len(filtered_items)}")
                    
                    processed_data = {}
                    for item in filtered_items:
                        account_name = item.get('account_nm', '')
                        amount_str = item.get('thstrm_amount', '0').replace(',', '') or '0'
                        try:
                            amount = int(amount_str)
                            processed_data[account_name] = amount
                        except:
                            processed_data[account_name] = 0
                    
                    # 계정 순서 정렬
                    sorted_data = sort_accounts(processed_data, sj_div)
                    quarterly_data[quarter] = sorted_data
                    successful_quarters += 1
                    print(f"✅ {quarter} 데이터 처리 완료: {len(sorted_data)}개 계정")
                    
                elif raw_data and raw_data.get('status') == '013':
                    print(f"⚠️ {quarter} 데이터 없음: {raw_data.get('message', '')}")
                    quarterly_data[quarter] = {}
                else:
                    error_msg = raw_data.get('message', '알 수 없는 오류') if raw_data else 'API 요청 실패'
                    print(f"❌ {quarter} 조회 실패: {error_msg}")
                    quarterly_data[quarter] = {}
                    
            except Exception as e:
                print(f"❌ {quarter} 데이터 조회 중 예외: {str(e)}")
                quarterly_data[quarter] = {}
        
        print(f"📈 분기별 조회 완료: {successful_quarters}/4 분기 성공")
        
        return jsonify({
            'year': year,
            'sj_div': sj_div.upper(),
            'fs_div': fs_div,
            'data': quarterly_data,
            'successful_quarters': successful_quarters,
            'success': True
        })
        
    except Exception as e:
        print(f"❌ 분기별 데이터 조회 전체 오류: {str(e)}")
        return jsonify({
            'error': f'분기별 데이터 조회 오류: {str(e)}',
            'success': False
        }), 500

# 다년도 분기별 비교 API
@app.route('/api/compare/multi-year', methods=['GET'])
def compare_multi_year():
    corp_code = request.args.get('corp_code')
    years = request.args.get('years', '').split(',')
    quarter = request.args.get('quarter', 'Q4')
    sj_div = request.args.get('sj_div', 'BS')
    fs_div = request.args.get('fs_div', 'CFS')
    
    if not corp_code or not years:
        return jsonify({'error': '회사코드와 연도가 필요합니다', 'success': False}), 400
    
    try:
        comparison_data = {}
        reprt_code = QUARTER_CODES.get(quarter, '11011')
        
        for year in years:
            year = year.strip()
            try:
                raw_data = get_financial_data(corp_code, year, reprt_code, fs_div)
                
                if raw_data and raw_data.get('status') == '000':
                    filtered_items = [item for item in raw_data.get('list', []) if item.get('sj_div') == sj_div.upper()]
                    
                    processed_data = {}
                    for item in filtered_items:
                        account_name = item.get('account_nm', '')
                        amount_str = item.get('thstrm_amount', '0').replace(',', '') or '0'
                        try:
                            amount = int(amount_str)
                            processed_data[account_name] = amount
                        except:
                            processed_data[account_name] = 0
                    
                    # 계정 순서 정렬
                    sorted_data = sort_accounts(processed_data, sj_div)
                    comparison_data[f'{year}년'] = sorted_data
                else:
                    comparison_data[f'{year}년'] = {}
                    
            except Exception as e:
                print(f"Error fetching {year} data: {e}")
                comparison_data[f'{year}년'] = {}
        
        # 성장률 계산
        growth_rates = calculate_growth_rates_korean(comparison_data, years)
        
        return jsonify({
            'years': years,
            'quarter': quarter,
            'sj_div': sj_div.upper(),
            'fs_div': fs_div,
            'data': comparison_data,
            'growth_rates': growth_rates,
            'success': True
        })
        
    except Exception as e:
        return jsonify({
            'error': f'다년도 비교 분석 오류: {str(e)}',
            'success': False
        }), 500

# 성장률 계산 함수 (한글 버전)
def calculate_growth_rates_korean(data, years):
    if len(years) < 2:
        return {}
    
    growth_rates = {}
    sorted_years = sorted(years)
    
    for i in range(1, len(sorted_years)):
        prev_year = sorted_years[i-1]
        curr_year = sorted_years[i]
        
        prev_key = f'{prev_year}년'
        curr_key = f'{curr_year}년'
        
        if prev_key in data and curr_key in data:
            year_growth = {}
            prev_data = data[prev_key]
            curr_data = data[curr_key]
            
            for account in curr_data.keys():
                if account in prev_data:
                    prev_value = prev_data[account]
                    curr_value = curr_data[account]
                    
                    if prev_value != 0:
                        growth_rate = ((curr_value - prev_value) / abs(prev_value)) * 100
                        year_growth[account] = round(growth_rate, 2)
                    else:
                        year_growth[account] = 0 if curr_value == 0 else 100
            
            growth_rates[f"{prev_year}년→{curr_year}년"] = year_growth
    
    return growth_rates

# 재무제표 데이터 API (개선된 버전)
@app.route('/api/financial/<sj_div>', methods=['GET'])
def financial_by_sj(sj_div):
    corp_code = request.args.get('corp_code')
    bsns_year = request.args.get('year') or request.args.get('bsns_year')
    reprt_code = request.args.get('reprt') or request.args.get('reprt_code', '11011')
    fs_div = request.args.get('fs_div', 'CFS')
    
    # fs_div 검증 및 한글명 변환
    fs_div_name = '연결재무제표' if fs_div == 'CFS' else '별도재무제표'
    print(f"📊 개별 재무제표 요청: {sj_div}, {corp_code}, {bsns_year}년, {reprt_code}, {fs_div}({fs_div_name})")
    
    if not corp_code:
        return jsonify({'error': '회사코드가 필요합니다', 'success': False}), 400
    
    if not bsns_year:
        bsns_year = get_latest_year(corp_code, reprt_code)
        print(f"🔍 연도 자동 탐색 결과: {bsns_year}")
    
    try:
        raw_data = get_financial_data(corp_code, bsns_year, reprt_code, fs_div)
        
        if not raw_data or (isinstance(raw_data, dict) and raw_data.get('status') != '000'):
            error_msg = raw_data.get('message', '데이터를 찾을 수 없습니다') if isinstance(raw_data, dict) else '데이터를 찾을 수 없습니다'
            print(f"❌ 데이터 조회 실패: {error_msg}")
            
            # 다른 연도로 재시도
            for retry_year in [str(int(bsns_year)-1), str(int(bsns_year)-2)]:
                print(f"🔄 {retry_year}년으로 재시도...")
                retry_data = get_financial_data(corp_code, retry_year, reprt_code, fs_div)
                if retry_data and retry_data.get('status') == '000':
                    raw_data = retry_data
                    bsns_year = retry_year
                    print(f"✅ {retry_year}년 데이터 조회 성공!")
                    break
            else:
                return jsonify({
                    'error': error_msg,
                    'year': bsns_year,
                    'sj_div': sj_div,
                    'fs_div': fs_div,
                    'fs_div_name': fs_div_name,
                    'data': {},
                    'success': False
                })
        
        # sj_div 필터링 및 데이터 가공
        filtered_items = [item for item in raw_data.get('list', []) if item.get('sj_div') == sj_div.upper()]
        print(f"✅ 필터링된 항목 수: {len(filtered_items)} ({fs_div_name})")
        
        # 데이터 검증: 실제로 다른 fs_div의 데이터인지 확인
        if len(filtered_items) > 0:
            sample_item = filtered_items[0]
            print(f"📋 샘플 데이터 fs_div: {sample_item.get('fs_div', '없음')}")
        
        # {계정명: 당기금액} 형태로 변환
        processed_data = {}
        for item in filtered_items:
            account_name = item.get('account_nm', '')
            amount_str = item.get('thstrm_amount', '0').replace(',', '') or '0'
            try:
                amount = int(amount_str)
                processed_data[account_name] = amount
            except:
                processed_data[account_name] = 0
        
        # 계정 순서 정렬
        sorted_data = sort_accounts(processed_data, sj_div)
        print(f"📈 처리 완료: {len(sorted_data)}개 계정 ({fs_div_name})")
        
        return jsonify({
            'year': bsns_year,
            'sj_div': sj_div.upper(),
            'fs_div': fs_div,
            'fs_div_name': fs_div_name,
            'reprt_code': reprt_code,
            'data': sorted_data,
            'raw_count': len(filtered_items),
            'success': True
        })
        
    except Exception as e:
        print(f"❌ API 호출 오류: {str(e)}")
        return jsonify({
            'error': f'API 호출 오류: {str(e)}',
            'year': bsns_year,
            'sj_div': sj_div,
            'fs_div': fs_div,
            'fs_div_name': fs_div_name,
            'data': {},
            'success': False
        }), 500

# 기존 재무제표 API (하위 호환성)
@app.route('/api/financial', methods=['GET'])
def financial():
    corp_code = request.args.get('corp_code')
    bsns_year = request.args.get('bsns_year')
    reprt_code = request.args.get('reprt_code')
    fs_div = request.args.get('fs_div', 'CFS')
    
    if not (corp_code and reprt_code):
        return jsonify({'error': '필수 파라미터 누락'}), 400
    if not bsns_year:
        bsns_year = get_latest_year(corp_code, reprt_code)
    
    try:
        data = get_financial_data(corp_code, bsns_year, reprt_code, fs_div)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 별도/연결 재무제표 테스트 API
@app.route('/api/test-fs-diff', methods=['GET'])
def test_fs_difference():
    """별도/연결 재무제표 차이 테스트 API"""
    corp_code = request.args.get('corp_code')
    bsns_year = request.args.get('year', '2023')
    reprt_code = request.args.get('reprt_code', '11011')
    sj_div = request.args.get('sj_div', 'BS')
    
    if not corp_code:
        return jsonify({'error': '기업코드가 필요합니다'}), 400
    
    try:
        print(f"🔍 별도/연결 재무제표 차이 테스트 시작: {corp_code}")
        
        # 연결재무제표 데이터 조회
        cfs_data = get_financial_data(corp_code, bsns_year, reprt_code, 'CFS')
        print(f"📊 연결재무제표 조회 결과: {cfs_data.get('status') if cfs_data else 'None'}")
        
        # 별도재무제표 데이터 조회
        ofs_data = get_financial_data(corp_code, bsns_year, reprt_code, 'OFS')
        print(f"📊 별도재무제표 조회 결과: {ofs_data.get('status') if ofs_data else 'None'}")
        
        result = {
            'corp_code': corp_code,
            'year': bsns_year,
            'reprt_code': reprt_code,
            'cfs_status': cfs_data.get('status') if cfs_data else 'error',
            'ofs_status': ofs_data.get('status') if ofs_data else 'error',
            'cfs_count': len(cfs_data.get('list', [])) if cfs_data else 0,
            'ofs_count': len(ofs_data.get('list', [])) if ofs_data else 0,
            'comparison': {}
        }
        
        # 두 데이터 모두 성공적으로 조회된 경우 비교 수행
        if (cfs_data and cfs_data.get('status') == '000' and 
            ofs_data and ofs_data.get('status') == '000'):
            
            # 특정 재무제표 유형으로 필터링
            cfs_filtered = [item for item in cfs_data.get('list', []) 
                          if item.get('sj_div') == sj_div.upper()]
            ofs_filtered = [item for item in ofs_data.get('list', []) 
                          if item.get('sj_div') == sj_div.upper()]
            
            # 계정별 금액 비교
            cfs_accounts = {item.get('account_nm'): item.get('thstrm_amount', '0') 
                          for item in cfs_filtered}
            ofs_accounts = {item.get('account_nm'): item.get('thstrm_amount', '0') 
                          for item in ofs_filtered}
            
            # 공통 계정 찾기
            common_accounts = set(cfs_accounts.keys()) & set(ofs_accounts.keys())
            different_accounts = []
            
            for account in list(common_accounts)[:10]:  # 상위 10개만 비교
                cfs_amount = cfs_accounts.get(account, '0').replace(',', '') or '0'
                ofs_amount = ofs_accounts.get(account, '0').replace(',', '') or '0'
                
                try:
                    cfs_val = int(cfs_amount)
                    ofs_val = int(ofs_amount)
                    
                    if cfs_val != ofs_val:
                        different_accounts.append({
                            'account': account,
                            'cfs_amount': cfs_val,
                            'ofs_amount': ofs_val,
                            'difference': cfs_val - ofs_val
                        })
                except:
                    pass
            
            result['comparison'] = {
                'cfs_filtered_count': len(cfs_filtered),
                'ofs_filtered_count': len(ofs_filtered),
                'common_accounts': len(common_accounts),
                'different_accounts': different_accounts,
                'has_difference': len(different_accounts) > 0
            }
            
            print(f"📈 비교 결과: 공통계정 {len(common_accounts)}개, 차이있는 계정 {len(different_accounts)}개")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ 테스트 오류: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 메인 페이지
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    # 배포 환경에서 포트 설정 (Render는 포트를 자동 할당)
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False) 