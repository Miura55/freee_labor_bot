# freee_labor_bot

freee と LINE の API を使った労務 bot のサンプル

# リッチメニューの登録

- 業務時間外に表示するメニューのオブジェクト

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

- 業務中に表示するメニューのオブジェクト

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
