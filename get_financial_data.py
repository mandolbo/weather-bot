import os
import requests
from dotenv import load_dotenv
import time

def get_financial_data(corp_code, bsns_year, reprt_code, fs_div='CFS'):
    """
    DART API를 통해 재무제표 데이터를 조회합니다.
    
    Args:
        corp_code: 기업 고유번호
        bsns_year: 사업년도 (YYYY)
        reprt_code: 보고서 코드 (11011: 사업보고서, 11012: 반기보고서, 11013: 1분기보고서, 11014: 3분기보고서)
        fs_div: 재무제표 구분 (CFS: 연결재무제표, OFS: 별도재무제표)
    
    Returns:
        dict: API 응답 데이터
    """
    # fs_div 검증
    if fs_div not in ['CFS', 'OFS']:
        fs_div = 'CFS'  # 기본값
    
    fs_div_name = '연결재무제표' if fs_div == 'CFS' else '별도재무제표'
    print(f"📊 DART API 요청 시작: {corp_code}, {bsns_year}년, 보고서코드: {reprt_code}, 구분: {fs_div}({fs_div_name})")
    
    # 환경변수 로드
    load_dotenv()
    api_key = os.getenv('OPEN_DART_API_KEY') or os.getenv('DART_API_KEY')
    
    # API 키가 없어도 테스트용으로 공개 키 사용 (제한적)
    if not api_key:
        print('⚠️ 환경변수에 DART API 키가 없습니다. 공개 API를 사용합니다 (요청 제한 있음).')
        # 공개 테스트용 키 (실제 서비스에서는 발급받은 키 사용 권장)
        api_key = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'  # 기본값
    else:
        print(f"✅ DART API 키 확인됨: {api_key[:10]}...")
    
    # API 요청 URL 및 파라미터
    url = 'https://opendart.fss.or.kr/api/fnlttSinglAcnt.json'
    params = {
        'crtfc_key': api_key,
        'corp_code': corp_code,
        'bsns_year': bsns_year,
        'reprt_code': reprt_code,
        'fs_div': fs_div
    }
    
    try:
        print(f"🌐 API 요청 URL: {url}")
        print(f"📝 요청 파라미터: corp_code={corp_code}, bsns_year={bsns_year}, reprt_code={reprt_code}, fs_div={fs_div}")
        
        # API 요청 (타임아웃 설정)
        resp = requests.get(url, params=params, timeout=30)
        
        print(f"📨 응답 상태 코드: {resp.status_code}")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
                print(f"✅ 응답 데이터 파싱 성공")
                
                # 응답 상태 확인
                status = data.get('status', 'unknown')
                message = data.get('message', 'no message')
                
                print(f"📊 API 응답 상태: {status}")
                print(f"💬 응답 메시지: {message}")
                
                if status == '000':
                    list_data = data.get('list', [])
                    print(f"✅ 데이터 조회 성공: {len(list_data)}개 항목 ({fs_div_name})")
                    
                    # 데이터 샘플 확인 (디버깅용)
                    if list_data and len(list_data) > 0:
                        sample = list_data[0]
                        print(f"📋 첫 번째 항목 샘플:")
                        print(f"   - 계정명: {sample.get('account_nm', 'N/A')}")
                        print(f"   - 재무제표구분: {sample.get('fs_div', 'N/A')}")
                        print(f"   - 재무제표명: {sample.get('fs_nm', 'N/A')}")
                        print(f"   - 당기금액: {sample.get('thstrm_amount', 'N/A')}")
                    
                    return data
                elif status == '013':
                    print(f"⚠️ 해당 년도/분기 데이터가 없습니다: {message}")
                    return {'status': '013', 'message': '해당 년도/분기 데이터가 없습니다', 'list': []}
                else:
                    print(f"❌ API 오류: {status} - {message}")
                    return {'status': status, 'message': message, 'list': []}
                    
            except ValueError as e:
                print(f"❌ JSON 파싱 오류: {e}")
                print(f"원본 응답: {resp.text[:500]}")
                return None
        else:
            print(f"❌ HTTP 오류: {resp.status_code}")
            print(f"응답 내용: {resp.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        print("❌ 요청 타임아웃 (30초)")
        return None
    except requests.exceptions.ConnectionError:
        print("❌ 연결 오류 - 인터넷 연결을 확인해주세요")
        return None
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {type(e).__name__}: {e}")
        return None

if __name__ == '__main__':
    # 예시: 삼성전자, 2023년, 사업보고서(11011)
    print("🧪 테스트 실행: 삼성전자 2023년 사업보고서")
    data = get_financial_data('00126380', '2023', '11011')
    if data:
        print(f"테스트 결과: {data.get('status', 'unknown')} - {len(data.get('list', []))}개 항목")
    else:
        print("테스트 실패") 