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

`sn`이 로봇의 시리얼 번호이고, 로봇을 가리키는 모든 호출에 쓰입니다. `first_active_time`은 Unix 시각(초)입니다. 이 코드는 한 번에 최대 20대까지 조회하도록 되어 있고, 이 값이 서버에서 허용되는지는 확인하지 못했습니다. 오류가 나면 `app/pudu.py`의 `get_robot_list`에서 `limit` 값을 줄여 보세요.

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

## 아직 실행해 보지 않은 호출

아래 네 개도 같은 방식으로 만들어 두었지만, 엔드포인트 경로를 다른 구현에서 가져왔고 직접 실행한 결과는 아직 없습니다. 위 세 개와 헬스 체크만 실제 서버에서 성공을 확인했습니다.

| 명령 | 하는 일 |
|---|---|
| `store-map-list --shop-id ...` | 매장에 등록된 맵 목록. 층별 맵이 있는지 볼 수 있을 것으로 보입니다 |
| `get-current-map --sn ...` | 로봇의 현재 맵과 맵 요소(elements) |
| `get-robot-groups --shop-id ...` | 로봇 그룹 목록 |
| `get-position --sn ...` | 로봇의 현재 위치 |

출력이 길면 파일로 저장해서 보세요. 저장 파일은 `.gitignore`에 들어 있는 `out*.json` 이름으로 만드세요.

```
python -m app.pudu get-current-map --sn ABCDEFG0123456 > out_current_map.json
```

조회 결과에는 로봇의 시리얼 번호와 MAC 주소, 회사와 매장 이름이 들어 있습니다. 공개 저장소나 채팅에 올릴 때는 지우거나 가짜 값으로 바꾸세요.

다음: [05. FastAPI와 SQLite로 서버 만들기](05-fastapi-server.md)
