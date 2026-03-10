from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# [가짜 DB 1] 식당 테이블 (진명님 테이블 구조 반영)
RESTAURANTS_DB = [
    {"id": 1, "name": "밍글스", "grade": "2", "cuisine": "한식", "address": "강남구", "price": "150,000원"},
    {"id": 2, "name": "모수", "grade": "3", "cuisine": "한식", "address": "용산구", "price": "200,000원"},
    {"id": 3, "name": "알렌", "grade": "1", "cuisine": "양식", "address": "강남구", "price": "120,000원"},
    {"id": 4, "name": "정식당", "grade": "2", "cuisine": "양식", "address": "강남구", "price": "160,000원"}
]

# [가짜 DB 2] 예약 테이블 (누가 몇 번 식당의 몇 타임을 예약했는지 저장)
RESERVATIONS_DB = [
    # 예시: 1번 식당(밍글스)의 1타임, 3타임은 이미 누군가 예약함
    {"restaurant_id": 1, "reserve_time": 1, "user_name": "홍길동"},
    {"restaurant_id": 1, "reserve_time": 3, "user_name": "김철수"}
]

# --- 1. 다중 필터로 식당 검색하기 ---
@app.route('/api/filter', methods=['POST'])
def filter_restaurants():
    filters = request.get_json()
    filtered_data = RESTAURANTS_DB.copy()

    if filters.get('grade') and len(filters['grade']) > 0:
        filtered_data = [res for res in filtered_data if res['grade'] in filters['grade']]

    if filters.get('cuisine') and len(filters['cuisine']) > 0:
        filtered_data = [res for res in filtered_data if res['cuisine'] in filters['cuisine']]

    return jsonify(filtered_data)

# --- 2. 예약 팝업 열 때: 이미 예약된 시간 확인하기 ---
@app.route('/api/check_reservation', methods=['GET'])
def check_reservation():
    # URL에서 식당 아이디를 가져옴 (?restaurant_id=1)
    req_id = int(request.args.get('restaurant_id'))
    
    # 예약 DB를 뒤져서 해당 식당의 예약된 '시간(time)'들만 리스트로 뽑아냄
    reserved_times = [res['reserve_time'] for res in RESERVATIONS_DB if res['restaurant_id'] == req_id]
    
    # 예: reserved_times = [1, 3]
    return jsonify({"reserved_times": reserved_times})

# --- 3. 최종 예약 버튼 눌렀을 때: 예약 저장하기 ---
@app.route('/api/make_reservation', methods=['POST'])
def make_reservation():
    data = request.get_json()
    res_id = int(data['restaurant_id'])
    res_time = int(data['reserve_time'])

    # (더블 체크) 그 짧은 찰나에 누가 예약했는지 다시 확인!
    for res in RESERVATIONS_DB:
        if res['restaurant_id'] == res_id and res['reserve_time'] == res_time:
            # 이미 있으면 실패 반환
            return jsonify({"success": False})
    
    # 없으면 예약 DB에 추가! (MariaDB의 INSERT 문 역할)
    RESERVATIONS_DB.append({
        "restaurant_id": res_id,
        "reserve_time": res_time,
        "user_name": data['user_name'],
        "user_phone": data['user_phone']
    })
    
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)