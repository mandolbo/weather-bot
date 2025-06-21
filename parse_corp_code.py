import json

json_path = 'corpCode.json'

# JSON 파일 읽기
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# 회사 목록 추출 (list 키가 최상위에 있다고 가정)
companies = []
for corp in data.get('list', []):
    corp_code = corp.get('corp_code', '')
    corp_name = corp.get('corp_name', '')
    stock_code = corp.get('stock_code', '')
    companies.append((corp_code, corp_name, stock_code))

# 예시: 상위 10개만 출력
print('고유번호\t회사명\t종목코드')
for corp_code, corp_name, stock_code in companies[:10]:
    print(f'{corp_code}\t{corp_name}\t{stock_code}')

print(f'총 회사 수: {len(companies)}') 