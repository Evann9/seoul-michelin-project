from flask import Flask, render_template
import json
import os
app=Flask(__name__)

@app.route('/')
def index():
    print("hello1")
    try: 
           
           cards=[]
           with open('/static/cards.json','r',encoding='utf-8') as f:
                cards=json.load(f)
           slides=[]
           slides=[cards[i:i+3] for i in range(0,len(cards)/3,1)] 
        # 18개의 기사 태그를 3개씩 잘라서 1슬라이드에 할당 > [i:i+3] :3개니까 i+3전인 i+2까지만 할당 / 제너레이터 사용
    except Exception as e:
        print("error", e)
         
        return
    return render_template('index.html',slides=slides)

if __name__=='__main__':
    print("hello2")
    app.run(debug=True, port=5000)