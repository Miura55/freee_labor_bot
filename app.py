# coding: utf-8
from flask import Flask, request, abort, jsonify, render_template
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
import requests
import base64
from logging import getLogger
from linepay import LinePayApi

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    FollowEvent,
    MessageEvent,
    TextMessage,
    TextSendMessage,
    StickerSendMessage,
    FlexSendMessage,
    ImageMessage,
)

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# LINE BOTの設定
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# RECIPT OCRの設定
OCR_API_URL = os.environ.get('OCR_API_URL')
OCR_API_KEY = os.environ.get('OCR_API_KEY')

# アプリケーションの設定
app = Flask(__name__, static_folder='static')
CORS(app)
logger = getLogger("werkzeug")


@app.route('/')
def connect():
    return "Hello from Flask"


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']
    # get request body as text
    body = request.get_data(as_text=True)
    logger.info("Request body: {}".format(body))
    # Connect Check
    data = json.loads(body)
    userId = data["events"][0]["source"]["userId"]
    if userId == "Udeadbeefdeadbeefdeadbeefdeadbeef":
        return "OK"

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=event.message.text))


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)

    image = base64.b64encode(message_content.content)
    recipt_message = call_recipt(image)
    line_bot_api.reply_message(
        event.reply_token,
        messages=recipt_message
    )


@handler.add(FollowEvent)
def handle_follow(event):
    message = "{}{}".format(
        '友だち追加ありがとうございます！オフィスの作業を効率化しよう！',
        '\n※このアカウントは空想上のプロトタイプなので、実際の挙動とは異なります')
    line_bot_api.reply_message(
        event.reply_token,
        [
            TextSendMessage(text=message),
            StickerSendMessage(
                package_id=11537,
                sticker_id=52002739
            )
        ]
    )


def call_recipt(image):
    # レシートの内容を読み込む
    response = requests.post(
        OCR_API_URL,
        headers={
            'x-linebrain-apigw-api-key': OCR_API_KEY
        },
        json={
            'imageContent': image
        }
    )
    response_json = response.json()
    logger.info('Request Body: {}'.format(response_json))

    with open('sample_recipt.json', 'r', encoding='utf-8') as f:
        recipt_form = json.load(f)

    # 読み込み結果を出力するメッセージを作成
    recipt_form['header']['contents'][2]['text'] = response_json['result']['storeInfo']['name']

    contents = [{
        "type": "separator",
        "color": "#000000"
    }]
    for item in response_json['result']['items']:
        box = {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": item['name'],
                    "size": "lg",
                    "align": "start",
                    "contents": []
                },
                {
                    "type": "text",
                    "text": "¥{}".format(item['priceInfo']['price']),
                    "color": "#000000",
                    "align": "end",
                    "gravity": "bottom",
                    "contents": []
                }
            ]
        }
        contents.append(box)

    # 合計金額を挿入
    contents += [{
        "type": "separator",
        "color": "#000000"
    },
        {
        "type": "box",
        "layout": "horizontal",
        "contents": [
            {
                "type": "text",
                "text": "合計",
                "contents": []
            },
            {
                "type": "text",
                "text": "¥{}".format(response_json['result']['totalPrice']['price']),
                "align": "end",
                "contents": []
            }
        ]
    }]
    recipt_form['body']['contents'] = contents
    recipt_message = FlexSendMessage.new_from_json_dict({
        "type": "flex",
        "altText": "レシート",
        "contents": recipt_form
    })
    return recipt_message


if __name__ == "__main__":
    app.debug = True
    app.run()
