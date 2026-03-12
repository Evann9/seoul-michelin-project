from flask import Flask, render_template, jsonify
import pymysql
import os

app = Flask(__name__)

# MariaDB 연결 정보
DB_CONFIG = {
    'host': os.getenv("DB_HOST", "127.0.0.1"),
    'port': int(os.getenv("DB_PORT", "3306")),
    'user': os.getenv("DB_USER", "root"),
    'password': os.getenv("DB_PASSWORD", "123"),
    'db': os.getenv("DB_NAME", "tp"),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

@app.route('/')
def index():
    # 1. DB에서 식당 데이터 조회
    restaurants = []
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # SQL 파일의 테이블명과 컬럼명에 맞춰 쿼리 작성
            sql = """
            SELECT 
                restaurant_name AS name, 
                grade AS star, 
                cuisine_type AS cuisine, 
                address AS addr 
            FROM michelin_star_restaurants
            """
            cursor.execute(sql)
            restaurants = cursor.fetchall()
            
            # 주소에서 '구' 정보 추출하여 데이터에 추가 (필터링용)
            for res in restaurants:
                # '서울 강남구 ...' 에서 '강남구'만 추출
                addr_parts = res['addr'].split()
                res['gu'] = addr_parts[1] if len(addr_parts) > 1 else "기타"
                
    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

    # 2. 조회된 데이터를 HTML(index.html)로 넘겨줌
    return render_template('index.html', restaurants=restaurants)

if __name__ == '__main__':
    app.run(debug=True, port=5500)