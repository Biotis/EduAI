# EduAI — 대학 강의 자료 분석 및 RAG 기반 학습 지원 서비스

강의 자료(PDF·PPT)를 올리면 **요약**, **용어집**, **예상문제**를 생성하고, 자료 내용을 근거로 답하는 **RAG 챗봇**을 제공하는 서비스입니다.

---

## 주요 기능

- **문서 파싱**: Google Document AI로 텍스트와 표를 추출합니다. PPT/PPTX는 LibreOffice headless 변환을 거쳐 처리하며, 텍스트가 200자 미만인 페이지는 스캔 문서로 판별해 별도 표시합니다.
- **학습 자료 생성**: 추출한 텍스트와 원본 파일을 함께 Gemini 2.5 Flash에 전달하는 하이브리드 파이프라인으로 요약·용어집·예상문제를 생성합니다. 각 단계는 정식 프롬프트 → 단순 프롬프트 → 규칙 기반 폴백의 3단 구조라서, 생성이 실패해도 응답이 비지 않습니다.
- **RAG 챗봇**: LlamaIndex와 LanceDB로 페이지 단위 인덱스를 만들고, `ContextChatEngine`으로 대화 히스토리를 유지합니다. 답변과 함께 근거 페이지 번호와 유사도 점수를 반환합니다.
- **개인화**: 학습자 수준(`novice`/`intermediate`)과 학습 목적(`understanding`/`exam`)에 따라 생성 결과가 달라집니다.

---

## 아키텍처

```
React (Firebase Hosting)
        │  POST /upload, POST /chat
        ▼
FastAPI (Cloud Run, Docker)
        ├── services/document_ai.py    Document AI 파싱, PPT→PDF 변환
        ├── services/vertex_gemini.py  요약·용어집·예상문제 생성 (Gemini 2.5 Flash)
        └── services/rag_llamaindex.py LlamaIndex + LanceDB 인덱싱 및 대화형 검색
                    │
                    ▼
        GCS (원본 보관) · Vertex AI (LLM/임베딩)
```

### 기술 스택

| 구분 | 사용 기술 |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | React 19 (Create React App), Tailwind CSS |
| 문서 처리 | Google Document AI, pypdf, LibreOffice |
| 생성 모델 | Vertex AI Gemini 2.5 Flash |
| 임베딩 | Vertex AI `text-embedding-005` |
| 벡터 스토어 | LanceDB (LlamaIndex `LanceDBVectorStore`) |
| 스토리지 | Google Cloud Storage |
| 배포 | Docker, Cloud Run, Firebase Hosting |

---

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/` | 헬스 체크 |
| `POST` | `/upload` | 강의 자료 업로드 후 요약·용어집·예상문제 생성. `file`, `audience`, `purpose` 를 multipart 로 전송 |
| `POST` | `/chat` | 업로드 시 받은 `docId` 를 대상으로 RAG 질의 응답 |

---

## 로컬 실행

### 사전 준비

- Python 3.11, Node.js 18 이상
- GCP 프로젝트와 Document AI 프로세서
- `gcloud auth application-default login` 으로 로컬 인증 설정
- PPT 업로드를 쓰려면 LibreOffice 설치

### 백엔드

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # 값을 채워 넣습니다
uvicorn main:app --reload --port 8000
```

### 프론트엔드

```bash
cd frontend
npm install
cp .env.example .env        # REACT_APP_API_BASE 를 백엔드 주소로 설정
npm start
```

---

## 배포

### 백엔드 — Cloud Run

```bash
cd backend
gcloud builds submit --tag asia-northeast3-docker.pkg.dev/$PROJECT_ID/eduai/backend:latest .
```

```bash
gcloud run deploy eduai-backend --image=asia-northeast3-docker.pkg.dev/$PROJECT_ID/eduai/backend:latest --region=asia-northeast3 --memory=4Gi --cpu=2 --timeout=600 --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,DOC_AI_LOCATION=us,DOC_AI_PROCESSOR_ID=$DOC_AI_PROCESSOR_ID,DOC_AI_GCS_BUCKET=$DOC_AI_GCS_BUCKET,DOC_AI_GCS_PREFIX=docai,LIBREOFFICE_PATH=/usr/bin/soffice,ALLOWED_ORIGINS=https://$FIREBASE_PROJECT.web.app" --allow-unauthenticated
```

Cloud Run 서비스 계정에는 Document AI 사용자, Storage 객체 관리자, Vertex AI 사용자 역할이 필요합니다.

> **자격 증명을 저장소에 커밋하지 마십시오.** 서비스 계정 키 파일 대신 Cloud Run 의 런타임 서비스 계정을 사용하고, 로컬에서는 `gcloud auth application-default login` 을 쓰면 키 파일 자체가 필요 없습니다.

### 프론트엔드 — Firebase Hosting

```bash
cd frontend
echo "REACT_APP_API_BASE=https://<cloud-run-service-url>" > .env.production
npm run build
firebase deploy --only hosting
```

`.firebaserc` 의 `your-firebase-project-id` 를 실제 프로젝트 ID로 바꾸어야 합니다.

---

## 알려진 제약

- **LanceDB 인덱스가 컨테이너 로컬 디스크(`./lancedb`)에 저장됩니다.** Cloud Run 인스턴스는 상태를 유지하지 않으므로, 인스턴스가 교체되거나 여러 개로 확장되면 이전에 업로드한 문서의 인덱스를 찾지 못합니다. 다중 인스턴스 환경에서 운영하려면 인덱스를 GCS 등 외부 스토리지로 옮기거나 최소 인스턴스를 1로 고정해야 합니다.
- 채팅 엔진(`_CHAT_ENGINES`)이 프로세스 메모리에 캐시되므로 대화 히스토리도 인스턴스 재시작 시 사라집니다.
- LibreOffice 를 포함하면서 이미지 용량이 커져 콜드 스타트가 느립니다. PPT 지원이 필요 없다면 `Dockerfile` 의 해당 설치 단계를 제거할 수 있습니다.

---

## 프로젝트 구조

```
backend/
├── Dockerfile
├── requirements.txt
├── .env.example
├── main.py                    FastAPI 엔트리포인트
└── services/
    ├── document_ai.py         Document AI 파싱
    ├── vertex_gemini.py       요약·용어집·예상문제 생성
    └── rag_llamaindex.py      LlamaIndex + LanceDB RAG
frontend/
├── firebase.json
├── .firebaserc
├── .env.example
└── src/                       React 애플리케이션
발표 자료/                       최종 발표 자료
```
