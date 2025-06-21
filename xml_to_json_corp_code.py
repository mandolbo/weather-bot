import zipfile
import xml.etree.ElementTree as ET
import json

zip_path = 'corpCode.zip'
xml_filename = 'CORPCODE.xml'
json_path = 'corpCode.json'

# ZIP 파일에서 XML 추출
with zipfile.ZipFile(zip_path, 'r') as z:
    z.extract(xml_filename)

# XML 파싱
companies = []
tree = ET.parse(xml_filename)
root = tree.getroot()
for corp in root.findall('list'):
    code_elem = corp.find('corp_code')
    name_elem = corp.find('corp_name')
    stock_elem = corp.find('stock_code')
    modify_elem = corp.find('modify_date')
    companies.append({
        'corp_code': code_elem.text if code_elem is not None else '',
        'corp_name': name_elem.text if name_elem is not None else '',
        'stock_code': stock_elem.text if stock_elem is not None else '',
        'modify_date': modify_elem.text if modify_elem is not None else ''
    })

# JSON 파일로 저장
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump({'list': companies}, f, ensure_ascii=False, indent=2)

print(f'회사 목록이 {json_path} 파일로 저장되었습니다!') 