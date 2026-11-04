# 03. 푸두 클라우드 접속하기

## 서버 주소

푸두는 지역별로 고정 주소를 둡니다. 개발자 문서의 [Authentication Access](https://open.pudutech.com/en/cloud-api/hbs3v28rguaas8rw13tk1lzs) 항목에 적힌 값입니다.

| 지역 | 주소 |
|---|---|
| 해외(일본, 한국, 싱가포르) | `https://css-open-platform.pudutech.com/pudu-entry` |
| 중국 | `https://open-platform.pudutech.com/pudu-entry` |
| 독일 | `https://csg-open-platform.pudutech.com/pudu-entry` |
| 미국 | `https://csu-open-platform.pudutech.com/pudu-entry` |

한국에서는 첫 줄의 주소를 썼습니다. 끝의 `/pudu-entry`까지 포함해서 넣어야 합니다. API 키를 발급받은 지역과 맞아야 인증이 통과합니다.

주의할 점이 하나 있습니다. `css.pudutech.com/login` 같은 주소는 사람이 브라우저로 로그인하는 관리 콘솔이고, API를 호출하는 주소가 아닙니다. 콘솔에서는 매장, 로봇, 맵, 지점이 어떻게 등록돼 있는지 눈으로 볼 수 있어서 조회 결과를 확인할 때 도움이 됩니다.

## `.env` 파일

`.env`는 이름이 정확히 `.env`(앞에 점, 확장자 없음)인 텍스트 파일입니다. 키와 서버 주소를 적어 두는 설정 파일이고, 코드는 **명령을 실행한 폴더**에서 이 파일을 찾습니다. 그래서 `README.md`가 있는 폴더, 즉 저장소 맨 위 폴더에 있어야 합니다. 이 파일은 `.gitignore`에 들어 있어서 Git에 올라가지 않습니다.

CMD에서 저장소 폴더에 들어간 뒤 양식을 복사해서 엽니다.

```
copy .env.example .env
notepad .env
```

메모장에서 값을 채우고 저장하세요.

```
PLATFORM_URL=https://css-open-platform.pudutech.com/pudu-entry
API_APP_KEY=(발급받은 ApiAppKey 값)
API_APP_SECRET=(발급받은 ApiAppSecret 값)
```

- 푸두 문서는 두 값을 `ApiAppKey`, `ApiAppSecret`이라고 부릅니다. 이 프로젝트의 `.env`에서는 `API_APP_KEY`, `API_APP_SECRET`으로 적어야 합니다. 이름이 다르면 코드가 값을 못 읽습니다.
- `=` 앞뒤에 공백을 넣지 마세요. 따옴표는 없어도 됩니다.
- `notepad .env`로 열어서 저장하면 파일 이름이 `.env.txt`로 바뀔 걱정이 없습니다. 메모장이 UTF-8(BOM 포함)으로 저장해도 읽도록 만들었습니다.

## 헬스 체크

푸두 문서가 첫 호출로 권하는 것이 헬스 체크입니다. 로봇을 움직이지 않는 호출이고, 주소와 키와 서명이 모두 맞는지 확인해 줍니다.

```
python -m app.pudu health-check
```

성공하면 `message`에 `Success`가 들어간 JSON이 나옵니다. 필드 구성은 서버 응답에 따라 조금 다를 수 있습니다.

```
{
  "message": "GetHealthCheck Success！request={}",
  "data": null
}
```

## 오류가 났을 때

| 증상 | 원인과 해결 |
|---|---|
| `PuduConfigError`, "설정이 없습니다" | `.env`를 못 읽은 겁니다. 명령을 실행한 폴더에 `.env`가 있는지, 이름이 `.env.txt`가 아닌지, 세 줄의 이름 철자가 맞는지 확인하세요. 이름만 출력해서 확인하는 방법은 아래에 있습니다. |
| `PuduAPIError`, `HTTP 401` | 인증 실패입니다. 키와 시크릿 값, 서버 주소의 지역이 맞는지 확인하세요. 문서에 따르면 서명이 틀렸을 때 서버가 응답 헤더로 서버 쪽 서명 문자열(StringToSign)을 돌려주고, 이 도구는 오류 출력의 `response_headers`에 응답 헤더를 같이 보여 줍니다. 내 쪽 서명 문자열과 비교할 때 쓰세요. |
| `PuduError`, "서버에 연결하지 못했습니다" | 인터넷 연결이나 회사 방화벽, 프록시 문제입니다. 주소 철자도 확인하세요. |

`.env`에 어떤 이름이 들어 있는지 값은 숨기고 이름만 보려면 이렇게 합니다.

```
for /f "delims==" %a in (.env) do @echo %a
```

`PLATFORM_URL`, `API_APP_KEY`, `API_APP_SECRET` 세 줄이 나오면 정상입니다. 첫 줄 앞에 이상한 글자가 붙어 있으면 메모장이 파일 맨 앞에 보이지 않는 표시(BOM)를 넣은 겁니다. 이 저장소의 코드는 그 경우도 읽지만, 다른 도구와 함께 쓸 때를 위해 알아 두세요.

## 서명이 하는 일

푸두는 키를 요청에 그대로 싣지 않고 서명을 붙이게 합니다. 요청의 핵심 내용을 다음 순서로 이어 붙인 문자열을 만들고, 줄바꿈으로 구분합니다.

1. `x-date: ` 뒤에 요청 시각(GMT)
2. HTTP 메서드(`GET`)
3. `Accept` 값
4. `Content-Type` 값
5. `Content-MD5` 값(본문이 없는 GET은 빈 줄)
6. 경로와 쿼리. 쿼리는 키를 사전순으로 정렬하고, 값이 비면 키만 적습니다.

이 문자열을 `ApiAppSecret`으로 HMAC-SHA1 계산하고 Base64로 인코딩한 값을 `Authorization` 헤더에 넣습니다. 시크릿은 서버로 가지 않고, 서버가 같은 계산을 해서 서명이 일치하는지만 봅니다. 코드는 `app/pudu.py`의 `sign_path`와 `make_headers`입니다.

다음: [04. 조회로 현장 파악하기](04-read-site-info.md)
