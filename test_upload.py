import requests, json, os

base = 'http://localhost:8005'
r = requests.post(f'{base}/api/auth/login', json={'email': 'test2@test.com', 'password': 'test1234'})
token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

with open('test_bill.jpg', 'rb') as f:
    r = requests.post(f'{base}/api/bills/upload', headers=headers, files={'file': ('test_bill.jpg', f, 'image/jpeg')})

print(f'UPLOAD: {r.status_code}')
if r.status_code == 201:
    data = r.json()
    bid = data['id']
    print(f'  id: {bid}')
    print(f'  status: {data["status"]}')
    print(f'  seller: {data.get("seller_name")}')
    print(f'  bill_number: {data.get("bill_number")}')
    print(f'  items: {data.get("item_count")}')
    print(f'  confidence: {data.get("ocr_confidence")}')
    print(f'  time_ms: {data.get("processing_time_ms")}')
    items = data.get("items", [])
    for i, item in enumerate(items):
        print(f'  item[{i}]: {json.dumps(item)}')
    with open('bill_id.txt', 'w') as f2:
        f2.write(bid)
    bn = data.get('bill_number', '') or ''
    with open('bill_number.txt', 'w') as f2:
        f2.write(str(bn))
else:
    print(f'ERROR: {r.text}')
