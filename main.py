import json
import os

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, Response
import requests

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(16)

password_hash = generate_password_hash('Nwa741741')
# https://portal.qiniu.com/ai-inference/model 孩子们自己去申请一下 免费3个月deepseek 去申请个key替换下面
API_KEY = "sk-29560a2015b2497b70ecd32134c0b0d9140e021fc0dae00b4a26ee4ddc585956"
url = "https://api.qnaigc.com/v1/chat/completions"

@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/home')
def home_page():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'luckyNwa' and check_password_hash(password_hash, password):
            flash('登录成功！', 'success')
            return redirect(url_for('home_page'))
        else:
            flash('账号或密码错误！', 'error')
            return render_template('login.html')
    else:
        return render_template('login.html')

@app.route('/api/chatAll', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('messages', [])[0].get('content', '')
    payload = {
        "stream": False,
        "model": "deepseek-r1",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant."
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    }
    headers = {
        "Authorization": "Bearer "+API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    return jsonify(response.json())


@app.route('/api/chatStream', methods=['POST'])
def chat_stream():
    data = request.get_json()
    user_message = data.get('messages', [])[0].get('content', '')

    payload = {
        "stream": True,
        "model": "deepseek-r1",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_message}
        ]
    }

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }

    def generate():
        try:
            with requests.post(url, json=payload, headers=headers, stream=True) as resp:
                if resp.status_code != 200:
                    yield f"data: 请求失败，状态码：{resp.status_code}\n\n"
                    return

                for chunk in resp.iter_lines():
                    if chunk:
                        decoded_chunk = chunk.decode('utf-8')
                        try:
                            # 过滤心跳信号等非数据行
                            if decoded_chunk.startswith("data:"):
                                json_str = decoded_chunk[5:].strip()
                                if json_str == "[DONE]":
                                    break
                                json_data = json.loads(json_str)
                                if 'choices' in json_data:
                                    content = json_data['choices'][0]['delta'].get('content', '')
                                    if content:
                                        # 以SSE格式发送数据
                                        yield f"data: {json.dumps({'content': content})}\n\n"
                        except json.JSONDecodeError as e:
                            yield f"data: {json.dumps({'error': '数据解析失败'})}\n\n"
                        except Exception as e:
                            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        except requests.exceptions.RequestException as e:
            yield f"data: {json.dumps({'error': '连接异常'})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )



if __name__ == '__main__':
    app.run(debug=True)