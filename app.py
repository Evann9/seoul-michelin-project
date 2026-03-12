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
    restaurants = []  # 기본값 설정
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
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

            # 구(gu) 정보 추출
            for res in restaurants:
                addr_parts = res['addr'].split()
                res['gu'] = addr_parts[1] if len(addr_parts) > 1 else "기타"

    except Exception as e:
        print(f"DB Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

    # 데이터가 비어있어도 restaurants 변수는 반드시 전달됨
    return render_template('index.html', restaurants=restaurants)

if __name__ == '__main__':
    app.run(debug=True, port=5500)