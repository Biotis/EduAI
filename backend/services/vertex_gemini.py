# # -*- coding: utf-8 -*-
# import os
# import re
# import json
# from typing import Any, Dict, List, Optional

# import vertexai
# from vertexai.generative_models import GenerativeModel, GenerationConfig, Part


# PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
# VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")

# # 모델 선택 우선순위 (환경변수 우선)
# PREFERRED_MODELS = [
#     os.getenv("VERTEX_MODEL", "gemini-2.5-pro"),
#     "gemini-2.5-flash",
# ]

# _vertex_inited = False
# _model: Optional[GenerativeModel] = None


# def _init_model() -> None:
#     global _vertex_inited, _model
#     if _vertex_inited:
#         return
#     if not PROJECT_ID:
#         raise RuntimeError("VERTEX 설정 누락: GOOGLE_CLOUD_PROJECT 확인")
#     vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)

#     last_err: Optional[Exception] = None
#     for name in PREFERRED_MODELS:
#         try:
#             _model = GenerativeModel(name)
#             _vertex_inited = True
#             return
#         except Exception as e:
#             last_err = e
#     if last_err:
#         raise last_err


# def _chunk_text(text: str, chunk_size: int = 15000) -> List[str]:
#     return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


# def _resp_to_text(resp) -> str:
#     """Vertex SDK 응답에서 텍스트를 안정적으로 추출."""
#     try:
#         cands = getattr(resp, "candidates", None)
#         if cands:
#             parts = getattr(cands[0].content, "parts", None)
#             if parts:
#                 for p in parts:
#                     t = getattr(p, "text", None)
#                     if t:
#                         return str(t).strip()
#         t = getattr(resp, "text", "")
#         return (t or "").strip()
#     except Exception:
#         t = getattr(resp, "text", "")
#         return (t or "").strip()


# def _extract_first_json_block(s: str) -> Optional[str]:
#     in_str, esc, start = False, False, -1
#     stack: List[str] = []
#     for i, ch in enumerate(s):
#         if in_str:
#             if esc:
#                 esc = False
#             elif ch == "\\":
#                 esc = True
#             elif ch == '"':
#                 in_str = False
#             continue
#         else:
#             if ch == '"':
#                 in_str = True
#                 continue
#             if ch in "{[":
#                 if not stack:
#                     start = i
#                 stack.append(ch)
#             elif ch in "}]":
#                 if stack:
#                     stack.pop()
#                     if not stack and start != -1:
#                         end = i + 1
#                         return s[start:end]
#     return None


# def _safe_json(s: str):
#     s = (s or "").strip()
#     s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I).strip()
#     s = re.sub(r"\s*```$", "", s).strip()

#     block = _extract_first_json_block(s)
#     if block:
#         try:
#             return json.loads(block)
#         except Exception:
#             block2 = re.sub(r",\s*([}\]])", r"\1", block)
#             try:
#                 return json.loads(block2)
#             except Exception:
#                 pass

#     objs: List[Any] = []
#     buf = ""
#     for line in s.splitlines():
#         buf += line.strip()
#         blk = _extract_first_json_block(buf)
#         if blk:
#             try:
#                 objs.append(json.loads(blk))
#                 buf = ""
#             except Exception:
#                 pass
#     if objs:
#         return objs
#     return {}


# def _gen_text(prompt: str, max_tokens: int = 2048, parts: Optional[List[Any]] = None) -> str:
#     _init_model()
#     cfg = GenerationConfig(temperature=0.2, top_p=0.9, max_output_tokens=max_tokens)
#     content = [prompt] + (parts or [])
#     resp = _model.generate_content(content, generation_config=cfg)
#     return _resp_to_text(resp)


# def _gen_json(prompt: str, max_tokens: int = 4096, parts: Optional[List[Any]] = None):
#     _init_model()
#     strict = f"""
# 다음 기준을 반드시 따르세요.
# 1) JSON만 출력. 마크다운/설명/코드블록 금지.
# 2) 지정한 키와 구조를 지키고, 유효한 JSON을 반환.

# [지시]
# {prompt}
# """.strip()

#     cfg = GenerationConfig(
#         temperature=0.15,
#         top_p=0.9,
#         max_output_tokens=max_tokens,
#         response_mime_type="application/json",
#     )

#     def _try(parts_):
#         content = [strict] + (parts_ or [])
#         resp = _model.generate_content(content, generation_config=cfg)
#         raw = _resp_to_text(resp)
#         return _safe_json(raw), raw

#     try:
#         data, _ = _try(parts)
#         return data
#     except Exception:
#         pass
#     try:
#         data, _ = _try(None)
#         return data
#     except Exception:
#         return {}


# # ---------- 규칙 폴백 ----------
# def _fallback_summary_from_text(full_text: str) -> Dict[str, Any]:
#     paras = [p.strip() for p in re.split(r"\n\s*\n", full_text or "") if p.strip()]
#     high = (paras[0] if paras else (full_text or "")[:600])
#     secs: List[Dict[str, Any]] = []
#     for i, p in enumerate(paras[1:4], 1):
#         bullets = [s.strip() for s in re.split(r"[•\-\u2022]|(?<=[.!?])\s+", p) if s.strip()][:4]
#         secs.append({"title": f"Section {i}", "bullets": bullets})
#     return {"high_level": (high or "요약 없음")[:1200], "sections": secs}


# def _fallback_glossary_from_summary(full_text: str, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
#     s_text = (summary.get("high_level", "") + " " + " ".join(
#         b for sec in summary.get("sections", []) for b in sec.get("bullets", [])
#     )).lower()
#     if len(s_text) < 50:
#         s_text = (full_text or "")[:4000].lower()
#     tokens = re.findall(r"[a-zA-Z가-힣]{2,}", s_text)
#     stop = set(["그리고","그러나","또는","이다","있는","하는","에서","으로","the","and","for","with","that","this"])
#     cand = [t for t in tokens if t not in stop]
#     uniq: List[str] = []
#     for t in cand:
#         if t not in uniq:
#             uniq.append(t)
#         if len(uniq) >= 12:
#             break
#     out: List[Dict[str, Any]] = []
#     sentences = re.split(r"(?<=[.!?])\s+", full_text or "")
#     for i, term in enumerate(uniq[:12]):
#         sent = next((s for s in sentences if term in s), "")
#         out.append({
#             "term": term,
#             "definition": (sent[:160] or "강의 맥락의 핵심 용어입니다."),
#             "importance": "매우 중요" if i < 4 else "중요",
#         })
#     if not out:
#         out = [{"term": "핵심", "definition": "강의 핵심 개념.", "importance": "중요"}]
#     return out


# def _fallback_questions_from_summary(summary: Dict[str, Any], glossary: List[Dict[str, Any]], purpose: str) -> List[Dict[str, Any]]:
#     items: List[Dict[str, Any]] = []
#     pool = [g.get("term") for g in glossary if g.get("term")] or [
#         sec.get("title", "핵심 개념") for sec in summary.get("sections", [])
#     ]
#     if not pool:
#         pool = ["핵심 개념"]
#     while len(items) < 10:
#         term = pool[len(items) % len(pool)]
#         items.append({
#             "type": "short",
#             "stem": f"다음 용어를 설명하시오: {term}",
#             "answer": next((g.get("definition") for g in glossary if g.get("term") == term), "핵심 정의를 서술하시오."),
#             "rationale": "강의 요약과 용어 정리에 근거함.",
#             "difficulty": ("easy" if purpose != "exam" and len(items) < 4 else ("medium" if len(items) < 9 else "hard")),
#         })
#     return items


# # ---------- 생성 단계 ----------
# def _generate_summary_hybrid(full_text: str, audience: str, purpose: str, parts: Optional[List[Any]]):
#     chunks = _chunk_text(full_text or "", 15000)
#     bullets_all: List[str] = []
#     for i, ch in enumerate(chunks or [full_text or ""], 1):
#         p = f"""
# 당신은 강의자료 조교입니다. 다음 텍스트에서 핵심 개념/정의/결론/주의 6개 내외 불릿으로 요약하세요.
# audience={audience}, purpose={purpose}. 과도한 축약 금지, 중복 제거.

# [청크 {i}/{len(chunks) or 1}]
# {ch}
# """
#         bullets_all.append(_gen_text(p, max_tokens=8192))

#     joined = "\n".join(f"- {b}" for b in bullets_all if b)
#     prompt = f"""
# 역할: 강의 조교(최종 정리). 출처: Doc AI 추출 텍스트 + 원본 파일(PDF/PPT).
# 요구: 고수준 요약과 섹션별 불릿을 JSON으로만 반환.
# 스키마: {{"high_level":"...","sections":[{{"title":"...","bullets":["...","..."]}}]}}

# [증거 불릿]
# {joined}
# """
#     data = _gen_json(prompt, max_tokens=8192, parts=parts)
#     if isinstance(data, dict) and "high_level" in data and "sections" in data:
#         return data

#     # 2차 간소화 프롬프트
#     prompt_simple = f"""
# 아래 강의 텍스트를 간단히 요약하여 JSON 한 객체만 출력하세요.
# 스키마: {{"high_level":"...","sections":[{{"title":"...","bullets":["...","..."]}}]}}
# JSON만 출력.

# [텍스트]
# {(full_text or '')[:12000]}
# """
#     data2 = _gen_json(prompt_simple, max_tokens=8192, parts=None)
#     if isinstance(data2, dict) and "high_level" in data2 and "sections" in data2:
#         return data2

#     return _fallback_summary_from_text(full_text or "")


# def _generate_glossary_hybrid(full_text: str, summary: Dict[str, Any], audience: str, purpose: str, parts: Optional[List[Any]]):
#     s_high = summary.get("high_level", "")
#     s_secs = summary.get("sections", [])
#     s_text = s_high + "\n" + "\n".join(
#         f"[{sec.get('title','')}]\n" + "\n".join(sec.get("bullets", [])) for sec in s_secs
#     )
#     prompt = f"""
# 역할: 강의 조교(용어 정리). 요약+원본 파일을 근거로 핵심 용어 10~15개 JSON 배열만 출력.
# 요소 키: term, definition, importance.

# [요약]
# {s_text}

# [본문(발췌)]
# {(full_text or '')[:12000]}
# """
#     data = _gen_json(prompt, max_tokens=8192, parts=parts)
#     if isinstance(data, list) and data:
#         return data

#     prompt_simple = f"""
# 다음 요약에서 핵심 용어 10~15개를 JSON 배열로만 출력하세요.
# 각 원소는 {{"term":"...","definition":"...","importance":"..."}} 키를 모두 포함.

# [요약]
# {s_text}
# """
#     data2 = _gen_json(prompt_simple, max_tokens=8192, parts=None)
#     if isinstance(data2, list) and data2:
#         return data2

#     return _fallback_glossary_from_summary(full_text or "", summary)


# def _generate_questions_hybrid(full_text: str, summary: Dict[str, Any], audience: str, purpose: str, parts: Optional[List[Any]]):
#     s_high = summary.get("high_level", "")
#     s_secs = summary.get("sections", [])
#     s_text = s_high + "\n" + "\n".join(
#         f"[{sec.get('title','')}]\n" + "\n".join(sec.get("bullets", [])) for sec in s_secs
#     )
#     prompt = f"""
# 역할: 강의 조교(문항 출제). 요약+원본 파일을 근거로 총 10문항을 JSON 배열로만 출력.
# - mcq 6개, short 4개
# - mcq: {{"type":"mcq","stem":"...","choices":["A","B","C","D"],"answer":"...","rationale":"...","difficulty":"easy|medium|hard"}}
# - short: {{"type":"short","stem":"...","answer":"...","rationale":"...","difficulty":"easy|medium|hard"}}
# JSON 외 출력 금지.

# [요약]
# {s_text}

# [본문(발췌)]
# {(full_text or '')[:14000]}
# """
#     data = _gen_json(prompt, max_tokens=8192, parts=parts)
#     if isinstance(data, list) and data:
#         return data

#     prompt_simple = f"""
# 다음 요약을 기반으로 총 10문항(JSON 배열)만 출력하세요. mcq 6개, short 4개.
# 스키마는 위와 동일. JSON만 출력.

# [요약]
# {s_text}
# """
#     data2 = _gen_json(prompt_simple, max_tokens=3200, parts=None)
#     if isinstance(data2, list) and data2:
#         return data2

#     # 최종 규칙 폴백(항상 10문항 보장)
#     glossary = _fallback_glossary_from_summary(full_text or "", summary)
#     return _fallback_questions_from_summary(summary, glossary, purpose)


# def run_pipeline_hybrid(full_text: str, audience: str, purpose: str, file_uri: Optional[str], mime_type: Optional[str]):
#     parts: List[Any] = []
#     if file_uri and mime_type:
#         try:
#             parts = [Part.from_uri(uri=file_uri, mime_type=mime_type)]
#         except Exception:
#             parts = []

#     summary = _generate_summary_hybrid(full_text, audience, purpose, parts)
#     glossary = _generate_glossary_hybrid(full_text, summary, audience, purpose, parts)
#     questions = _generate_questions_hybrid(full_text, summary, audience, purpose, parts)

#     return {"summary": summary, "glossary": glossary, "questions": questions}

# # ---------- [NEW] 챗봇 기능 추가 ----------
# def generate_chat_response(text_content: str, user_question: str) -> str:
#     """
#     추출된 텍스트 내용을 바탕으로 사용자의 질문에 답변합니다.
#     """
#     _init_model()
    
#     # 프롬프트 구성
#     prompt = f"""
#     당신은 친절하고 똑똑한 '강의 보조 AI 조교'입니다.
#     아래 제공된 [강의 자료 내용]을 바탕으로 학생의 [질문]에 명확하고 이해하기 쉽게 답변해 주세요.
#     만약 내용에 없는 질문이라면 "문서 내용에 없는 부분이라 답변하기 어렵습니다."라고 정중히 말해주세요.

#     [강의 자료 내용]
#     {text_content[:25000]} 

#     [질문]
#     {user_question}
#     """
    
#     # 답변 생성 설정 (정확도 우선)
#     cfg = GenerationConfig(
#         max_output_tokens=8192,
#         temperature=0.2,
#         top_p=0.8,
#     )

#     try:
#         content = [prompt]
#         resp = _model.generate_content(content, generation_config=cfg)
#         return _resp_to_text(resp)
#     except Exception as e:
#         print(f"Gemini Chat Error: {e}")
#         return "죄송합니다. 답변을 생성하는 도중 오류가 발생했습니다."

# -*- coding: utf-8 -*-
import os
import re
import json
from typing import Any, Dict, List, Optional

import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig, Part


PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")

PREFERRED_MODELS = [
    os.getenv("VERTEX_MODEL", "gemini-2.5-pro"),
    "gemini-2.5-flash",
]

_vertex_inited = False
_model: Optional[GenerativeModel] = None


def _init_model() -> None:
    global _vertex_inited, _model
    if _vertex_inited:
        return
    if not PROJECT_ID:
        raise RuntimeError("VERTEX 설정 누락: GOOGLE_CLOUD_PROJECT 확인")
    vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)

    last_err: Optional[Exception] = None
    for name in PREFERRED_MODELS:
        try:
            _model = GenerativeModel(name)
            _vertex_inited = True
            print(f"✅ Selected Vertex AI Model: {name}") # 어떤 모델이 선택됐는지 로그 출력
            return
        except Exception as e:
            last_err = e
    if last_err:
        raise last_err


def _chunk_text(text: str, chunk_size: int = 15000) -> List[str]:
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


def _resp_to_text(resp) -> str:
    """Vertex SDK 응답에서 텍스트를 안정적으로 추출."""
    try:
        cands = getattr(resp, "candidates", None)
        if cands:
            parts = getattr(cands[0].content, "parts", None)
            if parts:
                for p in parts:
                    t = getattr(p, "text", None)
                    if t:
                        return str(t).strip()
        t = getattr(resp, "text", "")
        return (t or "").strip()
    except Exception:
        t = getattr(resp, "text", "")
        return (t or "").strip()


def _extract_first_json_block(s: str) -> Optional[str]:
    in_str, esc, start = False, False, -1
    stack: List[str] = []
    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        else:
            if ch == '"':
                in_str = True
                continue
            if ch in "{[":
                if not stack:
                    start = i
                stack.append(ch)
            elif ch in "}]":
                if stack:
                    stack.pop()
                    if not stack and start != -1:
                        end = i + 1
                        return s[start:end]
    return None

def _safe_json(s: str):
    s = (s or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.I).strip()
    s = re.sub(r"\s*```$", "", s).strip()

    block = _extract_first_json_block(s)
    if block:
        try:
            return json.loads(block)
        except Exception:
            block2 = re.sub(r",\s*([}\]])", r"\1", block)
            try:
                return json.loads(block2)
            except Exception:
                pass

    objs: List[Any] = []
    buf = ""
    for line in s.splitlines():
        buf += line.strip()
        blk = _extract_first_json_block(buf)
        if blk:
            try:
                objs.append(json.loads(blk))
                buf = ""
            except Exception:
                pass
    if objs:
        return objs
    return {}


def _gen_text(prompt: str, max_tokens: int = 8192, parts: Optional[List[Any]] = None) -> str:
    _init_model()
    # [수정됨] 기본 토큰 수 증가 (2048 -> 8192)
    cfg = GenerationConfig(temperature=0.2, top_p=0.9, max_output_tokens=max_tokens)
    content = [prompt] + (parts or [])
    resp = _model.generate_content(content, generation_config=cfg)
    return _resp_to_text(resp)


def _gen_json(prompt: str, max_tokens: int = 8192, parts: Optional[List[Any]] = None):
    _init_model()
    strict = f"""
다음 기준을 반드시 따르세요.
1) JSON만 출력. 마크다운/설명/코드블록 금지.
2) 지정한 키와 구조를 지키고, 유효한 JSON을 반환.

[지시]
{prompt}
""".strip()

    # [수정됨] 기본 토큰 수 증가 (4096 -> 8192)
    cfg = GenerationConfig(
        temperature=0.15,
        top_p=0.9,
        max_output_tokens=max_tokens,
        response_mime_type="application/json",
    )

    def _try(parts_):
        content = [strict] + (parts_ or [])
        resp = _model.generate_content(content, generation_config=cfg)
        raw = _resp_to_text(resp)
        return _safe_json(raw), raw

    try:
        data, _ = _try(parts)
        return data
    except Exception:
        pass
    try:
        data, _ = _try(None)
        return data
    except Exception:
        return {}


# ---------- 규칙 폴백 ----------
def _fallback_summary_from_text(full_text: str) -> Dict[str, Any]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", full_text or "") if p.strip()]
    high = (paras[0] if paras else (full_text or "")[:600])
    secs: List[Dict[str, Any]] = []
    for i, p in enumerate(paras[1:4], 1):
        bullets = [s.strip() for s in re.split(r"[•\-\u2022]|(?<=[.!?])\s+", p) if s.strip()][:4]
        secs.append({"title": f"Section {i}", "bullets": bullets})
    return {"high_level": (high or "요약 없음")[:1200], "sections": secs}


def _fallback_glossary_from_summary(full_text: str, summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    s_text = (summary.get("high_level", "") + " " + " ".join(
        b for sec in summary.get("sections", []) for b in sec.get("bullets", [])
    )).lower()
    if len(s_text) < 50:
        s_text = (full_text or "")[:4000].lower()
    tokens = re.findall(r"[a-zA-Z가-힣]{2,}", s_text)
    stop = set(["그리고","그러나","또는","이다","있는","하는","에서","으로","the","and","for","with","that","this"])
    cand = [t for t in tokens if t not in stop]
    uniq: List[str] = []
    for t in cand:
        if t not in uniq:
            uniq.append(t)
        if len(uniq) >= 12:
            break
    out: List[Dict[str, Any]] = []
    sentences = re.split(r"(?<=[.!?])\s+", full_text or "")
    for i, term in enumerate(uniq[:12]):
        sent = next((s for s in sentences if term in s), "")
        out.append({
            "term": term,
            "definition": (sent[:160] or "강의 맥락의 핵심 용어입니다."),
            "importance": "매우 중요" if i < 4 else "중요",
        })
    if not out:
        out = [{"term": "핵심", "definition": "강의 핵심 개념.", "importance": "중요"}]
    return out


def _fallback_questions_from_summary(summary: Dict[str, Any], glossary: List[Dict[str, Any]], purpose: str) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    pool = [g.get("term") for g in glossary if g.get("term")] or [
        sec.get("title", "핵심 개념") for sec in summary.get("sections", [])
    ]
    if not pool:
        pool = ["핵심 개념"]
    while len(items) < 10:
        term = pool[len(items) % len(pool)]
        items.append({
            "type": "short",
            "stem": f"다음 용어를 설명하시오: {term}",
            "answer": next((g.get("definition") for g in glossary if g.get("term") == term), "핵심 정의를 서술하시오."),
            "rationale": "강의 요약과 용어 정리에 근거함.",
            "difficulty": ("easy" if purpose != "exam" and len(items) < 4 else ("medium" if len(items) < 9 else "hard")),
        })
    return items


# ---------- 생성 단계 ----------
def _generate_summary_hybrid(full_text: str, audience: str, purpose: str, parts: Optional[List[Any]]):
    chunks = _chunk_text(full_text or "", 15000)
    bullets_all: List[str] = []
    for i, ch in enumerate(chunks or [full_text or ""], 1):
        p = f"""
당신은 강의자료 조교입니다. 다음 텍스트에서 핵심 개념/정의/결론/주의 6개 내외 불릿으로 요약하세요.
audience={audience}, purpose={purpose}. 과도한 축약 금지, 중복 제거.

[청크 {i}/{len(chunks) or 1}]
{ch}
"""
        # [수정됨] 요약 생성 시에도 긴 텍스트 허용
        bullets_all.append(_gen_text(p, max_tokens=8192))

    joined = "\n".join(f"- {b}" for b in bullets_all if b)
    prompt = f"""
역할: 강의 조교(최종 정리). 출처: Doc AI 추출 텍스트 + 원본 파일(PDF/PPT).
요구: 고수준 요약과 섹션별 불릿을 JSON으로만 반환.
스키마: {{"high_level":"...","sections":[{{"title":"...","bullets":["...","..."]}}]}}

[증거 불릿]
{joined}
"""
    data = _gen_json(prompt, max_tokens=8192, parts=parts)
    if isinstance(data, dict) and "high_level" in data and "sections" in data:
        return data

    # 2차 간소화 프롬프트
    prompt_simple = f"""
아래 강의 텍스트를 간단히 요약하여 JSON 한 객체만 출력하세요.
스키마: {{"high_level":"...","sections":[{{"title":"...","bullets":["...","..."]}}]}}
JSON만 출력.

[텍스트]
{(full_text or '')[:12000]}
"""
    data2 = _gen_json(prompt_simple, max_tokens=8192, parts=None)
    if isinstance(data2, dict) and "high_level" in data2 and "sections" in data2:
        return data2

    return _fallback_summary_from_text(full_text or "")


def _generate_glossary_hybrid(full_text: str, summary: Dict[str, Any], audience: str, purpose: str, parts: Optional[List[Any]]):
    s_high = summary.get("high_level", "")
    s_secs = summary.get("sections", [])
    s_text = s_high + "\n" + "\n".join(
        f"[{sec.get('title','')}]\n" + "\n".join(sec.get("bullets", [])) for sec in s_secs
    )
    prompt = f"""
역할: 강의 조교(용어 정리). 요약+원본 파일을 근거로 핵심 용어 10~15개 JSON 배열만 출력.
요소 키: term, definition, importance.

[요약]
{s_text}

[본문(발췌)]
{(full_text or '')[:12000]}
"""
    data = _gen_json(prompt, max_tokens=8192, parts=parts)
    if isinstance(data, list) and data:
        return data

    prompt_simple = f"""
다음 요약에서 핵심 용어 10~15개를 JSON 배열로만 출력하세요.
각 원소는 {{"term":"...","definition":"...","importance":"..."}} 키를 모두 포함.

[요약]
{s_text}
"""
    data2 = _gen_json(prompt_simple, max_tokens=8192, parts=None)
    if isinstance(data2, list) and data2:
        return data2

    return _fallback_glossary_from_summary(full_text or "", summary)


def _generate_questions_hybrid(full_text: str, summary: Dict[str, Any], audience: str, purpose: str, parts: Optional[List[Any]]):
    s_high = summary.get("high_level", "")
    s_secs = summary.get("sections", [])
    s_text = s_high + "\n" + "\n".join(
        f"[{sec.get('title','')}]\n" + "\n".join(sec.get("bullets", [])) for sec in s_secs
    )
    prompt = f"""
역할: 강의 조교(문항 출제). 요약+원본 파일을 근거로 총 10문항을 JSON 배열로만 출력.
- mcq 6개, short 4개
- mcq: {{"type":"mcq","stem":"...","choices":["A","B","C","D"],"answer":"...","rationale":"...","difficulty":"easy|medium|hard"}}
- short: {{"type":"short","stem":"...","answer":"...","rationale":"...","difficulty":"easy|medium|hard"}}
JSON 외 출력 금지.

[요약]
{s_text}

[본문(발췌)]
{(full_text or '')[:14000]}
"""
    data = _gen_json(prompt, max_tokens=8192, parts=parts)
    if isinstance(data, list) and data:
        return data

    prompt_simple = f"""
다음 요약을 기반으로 총 10문항(JSON 배열)만 출력하세요. mcq 6개, short 4개.
스키마는 위와 동일. JSON만 출력.

[요약]
{s_text}
"""
    data2 = _gen_json(prompt_simple, max_tokens=3200, parts=None)
    if isinstance(data2, list) and data2:
        return data2

    # 최종 규칙 폴백(항상 10문항 보장)
    glossary = _fallback_glossary_from_summary(full_text or "", summary)
    return _fallback_questions_from_summary(summary, glossary, purpose)


def run_pipeline_hybrid(full_text: str, audience: str, purpose: str, file_uri: Optional[str], mime_type: Optional[str]):
    parts: List[Any] = []
    if file_uri and mime_type:
        try:
            parts = [Part.from_uri(uri=file_uri, mime_type=mime_type)]
        except Exception:
            parts = []

    summary = _generate_summary_hybrid(full_text, audience, purpose, parts)
    glossary = _generate_glossary_hybrid(full_text, summary, audience, purpose, parts)
    questions = _generate_questions_hybrid(full_text, summary, audience, purpose, parts)

    return {"summary": summary, "glossary": glossary, "questions": questions}