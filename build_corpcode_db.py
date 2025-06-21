import json
import sqlite3

json_path = 'corpCode.json'
db_path = 'corpcode.db'

def main():
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    companies = data.get('list', [])

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS corpcode (
            corp_code TEXT PRIMARY KEY,
            corp_name TEXT,
            stock_code TEXT,
            modify_date TEXT
        )
    ''')
    c.execute('DELETE FROM corpcode')
    for corp in companies:
        c.execute('''
            INSERT INTO corpcode (corp_code, corp_name, stock_code, modify_date)
            VALUES (?, ?, ?, ?)
        ''', (
            corp.get('corp_code', ''),
            corp.get('corp_name', ''),
            corp.get('stock_code', ''),
            corp.get('modify_date', '')
        ))
    conn.commit()
    conn.close()
    print(f'{len(companies)}개 회사 정보가 {db_path}에 저장되었습니다.')

if __name__ == '__main__':
    main() 