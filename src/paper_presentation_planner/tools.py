"""Utility functions used by the agents."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "have", "has",
    "using", "used", "into", "between", "through", "their", "these", "those", "such", "can",
    "in", "on", "of", "to", "a", "an", "is", "be", "by", "as", "it", "we", "our", "or", "at",
    "논문", "연구", "방법", "결과", "사용", "대한", "통해", "있다", "한다", "에서", "으로", "그리고",
}

SECTION_ALIASES = {
    "abstract": ["abstract", "초록", "요약"],
    "introduction": ["introduction", "1 introduction", "서론", "1. 서론"],
    "related work": ["related work", "background", "관련 연구", "배경"],
    "method": ["method", "methods", "methodology", "approach", "proposed method", "모델", "방법론", "제안 방법"],
    "experiments": ["experiment", "experiments", "evaluation", "results", "실험", "평가", "결과"],
    "discussion": ["discussion", "analysis", "논의", "분석"],
    "conclusion": ["conclusion", "conclusions", "결론"],
    "limitations": ["limitation", "limitations", "한계", "제한점"],
}


def read_input_file(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    suffix = p.suffix.lower()
    if suffix in {".txt", ".md"}:
        return p.read_text(encoding="utf-8")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("PDF input requires pypdf. Install requirements.txt first.") from exc
        reader = PdfReader(str(p))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return "\n".join(pages)
    raise ValueError("Supported input formats are .txt, .md, and .pdf")


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sentences(text: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if not cleaned:
        return []
    pieces = re.split(r"(?<=[.!?。！？])\s+", cleaned)
    return [p.strip() for p in pieces if len(p.strip()) > 20]


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return "Untitled Paper"


def extract_authors(text: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2:
        return []
    candidate = lines[1]
    if len(candidate) > 160 or re.search(r"abstract|초록|introduction|서론", candidate, re.I):
        return []
    parts = re.split(r",|;| and |·|\|", candidate)
    return [p.strip() for p in parts if 1 < len(p.strip()) < 60][:8]


def canonical_section_name(header: str) -> str:
    h = re.sub(r"^[0-9IVXivx]+[.)]?\s*", "", header.strip()).lower()
    for canonical, aliases in SECTION_ALIASES.items():
        if any(a in h for a in aliases):
            return canonical
    return h[:40] if h else "unknown"


def split_sections(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    section_starts: List[Tuple[int, str]] = []
    header_pattern = re.compile(
        r"^\s*((?:[0-9]+\.?\s*)?(Abstract|Introduction|Related Work|Background|Method|Methods|Methodology|Approach|Experiments?|Evaluation|Results|Discussion|Conclusion|Limitations)|초록|요약|서론|관련 연구|배경|방법론|제안 방법|실험|평가|결과|논의|분석|결론|한계|제한점)\s*$",
        re.I,
    )
    for idx, line in enumerate(lines):
        if header_pattern.match(line.strip()):
            section_starts.append((idx, canonical_section_name(line)))
    if not section_starts:
        return {"full text": text}
    sections: Dict[str, str] = {}
    for i, (start, name) in enumerate(section_starts):
        end = section_starts[i + 1][0] if i + 1 < len(section_starts) else len(lines)
        body = "\n".join(lines[start + 1 : end]).strip()
        if body:
            sections[name] = body
    return sections or {"full text": text}


def extract_abstract(text: str, sections: Dict[str, str]) -> str:
    if sections.get("abstract"):
        return sections["abstract"][:2500].strip()
    m = re.search(r"abstract\s*\n(.{100,2500}?)(?:\n\s*(?:1\.?\s*)?introduction|\n\s*keywords|\n\s*index terms)", text, re.I | re.S)
    if m:
        return m.group(1).strip()
    sentences = split_sentences(text)
    return " ".join(sentences[:4])[:2500]


def top_keywords(text: str, n: int = 12) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{3,}|[가-힣]{2,}", text.lower())
    words = [w for w in words if w not in STOPWORDS and not w.isdigit()]
    counts = Counter(words)
    return [w for w, _ in counts.most_common(n)]


def keyword_sentences(text: str, keywords: Iterable[str], limit: int = 4) -> List[str]:
    sentences = split_sentences(text)
    kws = [k.lower() for k in keywords]
    scored = []
    for s in sentences:
        lower = s.lower()
        score = sum(1 for k in kws if k in lower)
        if score:
            scored.append((score, len(s), s))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [s for _, _, s in scored[:limit]]


def find_sentences_by_patterns(text: str, patterns: List[str], limit: int = 4) -> List[str]:
    sentences = split_sentences(text)
    matched = []
    regexes = [re.compile(p, re.I) for p in patterns]
    for s in sentences:
        if any(r.search(s) for r in regexes):
            matched.append(s)
    return matched[:limit]


def bulletize(sentences: List[str], limit: int = 5, max_len: int = 220) -> List[str]:
    bullets = []
    for s in sentences[:limit]:
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) > max_len:
            s = s[: max_len - 3].rstrip() + "..."
        bullets.append(s)
    return bullets


def safe_json_dump(data: Dict[str, Any], path: str) -> None:
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)



def extract_json_object(text: str) -> Dict[str, Any] | None:
    """Extract the first JSON object from a model response."""
    if not text:
        return None
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : idx + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        return None
    return None
