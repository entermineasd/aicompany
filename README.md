AI 컴퍼니 — 멀티 에이전트 시스템

주제를 던지면 AI 직원 10명이 실제로 토론하고, 최종 보고서와 코드까지 생성하는 멀티 에이전트 시스템

주요 기능
- 주제 입력 → AI 10명 순서대로 실시간 토론
- 신경망 시각화 (토론 흐름을 빛으로 표현)
- 피드백 반영 → AI들이 방향 수정 후 재토론
- 최종 보고서 자동 생성
- "코드 짜줘" 버튼 → AI가 실제 Flask 코드 생성

AI 직원 구성
| 역할 | 담당 |
|------|------|
| 기획자 x2 | 아이디어 제안 + 보완 |
| 검토자 x2 | 리스크 + 시장성 분석 |
| 개발자 x3 | 기술스택 + 일정 + DB 설계 |
| 테스터 x2 | QA + UX 검토 |
| 최종검토 x1 | 전체 취합 후 대표 보고 |

기술 스택
- Python, Flask
- OpenAI API (gpt-4o-mini)
- SSE (Server-Sent Events) 실시간 스트리밍
- HTML/CSS/JavaScript (Canvas 신경망 시각화)

실행 방법
1. 라이브러리 설치
```bash
pip install flask openai
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

사용 예시
- "중소기업 재고관리 SaaS 만들기"
- "배달앱 MVP 기획"
- "AI 자동화 대행 비즈니스 전략"

배포 URL
https://your-railway-url.up.railway.app