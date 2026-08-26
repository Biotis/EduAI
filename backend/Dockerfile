# EduAI backend — FastAPI on Cloud Run
FROM python:3.11-slim

# LibreOffice: services/document_ai.py 가 PPT/PPTX 를 PDF 로 변환할 때 사용합니다.
# PPT 업로드를 지원하지 않을 경우 아래 RUN 블록과 LIBREOFFICE_PATH 를 제거하면
# 이미지 크기가 크게 줄어들어 콜드 스타트가 빨라집니다.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-impress \
        fonts-nanum \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    LIBREOFFICE_PATH=/usr/bin/soffice

WORKDIR /app

# 의존성을 먼저 복사해 레이어 캐시를 활용합니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run 은 PORT 환경 변수로 수신 포트를 주입합니다. 로컬 실행 시 기본값은 8080 입니다.
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
