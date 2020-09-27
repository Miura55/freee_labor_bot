# coding: utf-8
from flask import Flask, request, abort, jsonify, render_template
from flask_cors import CORS
import datetime
import os
import json
import requests
import base64
from logging import getLogger
from dotenv import load_dotenv

# LINE bot SDK
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

# Cloudant
from cloudant.client import Cloudant
from cloudant.document import Document
from cloudant.adapters import Replay429Adapter

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# LINE BOTの設定
CHANNEL_ACCESS_TOKEN = os.environ.get('CHANNEL_ACCESS_TOKEN')
CHANNEL_SECRET = os.environ.get('CHANNEL_SECRET')
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
attend_menu_id = os.environ.get('ATTEND_MENU_ID')
on_work_menu_id = os.environ.get('ON_WORK_MENU_ID')

# RECIPT OCRの設定
OCR_API_URL = os.environ.get('OCR_API_URL')
OCR_API_KEY = os.environ.get('OCR_API_KEY')

# LIFFの用意
LIFF_ID = os.environ.get('LIFF_ID')

# Cloudantの接続
cloudant_url = os.environ.get('CLOUDANT_URL')
cloudant_username = os.environ.get('CLOUDANT_USERNAME')
cloudant_password = os.environ.get('CLOUDANT_PASSWORD')

db_client = Cloudant(
    cloudant_username,
    cloudant_password,
    url=cloudant_url,
    adapter=Replay429Adapter(retries=10, initialBackoff=0.01)
)


company_id = int(os.environ.get('COMPANY_ID'))

# アプリケーションの設定
app = Flask(__name__, static_folder='static')
CORS(app)
logger = getLogger("werkzeug")


@app.route('/')
def connect():
    return "Hello from Flask"


@app.route('/regist')
def regist():
    response = requests.get(
        'https://api.freee.co.jp/hr/api/v1/companies/{}/employees'.format(
            company_id),
        headers={
            'Authorization': 'Bearer {}'.format(select_freee_token())
        }
    )
    logger.info(response.json())
    return render_template('regist.html', liffId=LIFF_ID, employees=response.json())


@app.route('/reqlogin')
def reqlogin():
    return render_template('reqlogin.html')


@app.route('/submit', methods=['POST'])
def submit():
    body = request.get_json()
    logger.info('Request body: {}'.format(json.dumps(body, indent=4)))
    # トランザクションデータを作成
    data = {
        '_id': body['user_id'],
        'employee_id': body['employee_id'],
        'fix_time': False
    }
    db_client.connect()
    labor_bot_db = db_client['labor_bot']
    labor_bot_db.create_document(data)
    db_client.disconnect()
    # リッチメニューを設定
    line_bot_api.link_rich_menu_to_user(body['user_id'], attend_menu_id)
    return "OK!"


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
    user_id = event.source.user_id
    employee_id = select_user_data(user_id, 'employee_id')
    is_fixing_time = select_user_data(user_id, 'fix_time')
    flag = ''
    if event.message.text == '出勤':
        message = '出勤しました'
        flag = 'clock_in'
        line_bot_api.link_rich_menu_to_user(
            user_id, on_work_menu_id)
    elif event.message.text == '退勤':
        message = '退勤しました'
        flag = 'clock_out'
        line_bot_api.link_rich_menu_to_user(
            user_id, attend_menu_id)
    elif event.message.text == '打刻修正':
        message = '本日の出勤打刻修正をします。以下の例にしたがって打刻修正をしてください。\n'\
                  '例) 09:00'
        insert_bot_status(user_id, 'fix_time', True)
    elif is_fixing_time:
        message = '修正しました'
        insert_bot_status(user_id, 'fix_time', False)
    else:
        message = event.message.text

    if flag:
        response = requests.post(
            'https://api.freee.co.jp/hr/api/v1/employees/{}/time_clocks'.format(
                employee_id),
            headers={
                'Authorization': 'Bearer {}'.format(select_freee_token())
            },
            json={
                "company_id": company_id,
                "type": flag
            }
        )
        logger.info('Result: {}'.format(json.dumps(
            response.json(), indent=4, ensure_ascii=False)))
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=message))


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)

    image = base64.b64encode(message_content.content)
    response_message = call_recipt(image)
    line_bot_api.reply_message(
        event.reply_token,
        messages=response_message
    )


@handler.add(FollowEvent)
def handle_follow(event):
    message = "{}{}".format(
        '友だち追加ありがとうございます。オフィスの作業を効率化しよう！',
        '\n※このアカウントは空想上のプロトタイプなので、実際の挙動とは異なります')
    with open('regist_message.json', 'r', encoding='utf-8') as f:
        regist_form_content = json.load(f)
    regist_form_content['footer']['contents'][0]['action']['uri'] \
        = 'https://liff.line.me/{}'.format(LIFF_ID)
    regist_form_message = FlexSendMessage.new_from_json_dict({
        "type": "flex",
        "altText": "アカウントの連携",
        "contents": regist_form_content
    })
    line_bot_api.reply_message(
        event.reply_token,
        [
            TextSendMessage(text=message),
            regist_form_message,
            StickerSendMessage(
                package_id=11537,
                sticker_id=52002739
            )
        ]
    )


def select_user_data(user_id, column):
    db_client.connect()
    labor_bot_db = db_client['labor_bot']
    with Document(labor_bot_db, user_id) as document:
        user_doc = document[column]
    db_client.disconnect()
    return user_doc

def insert_bot_status(user_id, column, status):
    db_client.connect()
    labor_bot_db = db_client['labor_bot']
    with Document(labor_bot_db, user_id) as document:
        document[column] = status
    db_client.disconnect()


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
    logger.info('Recipt Data: {}'.format(json.dumps(response_json, indent=4)))

    if response.status_code == 200:
        # freeeへ申請
        expense_result = insert_expence(response_json)
        logger.info('Expensed Data: {}'.format(
            json.dumps(expense_result, indent=4)))

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
        contents += [
            {
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
            }
        ]
        recipt_form['body']['contents'] = contents
        response_message = FlexSendMessage.new_from_json_dict({
            "type": "flex",
            "altText": "レシート",
            "contents": recipt_form
        })
    else:
        response_message = TextSendMessage(text="レシートが読み取れませんでした。")
    return response_message


def select_freee_token():
    # freee APIの設定
    db_client.connect()
    freee_tokens = db_client['freee_tokens']
    with Document(freee_tokens, os.environ.get('TOKEN_DOC_ID')) as document:
        freee_access_token = document['access_token']
    db_client.disconnect()
    return freee_access_token


def insert_expence(recipt_data):
    transaction_date = recipt_data['result']['paymentInfo']['date']
    # 明細の記入
    items = []
    for item in recipt_data['result']['items']:
        items.append({
            "transaction_date": transaction_date,
            "description": item['name'],
            "amount": item['priceInfo']['price']
        })

    response = requests.post(
        'https://api.freee.co.jp/api/1/expense_applications',
        headers={
            'Authorization': 'Bearer {}'.format(select_freee_token())
        },
        json={
            "company_id": company_id,
            "title": "立替申請",
            "issue_date": datetime.date.today().strftime('%Y-%m-%d'),
            "description": recipt_data['result']['storeInfo']['name'],
            "editable_on_web": False,
            "expense_application_lines": items
        }
    )
    return response.json()


if __name__ == "__main__":
    app.debug = True
    app.run()
