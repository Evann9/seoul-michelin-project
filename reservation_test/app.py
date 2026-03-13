from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import mysql.connector
import pickle

app = Flask(__name__)
CORS(app)

# =====================================================================
# [1] DB 연결 설정
# =====================================================================
def get_db_connection():
    try:
        with open('mydb.dat', 'rb') as f:
            config = pickle.load(f)
        conn = mysql.connector.connect(**config)
        return conn
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None


@app.route('/')
def index():
    restaurants = []
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            # [핵심] 주인님의 예약/상세 로직을 위해 restaurant_id와 price를 추가로 가져옵니다!
            sql = """
            SELECT 
                restaurant_id,
                restaurant_name AS name, 
                grade AS star, 
                cuisine_type AS cuisine, 
                address AS addr,
                price
            FROM michelin_star_restaurants
            """
            cursor.execute(sql)
            restaurants = cursor.fetchall()

            # 구(gu) 정보 추출 (팀원의 데이터 가공 로직)
            for res in restaurants:
                addr_parts = res['addr'].split()
                res['gu'] = addr_parts[1] if len(addr_parts) > 1 else "기타"

        except Exception as e:
            print(f"DB Error: {e}")
        finally:
            cursor.close()
            conn.close()        

    return render_template('index.html', restaurants=restaurants)


# =====================================================================
# [2] API: 조건에 맞는 식당 목록 검색 (michelin_star_restaurants 테이블)
# =====================================================================
@app.route('/api/filter', methods=['POST'])
def filter_restaurants():
    filters = request.get_json()
    gu_filter = filters.get('gu', '전체')

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

        # 구 필터
        if gu_filter != '전체':
            query += " AND m.address LIKE %s"
            params.append(f"%{gu_filter.replace('구', '')}%")

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
# [5] API: 실제 예약 정보 저장 (reservations 테이블) - 중복 검증 기능 추가
# =====================================================================
@app.route('/api/make_reservation', methods=['POST'])
def make_reservation():
    data = request.get_json()
    restaurant_id = data.get('restaurant_id')
    user_name = data.get('user_name')
    user_phone = data.get('user_phone')
    reservation_time = data.get('time') 
    force = data.get('force', False) # JS에서 '확인'을 누르면 True로 전달됨

    # 프론트엔드의 시간표와 동일하게 매핑 (알림창 출력용)
    time_config = {"1": "18:00", "2": "19:00", "3": "20:00", "4": "21:00"}
    time_str = time_config.get(str(reservation_time), "해당 시간")

    conn = get_db_connection()
    if not conn: return jsonify({"success": False}), 500

    # dictionary=True를 사용하여 결과를 딕셔너리 형태로 쉽게 가져오게 설정
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        # [1] 번호는 같은데 이름이 다른 경우 (정보 확인 유도)
        cursor.execute("SELECT user_name FROM reservations WHERE user_phone = %s LIMIT 1", (user_phone,))
        existing_user = cursor.fetchone()
        if existing_user and existing_user['user_name'] != user_name:
            return jsonify({
                "success": False,
                "status": "error",
                "type": "USER_MISMATCH",
                "message": " 이름이나 번호를 다시 확인해 주세요."
            })
        # [1] 동일 식당 내 중복 예약 차단 (전화번호 + 식당 ID)
        cursor.execute("SELECT reservation_id FROM reservations WHERE user_phone = %s AND restaurant_id = %s", (user_phone, restaurant_id))
        if cursor.fetchone():
            return jsonify({
                "success": False, 
                "status": "error",
                "type": "ALREADY_BOOKED_HERE", 
                "message": "이미 이 식당에 예약된 내역이 있어 중복 예약이 불가능합니다."
            })

        # [2] 다른 식당, 같은 시간대 중복 예약 확인 (force가 False일 때만)
        
        other_res_query = """
            SELECT m.restaurant_name, r.reservation_id 
            FROM reservations r
            JOIN michelin_star_restaurants m ON r.restaurant_id = m.restaurant_id
            WHERE r.user_phone = %s AND r.reservation_time = %s
        """
        cursor.execute(other_res_query, (user_phone, reservation_time))
        other_res = cursor.fetchone()
            
        if other_res:
            if not force:
                res_name = other_res['restaurant_name']
                return jsonify({
                    "success": False,
                    "status": "confirm", 
                    "type": "DUPLICATE_TIME",
                    "message": f"이미 '{res_name}' 식당에 {time_str} 예약이 존재합니다. 예약을 변경하시겠습니까?"
                })

# 사용자가 변경을 수락(force=True)했다면 기존 예약 삭제
            else:
                cursor.execute("DELETE FROM reservations WHERE reservation_id = %s", (other_res['reservation_id'],))

        # [3] 모든 검사 통과 시 실제 예약 정보 저장
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

# API: 예약 취소하기 (reservations 테이블에서 삭제)
@app.route('/api/cancel_reservation', methods=['POST'])
def cancel_reservation():
    data = request.get_json()
    res_id = data.get('restaurant_id')
    name = data.get('user_name')
    phone = data.get('user_phone')

    conn = get_db_connection()
    if not conn: return jsonify({"success": False, "message": "DB 연결 실패"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # 1. 먼저 해당 정보와 일치하는 예약이 있는지 확인
        check_query = """
            SELECT reservation_id FROM reservations 
            WHERE restaurant_id = %s
            AND user_name = %s AND user_phone = %s
        """
        cursor.execute(check_query, (res_id, name, phone))
        result = cursor.fetchone()

        if result:
            # 2. 일치하는 정보가 있다면 삭제!
            cursor.execute("DELETE FROM reservations WHERE reservation_id = %s", (result['reservation_id'],))
            conn.commit()
            return jsonify({"success": True, "message": "예약이 성공적으로 취소되었습니다."})
        else:
            # 3. 정보가 일치하지 않으면 실패 알림
            return jsonify({"success": False, "message": "입력하신 정보와 일치하는 예약이 없습니다."})

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
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

# 관리자 모드 버튼 실행하기(예약 내역 전체 확인)
@app.route('/api/admin_reservations')
def admin_reservations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    # 예약 정보와 식당 이름을 합쳐서(JOIN) 가져옵니다.
    query = """
        SELECT r.*, m.restaurant_name 
        FROM reservations r
        JOIN michelin_star_restaurants m ON r.restaurant_id = m.restaurant_id
        ORDER BY r.reservation_time ASC
    """
    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()
    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True, port=5000)