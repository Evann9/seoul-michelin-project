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