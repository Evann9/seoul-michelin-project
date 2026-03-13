# =====================================================================
# [0] 웹 서버 준비물 (Import)
# 프로그램을 만들기 위해 똑똑한 사람들이 미리 만들어둔 도구 상자들을 가져옵니다.
# =====================================================================
from flask import Flask, request, jsonify, render_template # 웹 서버를 만들고, 화면을 그리고, 통신하는 핵심 도구
from flask_cors import CORS # 보안 경찰관입니다. 다른 주소에서 우리 서버로 몰래 데이터 요청하는 걸 허락해 줍니다.
import mysql.connector # 파이썬이 MySQL(데이터베이스 창고)과 대화할 수 있게 해주는 번역기입니다.
import pickle # 비밀번호 같은 중요 정보를 암호화해서 저장해 둔 파일(.dat)을 열어보는 도구입니다.
import os
import re

app = Flask(__name__) # "이제부터 여기가 웹 서버의 심장부야!" 라고 선언하는 것입니다.
CORS(app) # 우리 서버에 보안 허가증을 발급해 줍니다.

# =====================================================================
# [1] DB 연결 설정 (창고 문 열기)
# =====================================================================
# 데이터베이스라는 거대한 창고에 들어갈 때마다 매번 아이디/비밀번호를 칠 수 없으니,
# 필요할 때마다 자동으로 문을 열어주는 만능 열쇠 함수를 만듭니다.
def get_db_connection():
    try: # "일단 이 방법으로 문 열기를 시도해 봐!" (에러 방지용 안전망)
        # 'mydb.dat'라는 비밀 금고 파일을 읽기 모드(rb)로 엽니다.
        with open('mydb.dat', 'rb') as f:
            config = pickle.load(f) # 암호화된 정보를 파이썬이 읽을 수 있게 해독합니다.
        
        # 해독한 정보(아이디, 비번 등)를 넣어서 창고(MySQL)와 선을 연결(connect)합니다.
        conn = mysql.connector.connect(**config) 
        return conn # 연결된 선(통신망)을 밖으로 전달해 줍니다.
    except Exception as e: # 만약 금고가 안 열리거나 비번이 틀리면 여기로 빠집니다.
        print(f"DB 연결 실패: {e}") # 터미널에 빨간 글씨로 왜 실패했는지 알려줍니다.
        return None


# =====================================================================
# [홈페이지 첫 접속 시 화면 그리기]
# 사용자가 인터넷 주소창에 '우리사이트.com/' 을 치고 들어왔을 때 실행됩니다.
# =====================================================================
@app.route('/')
def index():
    restaurants = [] # 식당 정보를 담아둘 빈 보따리를 준비합니다.
    conn = get_db_connection() # 창고 문을 엽니다.
    
    if conn: # 창고 문이 무사히 열렸다면
        # cursor: 창고 안을 돌아다니며 데이터를 꺼내오는 심부름꾼 카트입니다.
        # dictionary=True: 데이터를 가져올 때 '이름표(Key)'도 같이 가져오라는 뜻입니다. (예: {'name': '가온'})
        cursor = conn.cursor(dictionary=True) 
        try:
            # [핵심] 창고지기에게 내리는 명령서(SQL)입니다.
            # "michelin_star_restaurants 테이블에서 아이디, 이름, 별점, 요리종류, 주소, 가격을 가져와!"
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
            cursor.execute(sql) # 심부름꾼에게 명령서를 읽어줍니다.
            restaurants = cursor.fetchall() # 심부름꾼이 긁어온 모든 데이터(all)를 보따리에 쏟아 붓습니다.


            img_root = os.path.join(os.getcwd(), 'static', 'img')
            actual_folders = os.listdir(img_root) if os.path.exists(img_root) else []

            for res in restaurants:
                db_name = res['name']
                # 진명님이 수정하신 대로 폴더명을 찾아서 넣어줍니다.
                match_folder = next((f for f in actual_folders if f == db_name), db_name)
                res['img_folder'] = match_folder


            # [데이터 가공] 구(gu) 정보 추출 로직
            # DB에는 '서울시 강남구 역삼동' 이라고 길게 적혀있으니, 파이썬이 이걸 쪼개서 '강남구'만 빼냅니다.
            for res in restaurants:
                addr_parts = res['addr'].split() # 띄어쓰기 기준으로 글자를 쪼갭니다. ['서울시', '강남구', '역삼동']
                # 두 번째 단어(인덱스 1)가 구 이름이므로, 그걸 'gu'라는 새 꼬리표에 담아줍니다.
                res['gu'] = addr_parts[1] if len(addr_parts) > 1 else "기타"

                db_name = res['name']
                match_folder = next((f for f in actual_folders if db_name in f), db_name)

                res['img_folder'] = match_folder

        except Exception as e:
            print(f"DB Error: {e}") # 데이터 꺼내다 넘어지면 에러 출력
        finally:
            # 문을 열었으면 반드시 닫아야 합니다! 안 그러면 서버가 과부하로 터집니다.
            cursor.close() 
            conn.close()        

    # 준비된 HTML 도화지(index.html)에 방금 꽉 채운 식당 보따리(restaurants)를 던져주면서 화면을 그리라고 명령합니다!
    return render_template('index.html', restaurants=restaurants)


# =====================================================================
# [2] API: 조건에 맞는 식당 목록 검색 
# 자바스크립트가 장바구니(selectedFilters)를 들고 올 때마다 실행되는 곳입니다.
# =====================================================================
@app.route('/api/filter', methods=['POST'])
def filter_restaurants():
    filters = request.get_json() # 자바스크립트가 보낸 장바구니 내용물을 뜯어봅니다.
    gu_filter = filters.get('gu', '전체') # 장바구니에서 '구' 정보만 쏙 빼냅니다. 없으면 '전체'로 간주합니다.

    conn = get_db_connection()
    if not conn: return jsonify({"error": "DB 연결 실패"}), 500 # 창고 못 열면 돌려보냅니다.

    cursor = conn.cursor(dictionary=True)

    try:
        # [레고 조립식 SQL 쿼리] 
        # 조건이 뭐가 올지 모르니, 일단 기본 뼈대만 만들어 둡니다. (WHERE 1=1 은 무조건 참이라는 뜻의 마법의 주문입니다)
        # IF 문은 "f.restaurant_id 가 존재하면(찜했으면) 1, 아니면 0을 반환해!" 라는 조건부 꼬리표입니다.
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
        params = [] # 조건문(%) 자리에 들어갈 진짜 값들을 모아두는 리스트입니다.

        # 1. 구 필터 조립
        if gu_filter != '전체':
            query += " AND m.address LIKE %s" # "주소에 특정 글자가 포함된(%s) 것만 찾아!"
            params.append(f"%{gu_filter.replace('구', '')}%") # '강남구' -> '%강남%' 으로 변환해서 넣습니다.

        # 2. 별점 필터 조립
        # 장바구니에 별점 정보가 1개 이상 있다면
        if filters.get('grade') and len(filters['grade']) > 0:
            # placeholders: 별점 개수만큼 '%s, %s' 모양을 만듭니다.
            placeholders = ', '.join(['%s'] * len(filters['grade']))
            query += f" AND m.grade IN ({placeholders})" # "별점이 이 명단 안에 있는 것만 찾아!"
            params.extend(filters['grade']) # 바구니에 있던 3 Stars 등을 꺼내 넣습니다.

        # 3. 음식 종류 필터 조립 (별점과 완벽히 같은 원리입니다)
        if filters.get('cuisine') and len(filters['cuisine']) > 0:
            placeholders = ', '.join(['%s'] * len(filters['cuisine']))
            query += f" AND m.cuisine_type IN ({placeholders})"
            params.extend(filters['cuisine'])
            
        # 4. 찜(즐겨찾기) 필터 조립
        if filters.get('favorite') == True:
            # 찜 정보는 아까 LEFT JOIN으로 가져왔으니, 찜 기록이 있는(NOT NULL) 녀석만 거릅니다.
            query += " AND f.restaurant_id IS NOT NULL"

        # 최종 완성된 레고(명령서)를 심부름꾼에게 주면서 괄호 안에 들어갈 단어(params)도 같이 줍니다.
        cursor.execute(query, tuple(params))
        # 긁어온 데이터를 자바스크립트가 알아먹기 쉽게 JSON 형태로 예쁘게 포장해서 돌려보냅니다!
        results = cursor.fetchall()
        img_root = os.path.join(os.getcwd(), 'static', 'img')
    # 1. 실제 폴더명 리스트 (예: ['정식당 Jungsik', '가온'])
        actual_folders = os.listdir(img_root) if os.path.exists(img_root) else []
    
        cleaned_folders = [re.sub(r'[^가-힣]', '', f) for f in actual_folders]

        for res in results:
        # DB에서 가져온 식당 이름에서 한글만 남깁니다. (예: "정식당" 또는 "정식당 Jungsik")
            db_name = res.get('restaurant_name') or res.get('name')
            db_hangul = re.sub(r'[^가-힣]', '', db_name)

            match_folder = db_name  # 찾지 못했을 때를 대비한 기본값
        
        # 3. [핵심 로직] 한글 리스트(cleaned_folders)를 돌면서 인덱스(i)를 확인합니다.
            for i in range(len(cleaned_folders)):
            # 만약 한글로 뽑아낸 이름이 서로 같다면?
                if db_hangul == cleaned_folders[i]:
                # 4. 정답은 한글 리스트가 아니라, '같은 번호'의 실제 리스트(actual_folders)에서 가져옵니다!
                    match_folder = actual_folders[i]
                    break
        
            res['img_folder'] = match_folder

        return jsonify(results)
            
    except Exception as e:
        print(f"쿼리 실행 에러: {e}")
        return jsonify({"error": "데이터 조회 실패"}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================================
# [3] API: 즐겨찾기(하트) 껐다 켜기
# 하트를 누를 때마다 "추가해라", "빼라" 판단하는 토글(Toggle) 스위치입니다.
# =====================================================================
@app.route('/api/toggle_favorite', methods=['POST'])
def toggle_favorite():
    data = request.get_json() # 자바스크립트가 보낸 식당 ID(res_id)를 받습니다.
    res_id = data.get('restaurant_id')
    
    conn = get_db_connection()
    if not conn: return jsonify({"success": False}), 500

    cursor = conn.cursor()
    try:
        # 먼저 창고(favorites 테이블)에 이 식당 ID가 이미 저장되어 있는지 검사합니다.
        cursor.execute("SELECT favorites_id FROM favorites WHERE restaurant_id = %s", (res_id,))
        result = cursor.fetchone() # 딱 하나만 가져와 봅니다.

        if result:
            # 이미 있으면? (빨간 하트 상태였다면) -> 창고에서 삭제합니다! (빈 하트로 변경)
            cursor.execute("DELETE FROM favorites WHERE restaurant_id = %s", (res_id,))
            action = 'removed'
        else:
            # 없으면? (빈 하트 상태였다면) -> 창고에 새로 집어넣습니다! (빨간 하트로 변경)
            cursor.execute("INSERT INTO favorites (restaurant_id) VALUES (%s)", (res_id,))
            action = 'added'
            
        conn.commit() # [중요] 삽입, 삭제, 수정 등 창고 내용이 바뀌면 도장(commit)을 쾅 찍어야 진짜 반영됩니다.
        return jsonify({"success": True, "action": action}) # 자바스크립트에게 "성공했어! 결과는 이거야!" 라고 알려줍니다.
    except Exception as e:
        conn.rollback() # 에러가 나면 방금 하려던 작업을 다 취소(되감기)해서 창고가 망가지는 걸 막습니다.
        print(f"즐겨찾기 에러: {e}")
        return jsonify({"success": False}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================================
# [4] API: 예약 가능 시간 확인하기
# 모달창이 열리기 직전, "이 식당 몇 시가 이미 예약 찼어?" 라고 물어보는 곳입니다.
# =====================================================================
@app.route('/api/check_reservation', methods=['GET'])
def check_reservation():
    restaurant_id = request.args.get('id') # 이번엔 URL 주소창 뒤에 붙은 '?id=숫자' 에서 빼옵니다. (GET 방식)
    conn = get_db_connection()
    if not conn: return jsonify([]), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # 예약 장부(reservations)에서 해당 식당의 예약된 '시간'만 싹 다 가져옵니다.
        query = "SELECT reservation_time FROM reservations WHERE restaurant_id = %s"
        cursor.execute(query, (restaurant_id,))
        results = cursor.fetchall()
        
        # 가져온 결과들 중에서 시간 번호(1, 2, 3 등)만 쏙쏙 뽑아 숫자 리스트로 만듭니다. (예: [1, 3])
        booked_times = [row['reservation_time'] for row in results]
        
        # 이 리스트를 자바스크립트에게 보내면, 자바스크립트가 알아서 그 시간 버튼을 클릭 못하게 막아버립니다!
        return jsonify(booked_times)
    except Exception as e:
        print(f"예약 조회 에러: {e}")
        return jsonify([]), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================================
# [5] API: 실제 예약 정보 저장하기 (핵심 관문)
# 온갖 중복과 에러를 방어하는 철통 보안 구역입니다!
# =====================================================================
@app.route('/api/make_reservation', methods=['POST'])
def make_reservation():
    data = request.get_json() # 자바스크립트가 보낸 편지 봉투(예약 정보들)를 엽니다.
    restaurant_id = data.get('restaurant_id')
    user_name = data.get("user_name")
    user_phone = data.get('user_phone')
    reservation_time = data.get('time') 
    
    # [히든 카드] 강제 예약 스위치입니다. 처음에 JS는 무조건 False로 보냅니다.
    # 만약 손님이 "예약 덮어쓸래!" 하고 확인을 누르면 JS가 이걸 True로 바꿔서 다시 보냅니다.
    force = data.get('force', False) 

    # 안내창에 예쁘게 "18:00" 이라고 띄워주기 위한 번역기입니다.
    time_config = {"1": "18:00", "2": "19:00", "3": "20:00", "4": "21:00"}
    time_str = time_config.get(str(reservation_time), "해당 시간")

    conn = get_db_connection()
    if not conn: return jsonify({"success": False}), 500

    # buffered=True: 심부름꾼이 데이터를 조금씩 안 나르고 한 번에 왕창 들고 오게 해서 꼬임을 방지합니다.
    cursor = conn.cursor(dictionary=True, buffered=True)
    try:
        # ------------------------------------------------------------
        # [방어막 1단계] 사칭 방지: 번호는 같은데 이름이 다른 경우
        # ------------------------------------------------------------
        # "이 폰 번호로 저장된 다른 예약이 있는지 찾아봐!"
        cursor.execute("SELECT user_name FROM reservations WHERE user_phone = %s LIMIT 1", (user_phone,))
        existing_user = cursor.fetchone()
        
        # 찾았는데 이름이 지금 예약하려는 사람과 다르다면? 오타이거나 남의 번호입니다.
        if existing_user and existing_user['user_name'] != user_name:
            return jsonify({
                "success": False,
                "status": "error",
                "type": "USER_MISMATCH",
                "message": " 이름이나 번호를 다시 확인해 주세요."
            })
            
        # ------------------------------------------------------------
        # [방어막 2단계] 동일 식당 중복 예약 방지
        # ------------------------------------------------------------
        # "같은 번호로, 이 똑같은 식당에 이미 예약한 적이 있는지 찾아봐!"
        cursor.execute("SELECT reservation_id FROM reservations WHERE user_phone = %s AND restaurant_id = %s", (user_phone, restaurant_id))
        if cursor.fetchone():
            return jsonify({
                "success": False, 
                "status": "error",
                "type": "ALREADY_BOOKED_HERE", 
                "message": "이미 이 식당에 예약된 내역이 있어 중복 예약이 불가능합니다."
            })

        # ------------------------------------------------------------
        # [방어막 3단계] 다른 식당 동시간대 예약 방지 (홍길동 소환 불가)
        # ------------------------------------------------------------
        # "식당은 다르지만, 똑같은 시간에 이 폰 번호로 예약한 게 있는지 찾아봐!"
        # 식당 이름도 알아야 "어느 식당에 예약되어 있습니다"라고 말해줄 수 있으니 JOIN을 써서 식당 이름까지 묶어서 가져옵니다.
        other_res_query = """
            SELECT m.restaurant_name, r.reservation_id 
            FROM reservations r
            JOIN michelin_star_restaurants m ON r.restaurant_id = m.restaurant_id
            WHERE r.user_phone = %s AND r.reservation_time = %s
        """
        cursor.execute(other_res_query, (user_phone, reservation_time))
        other_res = cursor.fetchone()
            
        # 어라? 동시간대에 다른 식당 예약이 발견됐네요!
        if other_res:
            if not force: # 아직 손님이 "강제로 덮어써!"(force=True) 라고 명령하지 않은 상태라면
                res_name = other_res["restaurant_name"]
                # 에러(error)가 아니라 확인(confirm) 상태로 돌려보내서 팝업창을 띄우게 합니다.
                return jsonify({
                    "success": False,
                    "status": "confirm", 
                    "type": "DUPLICATE_TIME",
                    "message": f"이미 '{res_name}' 식당에 {time_str} 예약이 존재합니다. 예약을 변경하시겠습니까?"
                })

            else: 
                # 손님이 팝업창에서 "예(변경할래)"를 눌러서 force=True로 다시 요청이 온 상태입니다!
                # 그러면 가차 없이 옛날 예약을 삭제해 버립니다.
                cursor.execute("DELETE FROM reservations WHERE reservation_id = %s", (other_res['reservation_id'],))

        # ------------------------------------------------------------
        # [최종 합격] 모든 검사 통과 시 실제 장부에 기록
        # ------------------------------------------------------------
        insert_query = """
            INSERT INTO reservations (restaurant_id, user_name, user_phone, reservation_time) 
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (restaurant_id, user_name, user_phone, reservation_time))
        conn.commit() # 쾅! 도장을 찍어서 진짜 저장합니다.
        
        return jsonify({"success": True}) # JS야, 미션 완료다!
        
    except Exception as e:
        conn.rollback() # 뭔가 잘못되면 다 취소!
        print(f"예약 저장 에러: {e}")
        return jsonify({"success": False}), 500
    finally:
        cursor.close()
        conn.close()   

# =====================================================================
# [6] API: 예약 취소하기
# 사용자가 이름과 폰번호를 입력하고 취소 버튼을 눌렀을 때 작동합니다.
# =====================================================================
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
        # 1. 묻지도 따지지도 않고 지우면 안 되니까, '이 식당 + 이 이름 + 이 번호'가 모두 일치하는 예약이 있는지 먼저 확인합니다.
        check_query = """
            SELECT reservation_id FROM reservations 
            WHERE restaurant_id = %s
            AND user_name = %s AND user_phone = %s
        """
        cursor.execute(check_query, (res_id, name, phone))
        result = cursor.fetchone()

        if result:
            # 2. 완벽히 일치하는 예약을 찾았다면, 그 예약의 고유 ID를 타겟으로 삭제합니다!
            cursor.execute("DELETE FROM reservations WHERE reservation_id = %s", (result['reservation_id'],))
            conn.commit() # 도장 쾅!
            return jsonify({"success": True, "message": "예약이 성공적으로 취소되었습니다."})
        else:
            # 3. 아무리 찾아도 그런 예약이 없으면 거절합니다.
            return jsonify({"success": False, "message": "입력하신 정보와 일치하는 예약이 없습니다."})

    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# =====================================================================
# [7] API: 모든 예약 싹 밀어버리기 (관리자/테스트 용도)
# =====================================================================
@app.route('/api/reset_reservations', methods=['POST'])
def reset_reservations():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # TRUNCATE는 DELETE와 다릅니다. 테이블 안의 모든 데이터를 빛의 속도로 싹 다 날려버리고
        # ID 번호표도 1번부터 다시 시작하게 만드는 무시무시한 초기화 마법입니다.
        cursor.execute("TRUNCATE TABLE reservations") 
        conn.commit()
        return jsonify({"success": True, "message": "초기화 완료"})
    except Exception as e:
        conn.rollback()
        return jsonify({"success": False, "message": str(e)})
    finally:
        cursor.close()
        conn.close()

# =====================================================================
# [8] API: 관리자 모드 장부 열람
# 누가, 어느 식당에, 언제 예약했는지 전체 리스트를 보여줍니다.
# =====================================================================
@app.route('/api/admin_reservations')
def admin_reservations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # [JOIN의 마법] 예약 장부(reservations)에는 식당 고유 번호(ID)만 적혀 있습니다.
    # 사람이 읽기 편하려면 식당 이름이 필요하겠죠? 그래서 식당 테이블(michelin_star_restaurants)과
    # ID를 기준으로 이어 붙여서(JOIN) 이름까지 같이 가져옵니다. 
    # ORDER BY ... ASC: 예약 시간(1시, 2시...)이 빠른 순서대로 정렬해서 가져옵니다.
    query = """
        SELECT r.*, m.restaurant_name 
        FROM reservations r
        JOIN michelin_star_restaurants m ON r.restaurant_id = m.restaurant_id
        ORDER BY r.reservation_time ASC
    """
    cursor.execute(query)
    results = cursor.fetchall()
    
    conn.close()
    return jsonify(results) # 싹싹 긁어모은 장부 데이터를 JS로 보냅니다!


# =====================================================================
# 파이썬아, 만약 누가 널 모듈로 가져다 쓰지 않고 직접 실행(Run)했다면, 
# 5000번 포트에서 웹 서버를 켜줘! (debug=True는 코드를 고칠 때마다 서버를 자동으로 재시작해주는 꿀옵션입니다)
# =====================================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)