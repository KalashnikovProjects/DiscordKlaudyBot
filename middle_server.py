import requests
from flask import Flask, request

app = Flask(__name__)


@app.route('/v1/completions', methods=['POST'])
def completionsChatP():
    headers = request.headers
    data = request.json

    # Переносим данные в новый запрос с использованием requests
    response = requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": headers["Authorization"]}, json=data)
    content_type = response.headers.get('content-type')
    if content_type:
        return response.content, response.status_code, {'Content-Type': content_type}
    else:
        return response.content, response.status_code


@app.route('/v1/completions', methods=['GET'])
def completionsChatG():
    headers = request.headers
    data = request.json

    # Переносим данные в новый запрос с использованием requests
    response = requests.get("https://api.openai.com/v1/chat/completions", headers={"Authorization": headers["Authorization"]}, json=data)
    content_type = response.headers.get('content-type')
    if content_type:
        return response.content, response.status_code, {'Content-Type': content_type}
    else:
        return response.content, response.status_code


@app.route('/v1/completions', methods=['POST'])
def completionsP():
    headers = request.headers
    data = request.json

    # Переносим данные в новый запрос с использованием requests
    response = requests.post("https://api.openai.com/v1/completions", headers={"Authorization": headers["Authorization"]}, json=data)
    content_type = response.headers.get('content-type')
    if content_type:
        return response.content, response.status_code, {'Content-Type': content_type}
    else:
        return response.content, response.status_code


@app.route('/v1/completions', methods=['GET'])
def completionsG():
    headers = request.headers
    data = request.json

    # Переносим данные в новый запрос с использованием requests
    response = requests.get("https://api.openai.com/v1/completions", headers={"Authorization": headers["Authorization"]}, json=data)
    content_type = response.headers.get('content-type')
    if content_type:
        return response.content, response.status_code, {'Content-Type': content_type}
    else:
        return response.content, response.status_code


if __name__ == '__main__':
    app.run()
