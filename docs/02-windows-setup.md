# 02. 윈도우 환경 준비

윈도우 CMD 기준입니다. PowerShell에서도 명령은 같습니다.

## 1. 파이썬 확인

```
python --version
```

`Python 3.9` 이상이 나오면 됩니다. 이 가이드는 3.11에서 확인했습니다. 명령을 찾을 수 없다고 나오면 [python.org](https://www.python.org/downloads/)에서 설치하세요. 윈도우에서 `python`만 쳐도 Microsoft Store가 열리는 경우가 있는데, 그쪽으로 설치해도 됩니다.

## 2. 작업 폴더는 영문 경로에 둡니다

저장소를 `C:\work\t300-guide`처럼 한글이 없는 경로에 내려받으세요. 폴더 이름과 상위 폴더 모두 영문이어야 합니다. OneDrive 동기화 폴더도 피하세요. 이유는 두 가지입니다.

**한글 경로에서 `pip install -e .`를 하면 파이썬이 시작되지 않습니다.** 실제로 겪은 일입니다. `pip install -e .`(개발 모드 설치)는 프로젝트 경로를 적은 `.pth` 파일을 파이썬 폴더에 만듭니다. 경로에 한글이 있으면 이 파일에 한글이 UTF-8로 적히는데, 파이썬 3.11은 시작할 때 이 파일을 cp949로 읽다가 실패합니다. 그 뒤로는 `python --version`을 포함한 모든 파이썬 실행이 이런 오류로 끝납니다.

```
Fatal Python error: init_import_site: Failed to import the site module
...
UnicodeDecodeError: 'cp949' codec can't decode byte 0xeb in position 32: illegal multibyte sequence
```

이 가이드는 `-e` 설치를 쓰지 않으므로 영문 경로에서는 일어나지 않습니다. 이미 겪었다면 `.pth` 파일 하나를 지워서 복구합니다. Microsoft Store 버전 파이썬 3.11에서 확인한 경로입니다. 먼저 파일을 확인하고, 이름에 `pudu`가 들어간 `.pth`만 지우세요.

```
dir "%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\*.pth"
del "%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\site-packages\*pudu*.pth"
```

다른 방법으로 설치한 파이썬이라면 폴더가 다릅니다. `%APPDATA%\Python\Python311\site-packages` 또는 파이썬 설치 폴더의 `Lib\site-packages`에서 같은 종류의 `.pth` 파일을 찾아보세요. 이 경로들은 직접 확인하지 못했습니다.

**OneDrive 폴더에 두면 `.env`의 키가 클라우드에 올라갑니다.** API 키를 클라우드 동기화 폴더에 두지 않는 편이 좋습니다.

## 3. 저장소 내려받기

Git이 있으면 이렇게 합니다.

```
git clone (이 저장소 주소) C:\work\t300-guide
cd C:\work\t300-guide
```

Git이 없으면 GitHub 저장소 페이지의 Code 버튼에서 Download ZIP을 받아 `C:\work\t300-guide`에 풀면 됩니다. 풀고 나서 `README.md`와 `requirements.txt`가 보이는 폴더로 `cd` 하세요. 폴더 안에 같은 이름의 폴더가 한 겹 더 있는 경우가 있습니다.

## 4. 패키지 설치

```
pip install -r requirements.txt
```

끝에 `A new release of pip is available` 안내가 나오면 무시해도 됩니다. 환경을 깔끔하게 나누고 싶으면 가상환경을 쓰세요.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 5. 테스트로 확인

```
python -m pytest -q
```

`22 passed` 비슷한 결과가 나오면 설치가 끝난 겁니다. 이 테스트는 API 키도 인터넷 연결도 필요 없습니다. 푸두 서버를 가짜로 대신하기 때문입니다.

다음: [03. 푸두 클라우드 접속하기](03-connect-pudu.md)
