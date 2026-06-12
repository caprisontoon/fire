"""Vercel 서버리스 함수 진입점.

Vercel은 api/ 폴더의 파이썬 파일에서 ASGI 앱(app)을 찾아 실행한다.
실제 라우트(/api/simulate)는 backend/main.py의 FastAPI 앱에 정의되어 있다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 임포트 경로에 추가 (backend 패키지를 찾기 위함)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.main import app  # noqa: E402,F401
