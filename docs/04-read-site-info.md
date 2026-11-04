# 04. 조회로 현장 파악하기

로봇을 움직이기 전에, 이 계정에 어떤 매장과 로봇과 맵이 있는지부터 봅니다. 아래 호출은 전부 읽기 전용이라 로봇이 움직이지 않습니다. 저장소 폴더에서 CMD로 실행하세요. 예시의 번호와 이름은 모두 가짜 값입니다.

## 1. 매장 목록

```
python -m app.pudu get-store-list
```

```
{
  "message": "success",
  "data": {
    "count": 1,
    "list": [
      {
        "company_id": "100000001",
        "company_name": "예시 회사",
        "shop_id": "123456789",
        "shop_name": "예시 매장"
      }
    ]
  }
}
```

`shop_id`를 적어 두세요. 다음 호출에 계속 씁니다.

## 2. 로봇 목록

```
python -m app.pudu get-robot-list --shop-id 123456789
```

```
{
  "message": "success",
  "data": {
    "count": 1,
    "list": [
      {
        "first_active_time": 1700000000,
        "mac": "00:00:00:00:00:00",
        "nickname": "예시 로봇",
        "product_code": "PuduT300",
        "shop_id": "123456789",
        "shop_name": "예시 매장",
        "sn": "ABCDEFG0123456"
      }
    ]
  }
}
```

`sn`이 로봇의 시리얼 번호이고, 로봇을 가리키는 모든 호출에 쓰입니다. `first_active_time`은 Unix 시각(초)입니다. 이 코드는 한 번에 최대 20대까지 조회하도록 되어 있고(`limit` 20), 이 값으로 실제 서버에서 정상 응답을 받았습니다.

## 3. 로봇의 현재 맵에 있는 지점

```
python -m app.pudu get-current-map-points --sn ABCDEFG0123456
```

```
{
  "message": "SUCCESS",
  "data": {
    "list": [
      {"name": "lift_wait", "type": "parking", "x": -4.2, "y": 3.8, "z": -1.5},
      {"name": "3F-A", "type": "table", "x": 1.6, "y": 2.5, "z": -1.5}
    ],
    "total": 2
  }
}
```

지점은 푸두 맵 도구에서 사람이 미리 찍어 둔 것이고, 이름은 만든 사람 마음대로입니다. 직접 확인한 `type` 값은 `parking`과 `table` 두 가지입니다. `x`와 `y`는 맵 좌표(미터로 보임)입니다. `z`는 값이 -3.14에서 3.14 사이로 보여서 방향각(라디안)일 것으로 짐작하지만 문서로 확인하지는 못했습니다.

이 호출은 로봇이 **지금 올라가 있는 맵** 하나만 보여 줍니다. 건물에 층별 맵이 여러 개 있어도 다른 층 맵의 지점은 여기서 나오지 않습니다.

## 4. 매장에 등록된 맵 목록

```
python -m app.pudu store-map-list --shop-id 123456789
```

```
{
  "data": {
    "count": 3,
    "list": [
      {"map_name": "1F#1#예시맵"},
      {"map_name": "3F#3#예시맵"},
      {"map_name": "0#0#test"}
    ]
  },
  "message": "ok"
}
```

층별 맵이 따로 등록돼 있는지 여기서 알 수 있습니다. `map_name`은 `층 표기#층 번호#이름` 순서로 보입니다(관찰한 것이고 문서로 확인하지는 못했습니다). 이 목록에 있다는 것이 로봇이 그 맵을 쓰고 있다는 뜻은 아닙니다.

## 5. 현재 맵의 전체 요소

```
python -m app.pudu get-current-map --sn ABCDEFG0123456
```

응답이 길어서 줄여 보면 이런 모양입니다.

```
{
  "data": {
    "floor": "3F",
    "name": "3F#3#예시맵",
    "shop_id": 123456789,
    "elements": [
      {"id": "lift_wait", "name": "lift_wait", "type": "source", "mode": "parking",
       "vector": [-4.2, 3.8, -1.5]},
      {"id": "3F-El", "name": "Elevator", "type": "gate", "vector": [-3.4, 4.0, -1.5]},
      {"id": "Charge", "type": "charging_pile", "vector": [-1.7, -0.8, 0.0]},
      {"id": "1", "type": "node", "vector": [-2.3, 2.5, 0]},
      {"id": "1", "type": "track", "vector": [-0.9, 1.3, -2.3, 2.5]}
    ]
  },
  "message": "SUCCESS"
}
```

`elements`에서 확인한 `type` 값입니다. 뜻은 이름과 값으로 짐작한 것입니다.

| type | 뜻 |
|---|---|
| `source` | 3번에서 본 지점. `mode`가 `parking` 또는 `table` |
| `gate` | 문이나 엘리베이터 같은 통과 지점으로 보임. 이름이 `Elevator`인 것이 있었음 |
| `charging_pile` | 충전 위치 |
| `lslam_restarter` | 재부팅 후 위치를 다시 잡는 기준점으로 보임 |
| `node` | 주행 경로의 점. `vector`는 `[x, y, 0]` |
| `track` | 두 node를 잇는 선. `vector`는 `[시작 x, 시작 y, 끝 x, 끝 y]` |

`gate`가 있다는 것은 맵에 엘리베이터가 표시돼 있다는 뜻일 뿐이고, 로봇이 이것으로 엘리베이터를 실제로 부르는지는 확인하지 못했습니다. 이 호출도 3번처럼 현재 올라가 있는 맵 하나만 보여 줍니다.

## 6. 로봇 그룹

```
python -m app.pudu get-robot-groups --shop-id 123456789
```

```
{"data": {"groups": [{"group_id": "예시그룹ID", "group_name": "默认分组",
  "shop_id": 123456789, "shop_name": "예시 매장"}]}, "message": "SUCCESS"}
```

기본 그룹의 이름이 중국어로 오는 경우가 있습니다(`默认分组`는 "기본 그룹"). 서버가 그렇게 돌려주는 값입니다.

## 7. 로봇의 현재 위치

```
python -m app.pudu get-position --sn ABCDEFG0123456
```

```
{"data": {"floor": "1", "map_name": "3F#3#예시맵",
  "position": {"x": -1.26, "y": 0.04, "z": 0.02}}, "message": "SUCCESS"}
```

실제로 받은 응답에서 `floor`는 `"1"`인데 `map_name`은 3층 맵이었습니다. 로봇은 그때 3층 충전기에 있었으므로 `map_name`과 좌표가 맞고, 어긋난 것은 `floor` 값입니다. 이 값이 무엇을 뜻하는지(층 번호가 아닌 다른 값일 수 있음)는 확인하지 못했으니, 층을 판단할 때는 `floor`가 아니라 `map_name`을 보세요.

출력이 길면 파일로 저장해서 보세요. 저장 파일은 `.gitignore`에 들어 있는 `out*.json` 이름으로 만드세요.

```
python -m app.pudu get-current-map --sn ABCDEFG0123456 > out_current_map.json
```

조회 결과에는 로봇의 시리얼 번호와 MAC 주소, 회사와 매장 이름이 들어 있습니다. 공개 저장소나 채팅에 올릴 때는 지우거나 가짜 값으로 바꾸세요.

다음: [05. FastAPI와 SQLite로 서버 만들기](05-fastapi-server.md)
