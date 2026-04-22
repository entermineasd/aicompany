# 🤖 AI 컴퍼니 — 멀티 에이전트 AI 시스템

주제를 던지면 AI 직원 10명이 실제로 토론하고, 최종 보고서와 코드까지 생성하는 멀티 에이전트 시스템

## 🌐 배포 URL
https://aicompany-production.up.railway.app

## ✨ 주요 기능
- 주제 입력 → AI 10명 순서대로 실시간 토론
- 신경망 시각화 (토론 흐름을 빛으로 표현)
- 기획자1 (불도저/공격적) vs 기획자2 (안전제일/보수적) 성격 부여
- 3라운드 맞토론 (반박 → 재반박 → 최후진술)
- Devil's Advocate — 악마의 변호인이 양측 약점 분석
- 경쟁사 자동 분석
- 토론 온도계 (공격 vs 보수 팽팽한 정도 시각화)
- 전체 AI 찬반 투표 (통과/부결)
- 검토자들이 최적안 조합 (장점만 합치기)
- 재검토 요청 시 기획자들 수정 후 재조합
- 주차별 실행 계획 자동 생성
- 피드백 반영 (대표가 의견 주면 AI들이 수정)
- 코드 짜줘 버튼 (AI가 실제 Flask 코드 생성)
- 히스토리 DB 저장 + 다시 보기
- SSE 실시간 스트리밍
- 주제 반려 기능 (불법/불가능한 주제 거부)

## 💡 활용 팁
- aicompany 최종 보고서를 복사해서 paper-summarizer에 붙여넣으면 핵심만 요약해줌
- github.com/entermineasd/paper-summarizer

## 👥 AI 직원 구성
| 역할 | 담당 | 성격 |
|------|------|------|
| 기획자1 | 공격안 제시 | 불도저 |
| 기획자2 | 보수안 제시 | 안전제일 |
| 검토자1 | 비교 분석 | 냉철한 분석가 |
| 검토자2 | 최적안 조율 | 의사결정 전문가 |
| 개발자1 | 기술 스택 | 백엔드 |
| 개발자2 | 개발 일정 | 풀스택 |
| 개발자3 | DB 설계 | DB 전문가 |
| 테스터1 | QA 기준 | QA 엔지니어 |
| 테스터2 | 약점 분석 | 악마의 변호인 |
| 최종검토 | 보고서 작성 | 프로젝트 매니저 |

## 🛠 기술 스택
- Python, Flask
- OpenAI API (gpt-4o-mini)
- SQLite (Flask-SQLAlchemy)
- SSE (Server-Sent Events) 실시간 스트리밍
- HTML/CSS/JavaScript (Canvas 신경망 시각화)

## 🚀 실행 방법
1. 라이브러리 설치
```bash
pip install flask openai flask-sqlalchemy gunicorn
```

2. OpenAI API 키 설정
```bash
export OPENAI_API_KEY="your-api-key"
```

3. 실행
```bash
PORT=8081 python3 app.py
```

4. 브라우저 접속
http://localhost:8081

## 💡 사용 예시
- "중소기업 재고관리 SaaS 만들기"
- "동네 세탁소 AI 자동화 서비스"
- "AI 직원 10명으로 1인 기업 운영하기"