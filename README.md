# T300 따라하기

푸두(PUDU) T300 물류 로봇을 파이썬으로 다루는 과정을, 실제로 해 본 순서대로 적은 한글 가이드입니다. 최종 목표는 회사 건물 안에서 T300이 엘리베이터를 타고 층간 이동을 하며 물건을 나르게 만드는 것입니다. 막혔던 곳과 해결 방법도 그대로 적습니다.

비공식 자료이고 푸두 로보틱스와 관련이 없습니다. 로봇이 움직이거나 엘리베이터를 쓰는 작업은 현장 담당자와 건물 관리 주체의 승인을 받은 뒤에 하세요. 이 저장소는 그 전 단계인 조회까지만 다룹니다.

## 진행 상황

| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | 윈도우에서 파이썬 환경 준비 | 완료 |
| 2 | 푸두 클라우드에 접속(health check) | 완료 (이 저장소의 `app/pudu.py`로 실제 서버 응답 확인) |
| 3 | 조회로 매장, 로봇, 맵 파악 | 일부 완료 (매장, 로봇, 지점 조회는 다른 도구로 확인. 이 저장소 코드로 4개 추가 조회는 아직) |
| 4 | FastAPI + SQLite 서버 | 코드와 테스트 완료, 서버를 띄워 푸두와 붙인 실행은 아직 |
| 5 | 같은 층 안에서 지점 이동 | 예정 |
| 6 | 엘리베이터로 층간 이동 | 계획만 있음 |
| 7 | 물건 운반 | 예정 |

## 빠른 시작

푸두 오픈플랫폼의 API 키가 이미 있다는 전제입니다. 키가 없다면 [01 개요](docs/01-overview.md)를 먼저 보세요. 윈도우 CMD 기준입니다.

```
cd C:\work\t300-guide
pip install -r requirements.txt
copy .env.example .env
notepad .env
python -m app.pudu health-check
```

`C:\work\t300-guide`는 이 저장소를 내려받은 영문 경로입니다. 한글이 들어간 경로나 OneDrive 폴더는 피하세요. 이유는 [02 환경 준비](docs/02-windows-setup.md)에 있습니다. `.env`에 넣을 값은 [03 푸두 접속](docs/03-connect-pudu.md)에 적었습니다.

## 목차

1. [개요: 무엇을 하고, 무엇이 필요한가](docs/01-overview.md)
2. [윈도우 환경 준비](docs/02-windows-setup.md)
3. [푸두 클라우드 접속하기](docs/03-connect-pudu.md)
4. [조회로 현장 파악하기](docs/04-read-site-info.md)
5. [FastAPI와 SQLite로 서버 만들기](docs/05-fastapi-server.md)
6. [엘리베이터 층간 이동 계획](docs/06-elevator-plan.md)

## 진행 방식

계획과 현재 상태를 파일로 따로 적어 두고 작업합니다. 계획은 잘 안 바뀌는 문서이고, 상태 파일은 매번 고칩니다. 지금 어느 단계인지, 무엇이 막혀 있는지, 어떤 결정을 왜 했는지가 한 파일에 남아서 며칠 쉬었다 돌아와도 바로 이어갈 수 있습니다. 양식은 [templates/state-template.md](templates/state-template.md)에 있습니다.

## 폴더 구성

```
app/          파이썬 코드 (pudu.py 클라이언트, main.py 서버, db.py 데이터베이스)
tests/        테스트 (키와 네트워크 없이 돌아갑니다)
docs/         단계별 가이드
templates/    state 파일 양식
```

## 참고 자료

- [PUDU Open Platform](https://open.pudutech.com/en)
- [PUDU Cloud API 개발 가이드: Authentication Access](https://open.pudutech.com/en/cloud-api/hbs3v28rguaas8rw13tk1lzs)
- [PUDU Cloud API 개발 가이드: Quick Start](https://open.pudutech.com/en/cloud-api/nxxd6u61rrrakorlldz54kf9)
