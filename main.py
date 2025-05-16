import json
import os

from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, Response, session
import requests

from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(16)

password_hash = generate_password_hash('Nwa741741')
# https://portal.qiniu.com/ai-inference/model 孩子们自己去申请一下 免费3个月deepseek 去申请个key替换下面
API_KEY = "sk-xxxxx"
url = "https://api.qnaigc.com/v1/chat/completions"


# 下面是返回页面----------------------------------
@app.route('/')
def index_page():
    return render_template('index.html')

@app.route('/lucky')
def lucky_page():
    return "直接返回文字"

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/home')
def home_page():
    return render_template('home.html')

# 下面是访问接口-----------------------------------------------------
@app.route('/test-api', methods=['POST'])
def test_api():
    # 此处可以添加你的接口逻辑
    data = {'message': '接口测试成功！'}
    return jsonify(data)


@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"收到的登录请求 - 用户名: {username}, 密码: {password}")
        # 改第三方验证登录
        api_url = 'https://admin.luckynwa.top/proxyApi/login'
        send_data = {'username': username, 'password': password}
        response = requests.post(
            api_url,
            json=send_data,  # 使用json参数自动设置Content-Type为application/json
            headers={'Content-Type': 'application/json'}
        )
        response_data = response.json()
        print(f"收到的登录响应 - res: {response_data}")
        if response_data.get('code') == 200:
            token = response_data.get('token')
            if token:
                # session['auth_token'] = token  # 存储token到session
                # print(session.get('auth_token'))  # 使用get方法避免KeyError
                url = 'https://admin.luckynwa.top/proxyApi/system/config/list'
                params = {
                    'pageNum': 1,
                    'pageSize': 10,
                    'configKey': 'lucky.ai'
                }
                headers = {
                    'Authorization': f'Bearer {token}'
                }

                response2 = requests.get(url, params=params, headers=headers)
                response_data2 = response2.json()
                print(f"AI配置 - res: {response_data2}")
                if response_data2.get('code') == 200:

                    config_value = response_data2.get('rows')[0].get('configValue')
                    part1, part2 = config_value.split('@')
                    # 存储到session中
                    session['api_url'] = part1
                    session['api_key'] = part2
                    print(session.get('api_url'))
                    print(session.get('api_key'))

                    flash('登录成功！', 'success')
                    return redirect(url_for('home_page'))
                else:
                    flash('获取AI配置失败', 'error')
                    return render_template('login.html')
        else:
            flash('账号或密码错误，或API请求失败！', 'error')
            return render_template('login.html')
        # if username == 'luckyNwa' and check_password_hash(password_hash, password):
        #     flash('登录成功！', 'success')
        #     return redirect(url_for('home_page'))
        # else:
        #     flash('账号或密码错误！', 'error')
        #     return render_template('login.html')
    else:
        return render_template('login.html')

@app.route('/api/chatAll', methods=['POST'])
def chat():
    API_KEY = session.get('api_key')
    url = session.get('api_url')
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

    API_KEY = session.get('api_key')
    url = session.get('api_url')
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