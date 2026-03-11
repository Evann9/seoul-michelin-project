from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import pickle

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('index.html')

# =====================================================================
# [1] DB 연결 설정
# =====================================================================
def get_db_connection():
    """
    주인님께서 생성하신 'mydb.dat' (pickle) 파일에서 접속 정보를 읽어
    MariaDB와 연결합니다.
    """
    try:
        with open('mydb.dat', 'rb') as f:
            config = pickle.load(f)
        conn = mysql.connector.connect(**config)
        return conn
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None

# =====================================================================
# [2] API: 조건에 맞는 식당 목록 검색 (michelin_star_restaurants 테이블)
# =====================================================================
@app.route('/api/filter', methods=['POST'])
def filter_restaurants():
    filters = request.get_json()
    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB 연결 실패"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT 
                m.restaurant_id, 
                m.restaurant_name, 
                m.grade, 
                m.cuisine_type, 
                m.address, 
                m.price,
                IF(f.restaurant_id IS NOT NULL, 1, 0) as is_favorite 
            FROM michelin_star_restaurants m
            LEFT JOIN favorites f ON m.restaurant_id = f.restaurant_id
            WHERE 1=1
        """
        params = []

        # 별점 필터
        if filters.get('grade') and len(filters['grade']) > 0:
            placeholders = ', '.join(['%s'] * len(filters['grade']))
            query += f" AND m.grade IN ({placeholders})"
            params.extend(filters['grade'])

        # 음식 구분 필터 
        if filters.get('cuisine') and len(filters['cuisine']) > 0:
            placeholders = ', '.join(['%s'] * len(filters['cuisine']))
            query += f" AND m.cuisine_type IN ({placeholders})"
            params.extend(filters['cuisine'])
            
        # 즐겨찾기 필터
        if filters.get('favorite') == True:
             query += " AND f.restaurant_id IS NOT NULL"

        cursor.execute(query, tuple(params))
        return jsonify(cursor.fetchall())
    except Exception as e:
        print(f"쿼리 실행 에러: {e}")
        return jsonify({"error": "데이터 조회 실패"}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================================
# [3] API: 즐겨찾기 추가 및 취소 (favorites 테이블)
# =====================================================================
@app.route('/api/toggle_favorite', methods=['POST'])
def toggle_favorite():
    data = request.get_json()
    res_id = data.get('restaurant_id')
    
    conn = get_db_connection()
    if not conn: return jsonify({"success": False}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("SELECT favorites_id FROM favorites WHERE restaurant_id = %s", (res_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute("DELETE FROM favorites WHERE restaurant_id = %s", (res_id,))
            action = 'removed'
        else:
            cursor.execute("INSERT INTO favorites (restaurant_id) VALUES (%s)", (res_id,))
            action = 'added'
            
        conn.commit()
        return jsonify({"success": True, "action": action})
    except Exception as e:
        conn.rollback()
        print(f"즐겨찾기 에러: {e}")
        return jsonify({"success": False}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================================
# [4] API: 예약 가능 시간 조회 (reservations 테이블)
# =====================================================================
@app.route('/api/check_reservation', methods=['GET'])
def check_reservation():
    restaurant_id = request.args.get('id')
    conn = get_db_connection()
    if not conn: return jsonify([]), 500

    cursor = conn.cursor(dictionary=True)
    try:
        query = "SELECT reservation_time FROM reservations WHERE restaurant_id = %s"
        cursor.execute(query, (restaurant_id,))
        results = cursor.fetchall()
        
        booked_times = [row['reservation_time'] for row in results]
        return jsonify(booked_times)
    except Exception as e:
        print(f"예약 조회 에러: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================================
# [5] API: 실제 예약 정보 저장 (reservations 테이블)
# =====================================================================
@app.route('/api/make_reservation', methods=['POST'])
def make_reservation():
    data = request.get_json()
    restaurant_id = data.get('restaurant_id')
    user_name = data.get('user_name')
    user_phone = data.get('user_phone')
    reservation_time = data.get('time') 
    
    conn = get_db_connection()
    if not conn: return jsonify({"success": False}), 500

    cursor = conn.cursor(buffered=True)
    try:
        check_query = "SELECT reservation_id FROM reservations WHERE restaurant_id = %s AND reservation_time = %s"
        cursor.execute(check_query, (restaurant_id, reservation_time))
        if cursor.fetchone():
            return jsonify({"success": False, "message": "이미 예약된 시간입니다."})

        insert_query = """
            INSERT INTO reservations (restaurant_id, user_name, user_phone, reservation_time) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (restaurant_id, user_name, user_phone, reservation_time))
        conn.commit()
        
        return jsonify({"success": True})
    except Exception as e:
        conn.rollback()
        print(f"예약 저장 에러: {e}")
        return jsonify({"success": False}), 500
    finally:
        cursor.close()
        conn.close()

# 예약정보 초기화하기
@app.route('/api/reset_reservations', methods=['POST'])
def reset_reservations():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 예약 테이블의 모든 데이터를 삭제하는 마법의 명령어!
        cursor.execute("TRUNCATE TABLE reservations") 
        conn.commit()
        return jsonify({"success": True, "message": "초기화 완료"})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)})
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True, port=5000)