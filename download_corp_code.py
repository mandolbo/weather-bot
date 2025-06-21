import os
import requests
from dotenv import load_dotenv

# .env 파일에서 API 키 불러오기
load_dotenv()
API_KEY = os.getenv('OPEN_DART_API_KEY')

if not API_KEY:
    raise Exception('OPEN_DART_API_KEY가 .env 파일에 설정되어 있지 않습니다.')

url = f'https://opendart.fss.or.kr/api/corpCode.json?crtfc_key={API_KEY}'
response = requests.get(url)

if response.status_code == 200:
    with open('corpCode.json', 'w', encoding='utf-8') as f:
        f.write(response.text)
    print('회사코드 파일(corpCode.json) 다운로드 완료!')
else:
    print('다운로드 실패:', response.status_code)
    print(response.text) 