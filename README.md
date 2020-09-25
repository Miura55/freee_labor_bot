# freee_labor_bot

freee と LINE の API を使った労務 bot のサンプル

## システム構成

[システム構成](https://github.com/Miura55/freee_labor_bot/blob/master/system_arch.svg)

## セットアップ方法

1. `.env_sample`をコピーし、ファイル名を`.env`にして必要な環境変数をセットする(`LIFF_ID`については 4．の設定を行う際に出力される LIFF ID をセットする)
2. 以下のコマンドで必要なライブラリをインストール

```
pip install -r requirements.txt
```

3. ngrok を起動し、Messaging API 及び LINE ログイン(LIFF を管理するチャネル)のエンドポイント URL に設定する

```
ngrok http 5000
```

4. LIFF ID を`.env`の`LIFF_ID`にセットする

5. `app.py`でアプリを実行する。

## リッチメニューの登録

リッチメニューの設定には API を使用するため、`static/img`内にあるリッチメニューの画像を設定する場合につかう Json オブジェクト（[リッチメニューの API ドキュメント](https://developers.line.biz/ja/reference/messaging-api/#rich-menu)）

- 業務時間外に表示するメニューのオブジェクト(`static/img/richmenu_attend.jpg`)

```
{
  "size": {
    "width": 2500,
    "height": 1686
  },
  "selected": false,
  "name": "Attend",
  "chatBarText": "Tap to attend",
  "areas": [
	{
		"bounds": {
			"x": 0,
			"y": 0,
			"width": 2500,
			"height": 1686
		},
		"action": {
			"type":"message",
			"label":"出勤",
			"text":"出勤"
		}
    }
  ]
}
```

- 業務中に表示するメニューのオブジェクト(`static/img/richmenu_on_work.jpg`)

```
{
  "size": {
    "width": 2500,
    "height": 1686
  },
  "selected": false,
  "name": "Attend",
  "chatBarText": "Tap to attend",
  "areas": [
	{
		"bounds": {
			"x": 0,
			"y": 0,
			"width": 1686,
			"height": 1686
		},
		"action": {
			"type":"uri",
			"uri":"https://line.me/R/nv/camera/"
		}
    },
    {
		"bounds": {
			"x": 1686,
			"y": 0,
			"width": 814,
			"height": 843
		},
		"action": {
			"type":"message",
			"label":"退勤",
			"text":"退勤"
		}
    },
    {
		"bounds": {
			"x": 1686,
			"y": 843,
			"width": 814,
			"height": 843
		},
		"action": {
			"type":"message",
			"label":"打刻修正",
			"text":"打刻修正"
		}
    }
  ]
}
```
