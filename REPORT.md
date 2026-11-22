# Brief Report

# LLM 기반 논문 요약·발표자료 기획 Agentic System

## 1. 시스템 개요

본 프로젝트는 **논문 요약·발표자료 기획 Agentic System**을 구현한 것이다. 사용자는 논문 파일을 입력하고, 시스템은 해당 논문을 분석하여 발표 준비에 필요한 요약, 슬라이드 구성안, 발표자 노트, 예상 질문과 답변을 생성한다.

본 시스템은 다음 기능을 수행한다.

1. `.txt`, `.md`, `.pdf` 형식의 논문 파일을 읽는다.
2. 논문 제목, 저자, 초록, 섹션, 주요 키워드를 추출한다.
3. Hugging Face LLM 기반 agent들을 사용하여 연구 문제, 방법론, 기여점, 한계점을 자연스럽게 요약한다.
4. 논문 발표에 적합한 8장 분량의 슬라이드 구성안을 생성한다.
5. 각 슬라이드에 대한 발표자 노트를 생성한다.
6. 발표 후 예상 질문과 답변을 생성한다.
7. Quality Review Agent가 결과물의 완성도와 누락 사항을 검토한다.
8. 최종 결과를 Markdown, JSON, workflow log 파일로 저장한다.

본 시스템은 agentic framework 중 하나인 **CrewAI**를 사용한다.

본 시스템은 LLM을 사용하였지만, TA 실행 환경에서 API token이나 네트워크 문제가 발생할 수 있으므로, Hugging Face LLM 호출이 실패하면 기존 deterministic pipeline 결과로 fallback되도록 구현하였다. `--require-llm` 옵션을 사용하면 LLM 호출 실패 시 오류가 발생하도록 strict mode로 실행할 수 있다.

---

## 2. 사용한 Agentic Framework

본 Homework #2에서 사용한 agentic framework는 CrewAI이다.

CrewAI를 선택한 이유는 다음과 같다.

- 각 agent의 role, goal, backstory를 명확하게 정의할 수 있다.
- 여러 agent가 순차적으로 협업하는 crew 구조를 설명하기 쉽다.
- 논문 발표 준비처럼 역할 분담이 중요한 작업에 적합하다.
- Paper Loader, Method Analyst, Slide Planner, Q&A Coach 등 전문 agent를 자연스럽게 구성할 수 있다.
- LLM 기반 agent와 로컬 tool 기반 agent를 함께 설명하기 쉽다.

본 시스템에서는 CrewAI의 agent/task/crew metadata를 구성하고, 실제 실행 workflow에서는 각 agent가 공통 state를 업데이트한다. LLM 사용이 가능한 agent들은 Hugging Face LLM을 호출하여 결과를 자연스럽게 개선한다.

---

## 3. 시스템 기능 설명

### 3.1 입력

시스템은 다음 형식의 논문 파일을 입력으로 받을 수 있다.

```text
.txt
.md
.pdf
```

실행 예시는 다음과 같다.

```bash
python run.py --input sample_papers/sample_ai_paper.txt --output outputs --print-summary
```

PDF 논문도 다음과 같이 입력할 수 있다.

```bash
python run.py --input path/to/paper.pdf --output outputs --print-summary
```

### 3.2 LLM 사용 방식

본 시스템은 기본적으로 Hugging Face LLM enhancement를 시도한다. Hugging Face token은 환경변수 `HF_TOKEN`으로 설정한다.

Windows PowerShell:

```powershell
$env:HF_TOKEN="hf_your_token_here"
```

macOS 또는 Linux:

```bash
export HF_TOKEN="hf_your_token_here"
```

LLM 호출이 성공하면 다음 agent들이 LLM을 사용하여 결과를 개선한다.

- Problem and Motivation Agent
- Method Analysis Agent
- Contribution and Limitation Agent
- Slide Planner Agent
- Speaker Notes Agent
- Q&A Preparation Agent
- Quality Review Agent

LLM 호출이 실패하면 프로그램이 바로 종료되지 않고 deterministic fallback 결과를 사용한다. 단, 다음 옵션을 사용하면 LLM 호출 실패 시 오류를 발생시킬 수 있다.

```bash
python run.py --input sample_papers/sample_ai_paper.txt --require-llm --output outputs --print-summary
```

LLM 없이 실행하고 싶을 때는 다음 옵션을 사용할 수 있다.

```bash
python run.py --input sample_papers/sample_ai_paper.txt --no-llm --output outputs --print-summary
```

### 3.3 출력

시스템 실행 후 다음 파일이 생성된다.

```text
outputs/paper_presentation_report.md
outputs/paper_presentation_report.json
outputs/paper_presentation_workflow.txt
```

각 파일의 역할은 다음과 같다.

| 파일명                            | 설명                                                                  |
| --------------------------------- | --------------------------------------------------------------------- |
| `paper_presentation_report.md`    | 사람이 읽기 쉬운 Markdown 형식의 논문 요약 및 발표자료 기획 report    |
| `paper_presentation_report.json`  | agent별 분석 결과, LLM 사용 여부, 최종 결과를 담은 구조화된 JSON 파일 |
| `paper_presentation_workflow.txt` | agentic workflow 실행 과정을 기록한 파일                              |

---

## 4. 실행 방법

### 4.1 가상환경 생성

```bash
python -m venv .venv
```

Windows PowerShell에서는 다음 명령으로 가상환경을 활성화한다.

```powershell
.venv\Scripts\Activate.ps1
```

macOS 또는 Linux에서는 다음 명령을 사용한다.

```bash
source .venv/bin/activate
```

### 4.2 필요한 패키지 설치

```bash
python -m pip install -r requirements.txt
```

`requirements.txt`에는 CrewAI, Hugging Face API 호출을 위한 `huggingface_hub`, PDF 처리를 위한 `pypdf`가 포함되어 있다.

### 4.3 Hugging Face Token 설정

Windows PowerShell:

```powershell
$env:HF_TOKEN="hf_your_token_here"
```

macOS 또는 Linux:

```bash
export HF_TOKEN="hf_your_token_here"
```

### 4.4 샘플 논문 실행

```bash
python run.py --input sample_papers/sample_ai_paper.txt --output outputs --print-summary
```

### 4.5 PDF 논문 실행

```bash
python run.py --input path/to/paper.pdf --output outputs --print-summary
```

### 4.6 사용할 LLM 모델 지정

```bash
python run.py --input sample_papers/sample_ai_paper.txt --model Qwen/Qwen2.5-1.5B-Instruct --output outputs --print-summary
```

### 4.7 테스트 실행

```bash
python -m pytest tests
```

---

## 5. 사용한 Agent와 역할

본 시스템은 총 **9개의 agent**를 사용한다.

| 번호 | Agent 이름                        | 역할                                                                                                |
| ---: | --------------------------------- | --------------------------------------------------------------------------------------------------- |
|    1 | Paper Loader Agent                | 논문 파일을 읽고 텍스트를 정리한다. `.txt`, `.md`, `.pdf` 입력을 처리한다.                          |
|    2 | Paper Structure Agent             | 제목, 저자, 초록, 섹션, 키워드 등 논문 구조 정보를 추출한다.                                        |
|    3 | Problem and Motivation Agent      | Hugging Face LLM을 사용하여 논문의 연구 문제, 배경, 동기를 자연스럽게 요약한다.                     |
|    4 | Method Analysis Agent             | Hugging Face LLM을 사용하여 제안 방법, 모델, 알고리즘, 시스템 구조를 발표용으로 요약한다.           |
|    5 | Contribution and Limitation Agent | Hugging Face LLM을 사용하여 논문의 주요 기여점, 실험 결과, 한계점을 정리한다.                       |
|    6 | Slide Planner Agent               | Hugging Face LLM을 사용하여 논문 발표에 적합한 slide-by-slide 구성안을 생성한다.                    |
|    7 | Speaker Notes Agent               | Hugging Face LLM을 사용하여 각 슬라이드에서 발표자가 말할 내용을 자연스러운 발표자 노트로 작성한다. |
|    8 | Q&A Preparation Agent             | Hugging Face LLM을 사용하여 발표 후 나올 수 있는 예상 질문과 답변을 생성한다.                       |
|    9 | Quality Review Agent              | Hugging Face LLM을 사용하여 최종 결과의 완성도, 누락 사항, 개선점을 검토한다.                       |

각 agent는 서로 다른 역할을 담당하며, 이전 agent의 결과를 다음 agent가 활용한다. 따라서 단일 prompt로 모든 결과를 한 번에 생성하는 방식보다 agentic system의 구조가 명확하다.

---

## 6. 사용한 Agentic Design Pattern과 목적

본 시스템은 총 **11개의 agentic design pattern**을 사용한다.

| 번호 | Design Pattern                | 사용 목적                                                                                                                     |
| ---: | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
|    1 | Multi-Agent Collaboration     | 논문 분석과 발표자료 기획을 여러 전문 agent가 나누어 수행한다.                                                                |
|    2 | Role-Based Agents             | CrewAI의 role, goal, backstory 구조를 활용하여 각 agent의 전문성을 명확히 정의한다.                                           |
|    3 | Sequential Workflow           | 논문 로딩 → 구조 분석 → 문제 분석 → 방법 분석 → 기여/한계 분석 → 슬라이드 기획 → 발표 노트 → Q&A → 품질 검토 순서로 진행한다. |
|    4 | Task Decomposition            | “논문 발표 준비”라는 큰 작업을 여러 작은 작업으로 분해한다.                                                                   |
|    5 | Tool Use                      | 파일 읽기, PDF 텍스트 추출, 섹션 분리, 문장 분리, 키워드 추출, Markdown/JSON 저장 도구를 사용한다.                            |
|    6 | LLM-as-Generator              | Hugging Face LLM을 사용하여 요약, 발표 흐름, 발표자 노트, Q&A를 자연스럽게 생성한다.                                          |
|    7 | Structured Output             | LLM agent가 JSON 형태의 구조화된 결과를 반환하도록 하여 후속 agent가 안정적으로 처리할 수 있게 한다.                          |
|    8 | Reflection / Critique         | Quality Review Agent가 최종 결과의 완성도와 누락 사항을 검토한다.                                                             |
|    9 | Presentation Planning Pattern | 논문 내용을 발표 흐름에 맞는 slide-by-slide plan으로 변환한다.                                                                |
|   10 | Knowledge Distillation        | 긴 논문 내용을 핵심 문제, 방법, 기여점, 한계점으로 압축한다.                                                                  |
|   11 | Graceful Fallback             | Hugging Face token이 없거나 LLM 호출에 실패해도 deterministic pipeline을 통해 실행 안정성을 확보한다.                         |

이러한 pattern을 통해 본 시스템은 단순한 요약 프로그램이 아니라, 여러 agent가 협업하여 논문 발표 준비 과정을 자동화하는 agentic system으로 동작한다.

---

## 7. 시스템 처리 흐름

본 시스템의 전체 workflow는 다음과 같다.

```text
Paper input
→ Paper Loader Agent
→ Paper Structure Agent
→ Problem and Motivation Agent using LLM
→ Method Analysis Agent using LLM
→ Contribution and Limitation Agent using LLM
→ Slide Planner Agent using LLM
→ Speaker Notes Agent using LLM
→ Q&A Preparation Agent using LLM
→ Quality Review Agent using LLM
→ Report Writer
```

각 단계는 공통 state를 업데이트하며, 이후 단계의 agent가 이전 결과를 활용한다.

---

## 8. 실행 예시

샘플 논문 파일을 사용한 실행 예시는 다음과 같다.

```bash
python run.py --input sample_papers/sample_ai_paper.txt --output outputs --print-summary
```

예상 출력 예시는 다음과 같다.

```text
Paper Presentation Planning completed successfully.
Framework status: CrewAI objects created successfully; LLM enhancement: enabled; HF_TOKEN detected.
Title: Lightweight Multi-Agent Planning for Academic Paper Presentations
Slides: 8
Q&A items: 5
Hugging Face LLM agents used: 7 / 7
Report: outputs/paper_presentation_report.md
JSON: outputs/paper_presentation_report.json
Workflow: outputs/paper_presentation_workflow.txt
```

Hugging Face token이 없거나 API 호출이 실패하면 다음처럼 fallback 실행 결과가 나올 수 있다.

```text
Hugging Face LLM agents used: 0 / 7
```

이 경우에도 프로그램은 실행되지만, LLM 기반 자연어 개선은 적용되지 않는다.

---

## 9. 시스템의 장점

본 시스템의 장점은 다음과 같다.

첫째, 논문 파일을 입력하면 요약, 슬라이드 구성안, 발표자 노트, 예상 Q&A를 한 번에 생성할 수 있어 실제 발표 준비에 유용하다.

둘째, Hugging Face LLM을 사용하여 기존 규칙 기반 결과보다 자연스럽고 발표에 적합한 문장을 생성한다.

셋째, 여러 agent가 각각 다른 관점에서 작업을 수행하므로 결과 생성 과정이 설명 가능하다.

넷째, Markdown report와 JSON output을 모두 생성하므로 사람이 읽기에도 좋고, 후속 프로그램에서 활용하기에도 좋다.

다섯째, LLM API가 실패해도 fallback이 동작하므로 TA 실행 환경에서 오류 가능성을 줄였다.

---

## 10. 결론

본 프로젝트는 CrewAI 기반의 LLM-enhanced 논문 요약·발표자료 기획 agentic system을 구현하였다. 시스템은 논문 입력을 받아 구조 분석, 연구 문제 분석, 방법론 요약, 기여점과 한계점 정리, 슬라이드 구성안 생성, 발표자 노트 생성, 예상 Q&A 생성, 품질 검토를 수행한다.
