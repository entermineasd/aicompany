from flask import Flask, render_template_string, request, Response, stream_with_context
from openai import OpenAI
from flask_sqlalchemy import SQLAlchemy
import os
import json
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aicompany.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(500), nullable=False)
    report = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

def ask(system, user):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return res.choices[0].message.content

def send(event, data):
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

last_results = {}
last_topic = ""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/history")
def history():
    discussions = Discussion.query.order_by(Discussion.created_at.desc()).all()
    return jsonify_list([{"id": d.id, "topic": d.topic, "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"), "report": d.report} for d in discussions])

def jsonify_list(data):
    from flask import Response
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/json")

@app.route("/run")
def run():
    global last_results, last_topic
    topic = request.args.get("topic", "")
    last_topic = topic
    last_results = {}

    def generate():
        global last_results
        results = {}

        # 주제 유효성 검사
        yield send("status", {"id": "fin", "state": "thinking", "text": "주제 검토 중..."})
        validity = ask(
            "당신은 프로젝트 게이트키퍼입니다. 완전히 불법이거나 물리적으로 불가능한 경우에만 '거부:이유'로 답하세요. 도전적이거나 어렵더라도 비즈니스/개발 아이디어면 무조건 '승인'으로 답하세요.",
            f"주제: {topic}"
        )
        if validity.startswith("거부"):
            reason = validity.replace("거부:", "").strip()
            yield send("rejected", {"reason": reason})
            yield send("done", {})
            return
        yield send("status", {"id": "fin", "state": "done", "text": "주제 승인"})

        # 경쟁 분석 AI
        yield send("status", {"id": "r1", "state": "thinking", "text": "경쟁사 분석 중..."})
        competition = ask(
            "당신은 시장 경쟁 분석가입니다. 주어진 주제의 현재 경쟁사, 유사 서비스, 시장 공백을 분석하세요. 경쟁사 3개와 차별화 포인트를 제시하세요. 3-4문장으로.",
            f"주제: {topic}"
        )
        results["competition"] = competition
        yield send("msg", {"id": "r1", "text": competition, "tag": "경쟁분석"})
        yield send("status", {"id": "r1", "state": "done", "text": "경쟁분석 완료"})

        # 기획자1 — 공격적
        yield send("status", {"id": "p1", "state": "thinking", "text": "공격안 구상 중..."})
        r = ask(
            "당신은 공격적 성향의 스타트업 기획자 '불도저'입니다. 경쟁 분석을 참고해서 리스크를 감수하고 크고 빠르게 가는 방향을 제안하세요. 시장 선점, 빠른 확장을 강조하세요. 2-3문장으로.",
            f"주제: {topic}\n경쟁분석: {competition}"
        )
        results["p1"] = r
        yield send("msg", {"id": "p1", "text": r, "tag": "공격안"})
        yield send("status", {"id": "p1", "state": "done", "text": "공격안 완료"})

        # 기획자2 — 보수적
        yield send("status", {"id": "p2", "state": "thinking", "text": "보수안 구상 중..."})
        r = ask(
            "당신은 보수적 성향의 스타트업 기획자 '안전제일'입니다. 경쟁 분석을 참고해서 검증하고 단계적으로 가는 방향을 제안하세요. 리스크 최소화를 강조하세요. 2-3문장으로.",
            f"주제: {topic}\n경쟁분석: {competition}\n공격안 참고: {results['p1']}"
        )
        results["p2"] = r
        yield send("msg", {"id": "p2", "text": r, "tag": "보수안"})
        yield send("status", {"id": "p2", "state": "done", "text": "보수안 완료"})

        # Devil's Advocate
        yield send("status", {"id": "t2", "state": "thinking", "text": "약점 찾는 중..."})
        devil = ask(
            "당신은 Devil's Advocate입니다. 별명은 '악마의 변호인'이에요. 공격안과 보수안 둘 다의 최악의 시나리오와 치명적 약점을 찾아내세요. 절대 긍정적인 말은 하지 마세요. 3-4문장으로.",
            f"주제: {topic}\n공격안: {results['p1']}\n보수안: {results['p2']}"
        )
        results["devil"] = devil
        yield send("msg", {"id": "t2", "text": devil, "tag": "악마의 변호인"})
        yield send("status", {"id": "t2", "state": "done", "text": "약점 분석 완료"})

        # 1라운드 토론
        yield send("round", {"round": 1, "text": "1라운드 — 기획자 맞토론"})
        yield send("status", {"id": "p1", "state": "thinking", "text": "반박 중..."})
        r = ask(
            "당신은 공격적 기획자 '불도저'입니다. 악마의 변호인 지적과 보수안에 반박하세요. 2문장으로.",
            f"보수안: {results['p2']}\n악마 지적: {devil}"
        )
        results["p1_r1"] = r
        yield send("msg", {"id": "p1", "text": r, "tag": "1라운드 반박"})
        yield send("status", {"id": "p1", "state": "done", "text": "반박 완료"})

        yield send("status", {"id": "p2", "state": "thinking", "text": "재반박 중..."})
        r = ask(
            "당신은 보수적 기획자 '안전제일'입니다. 불도저의 반박과 악마의 지적에 맞서세요. 2문장으로.",
            f"공격 반박: {results['p1_r1']}\n악마 지적: {devil}"
        )
        results["p2_r1"] = r
        yield send("msg", {"id": "p2", "text": r, "tag": "1라운드 재반박"})
        yield send("status", {"id": "p2", "state": "done", "text": "재반박 완료"})

        # 2라운드 토론
        yield send("round", {"round": 2, "text": "2라운드 — 심화 토론"})
        yield send("status", {"id": "p1", "state": "thinking", "text": "2라운드 공격 중..."})
        r = ask(
            "당신은 공격적 기획자 '불도저'입니다. 상대방 주장의 핵심 약점을 파고드세요. 더 구체적인 근거를 들어 설득하세요. 2문장으로.",
            f"상대 주장: {results['p2_r1']}\n내 주장: {results['p1_r1']}"
        )
        results["p1_r2"] = r
        yield send("msg", {"id": "p1", "text": r, "tag": "2라운드"})
        yield send("status", {"id": "p1", "state": "done", "text": "2라운드 완료"})

        yield send("status", {"id": "p2", "state": "thinking", "text": "2라운드 방어 중..."})
        r = ask(
            "당신은 보수적 기획자 '안전제일'입니다. 상대방의 2라운드 공격에 맞서 최후의 주장을 펼치세요. 2문장으로.",
            f"상대 공격: {results['p1_r2']}\n내 주장: {results['p2_r1']}"
        )
        results["p2_r2"] = r
        yield send("msg", {"id": "p2", "text": r, "tag": "2라운드"})
        yield send("status", {"id": "p2", "state": "done", "text": "2라운드 완료"})

        # 3라운드 — 최후진술
        yield send("round", {"round": 3, "text": "3라운드 — 최후 진술"})
        yield send("status", {"id": "p1", "state": "thinking", "text": "최후 진술 중..."})
        r = ask(
            "당신은 공격적 기획자 '불도저'입니다. 모든 토론을 종합해서 최후 진술을 하세요. 1-2문장으로 핵심만.",
            f"전체 토론: {results['p1_r1']} / {results['p1_r2']}"
        )
        results["p1_final"] = r
        yield send("msg", {"id": "p1", "text": r, "tag": "최후진술"})
        yield send("status", {"id": "p1", "state": "done", "text": "최후진술 완료"})

        yield send("status", {"id": "p2", "state": "thinking", "text": "최후 진술 중..."})
        r = ask(
            "당신은 보수적 기획자 '안전제일'입니다. 모든 토론을 종합해서 최후 진술을 하세요. 1-2문장으로 핵심만.",
            f"전체 토론: {results['p2_r1']} / {results['p2_r2']}"
        )
        results["p2_final"] = r
        yield send("msg", {"id": "p2", "text": r, "tag": "최후진술"})
        yield send("status", {"id": "p2", "state": "done", "text": "최후진술 완료"})

        # 토론 온도 측정
        temp = ask(
            "토론을 분석해서 0~100 숫자 하나만 답하세요. 0=완전 보수, 100=완전 공격, 50=팽팽.",
            f"공격안: {results['p1']}\n보수안: {results['p2']}\n전체토론: {results['p1_r2']} / {results['p2_r2']}"
        )
        try:
            temp_val = int(''.join(filter(str.isdigit, temp)))
            temp_val = max(0, min(100, temp_val))
        except:
            temp_val = 50
        yield send("temperature", {"value": temp_val})

        # 검토자1 — 비교 분석
        yield send("status", {"id": "r1", "state": "thinking", "text": "전체 토론 분석 중..."})
        r = ask(
            "당신은 냉철한 전략 분석가입니다. 이전 토론 기록이 있다면 반드시 언급하고 더 발전된 분석을 하세요. 3라운드 토론과 악마의 변호인 지적을 모두 반영해서 공격안과 보수안을 최종 비교 분석하세요. 재검토가 필요하면 '재검토 필요'를 명시하세요. 3-4문장으로.",
            f"주제: {topic}\n공격안: {results['p1']}\n보수안: {results['p2']}\n악마: {devil}\n토론전체: {results['p1_r2']} / {results['p2_r2']}"
        )
        results["r1"] = r
        yield send("msg", {"id": "r1", "text": r, "tag": "최종분석"})
        yield send("status", {"id": "r1", "state": "done", "text": "분석 완료"})

        # 검토자2 — 최적안
        yield send("status", {"id": "r2", "state": "thinking", "text": "최적안 조합 중..."})
        r = ask(
            "당신은 의사결정 전문가입니다. 악마의 변호인 지적을 반영해서 공격안+보수안 장점을 합치고 단점을 제거한 최적안을 만드세요. 조합 불가시 재검토 요청. 3-4문장으로.",
            f"주제: {topic}\n공격안: {results['p1']}\n보수안: {results['p2']}\n악마지적: {devil}\n분석: {results['r1']}"
        )
        results["r2"] = r
        needs_redo = ask("아래 검토 내용에서 기획자들에게 명시적으로 재검토를 요청하는 내용이 있으면 'yes', 단순히 장단점 언급 수준이면 'no'만 답하세요.", f"{results['r1']}\n{r}") == "yes"
        yield send("msg", {"id": "r2", "text": r, "tag": "최적안"})
        yield send("status", {"id": "r2", "state": "done", "text": "최적안 도출"})

        if needs_redo:
            yield send("round", {"round": 4, "text": "재검토 라운드 — 기획자 수정"})
            yield send("status", {"id": "p1", "state": "thinking", "text": "재검토 중..."})
            r = ask(
            "검토자 피드백을 반영해 공격안과 보수안의 장점만 합친 수정안을 2문장으로 제시하세요.",
            f"주제: {topic}\n공격안: {results['p1']}\n보수안: {results['p2']}\n피드백: {results['r2']}"
            )
            results["p1"] = r
            yield send("msg", {"id": "p1", "text": r, "tag": "수정안"})
            yield send("status", {"id": "p1", "state": "done", "text": "수정 완료"})
            yield send("status", {"id": "r2", "state": "thinking", "text": "최적안 재조합 중..."})
            r = ask(
            "수정안을 바탕으로 최적안을 3문장으로 제시하세요.",
            f"수정안: {results['p1']}\n악마지적: {devil}"
            )
            results["r2"] = r
            yield send("msg", {"id": "r2", "text": r, "tag": "최종 최적안"})
            yield send("status", {"id": "r2", "state": "done", "text": "최적안 확정"})

        # 전체 AI 투표
        yield send("round", {"round": 0, "text": "전체 투표 — 최적안 찬반"})
        votes = {}
        vote_agents = [
            ("d1", "백엔드 개발자"),
            ("d2", "풀스택 개발자"),
            ("d3", "DB 전문가"),
            ("t1", "QA 엔지니어"),
            ("t2", "UX 테스터"),
        ]
        yes_count = 0
        for agent_id, agent_role in vote_agents:
            yield send("status", {"id": agent_id, "state": "thinking", "text": "투표 중..."})
            vote = ask(
                f"당신은 {agent_role}입니다. 아래 최적안에 대해 '찬성\' 또는 \'반대\' 중 하나만 답하세요. 최적안의 실행 계획이 현실적이면 찬성, 치명적 결함이 있으면 반대하세요. 구체적 이유 한 줄.",
                f"주제: {topic}\n최적안: {results['r2']}"
            )
            votes[agent_id] = vote
            is_yes = "찬성" in vote
            if is_yes:
                yes_count += 1
            yield send("msg", {"id": agent_id, "text": vote, "tag": "찬성" if is_yes else "반대"})
            yield send("status", {"id": agent_id, "state": "done", "text": "찬성" if is_yes else "반대"})

        yield send("vote_result", {"yes": yes_count, "total": len(vote_agents)})

        # 개발자들 — 실행
        yield send("status", {"id": "d1", "state": "thinking", "text": "기술 스택 검토 중..."})
        r = ask("시니어 백엔드 개발자로서 기술 스택만 나열하세요. 전략 얘기 금지. 언어, 프레임워크, DB, 클라우드 추천 이유와 함께 2-3문장.",
                f"주제: {topic}\n최적안: {results['r2']}")
        results["d1"] = r
        yield send("msg", {"id": "d1", "text": r, "tag": "기술스택"})
        yield send("status", {"id": "d1", "state": "done", "text": "완료"})

        yield send("status", {"id": "d2", "state": "thinking", "text": "개발 일정 산정 중..."})
        r = ask("풀스택 개발자로서 MVP 개발 기간과 주요 단계를 2-3문장으로 제시하세요.",
                f"주제: {topic}\n최적안: {results['r2']}\n기술: {results['d1']}")
        results["d2"] = r
        yield send("msg", {"id": "d2", "text": r, "tag": "개발일정"})
        yield send("status", {"id": "d2", "state": "done", "text": "완료"})

        yield send("status", {"id": "d3", "state": "thinking", "text": "DB 설계 중..."})
        r = ask("DB 전문가로서 핵심 데이터 구조와 설계 방향을 2-3문장으로 제시하세요.",
                f"주제: {topic}\n기술: {results['d1']}")
        results["d3"] = r
        yield send("msg", {"id": "d3", "text": r, "tag": "DB설계"})
        yield send("status", {"id": "d3", "state": "done", "text": "완료"})

        yield send("status", {"id": "t1", "state": "thinking", "text": "QA 기준 수립 중..."})
        r = ask("QA 엔지니어로서 핵심 테스트 항목과 품질 기준을 2-3문장으로 제시하세요.",
                f"주제: {topic}\n기술: {results['d1']}\n일정: {results['d2']}")
        results["t1"] = r
        yield send("msg", {"id": "t1", "text": r, "tag": "QA"})
        yield send("status", {"id": "t1", "state": "done", "text": "완료"})

        yield send("status", {"id": "t2", "state": "thinking", "text": "UX 검토 중..."})
        r = ask("UX 테스터로서 사용성 주의사항과 개선 방향을 2-3문장으로 제시하세요.",
                f"주제: {topic}\n최적안: {results['r2']}\nQA: {results['t1']}")
        results["t2"] = r
        yield send("msg", {"id": "t2", "text": r, "tag": "UX"})
        yield send("status", {"id": "t2", "state": "done", "text": "완료"})

        # 실행 계획 AI
        yield send("status", {"id": "fin", "state": "thinking", "text": "실행 계획 수립 중..."})
        action_plan = ask(
            "당신은 프로젝트 매니저입니다. 아래 내용을 바탕으로 주차별 실행 계획을 수립하세요.\n형식:\n1주차: \n2주차: \n3주차: \n4주차: \n2개월차: \n3개월차: ",
            f"주제: {topic}\n최적안: {results['r2']}\n기술: {results['d1']}\n일정: {results['d2']}"
        )
        results["action_plan"] = action_plan
        yield send("msg", {"id": "fin", "text": action_plan, "tag": "실행계획"})

        # 최종 보고서
        r = ask(
            "최종 보고 담당자로서 대표에게 보고할 최종 요약을 작성하세요.\n형식:\n[핵심 아이디어]\n[경쟁 환경]\n[공격안 vs 보수안]\n[최적안]\n[투표 결과]\n[MVP 기능 3가지]\n[기술 스택]\n[주차별 실행 계획]\n[리스크 대응]\n[최종 결론]",
            f"주제: {topic}\n경쟁: {competition}\n공격안: {results['p1']}\n보수안: {results['p2']}\n악마: {devil}\n최적안: {results['r2']}\n투표: {yes_count}/{len(vote_agents)} 찬성\n기술: {results['d1']}\n일정: {results['d2']}\nDB: {results['d3']}\nQA: {results['t1']}\nUX: {results['t2']}\n실행계획: {action_plan}"
        )
        results["fin"] = r
        last_results = results.copy()

        with app.app_context():
            d = Discussion(topic=topic, report=r)
            db.session.add(d)
            db.session.commit()

        yield send("msg", {"id": "fin", "text": r, "tag": "최종보고"})
        yield send("status", {"id": "fin", "state": "done", "text": "보고 완료"})
        yield send("report", {"text": r, "topic": topic})

        feedback_q = ask(
            "프로젝트 매니저로서 보고서 전달 후 대표에게 방향성 확인을 위한 짧은 질문 하나만 하세요.",
            f"주제: {topic}\n보고서: {r}"
        )
        yield send("feedback_question", {"text": feedback_q})
        yield send("done", {})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/feedback")
def feedback():
    user_feedback = request.args.get("feedback", "")
    topic = last_topic

    def generate():
        yield send("status", {"id": "p1", "state": "thinking", "text": "피드백 반영 중..."})
        r = ask(
            "공격적 기획자로서 대표 피드백을 반영해 공격안을 수정하세요. 2-3문장.",
            f"주제: {topic}\n기존안: {last_results.get('p1','')}\n피드백: {user_feedback}"
        )
        yield send("msg", {"id": "p1", "text": r, "tag": "수정 공격안"})
        yield send("status", {"id": "p1", "state": "done", "text": "수정 완료"})

        yield send("status", {"id": "p2", "state": "thinking", "text": "피드백 반영 중..."})
        r2 = ask(
            "보수적 기획자로서 대표 피드백을 반영해 보수안을 수정하세요. 2-3문장.",
            f"주제: {topic}\n기존안: {last_results.get('p2','')}\n피드백: {user_feedback}"
        )
        yield send("msg", {"id": "p2", "text": r2, "tag": "수정 보수안"})
        yield send("status", {"id": "p2", "state": "done", "text": "수정 완료"})

        yield send("status", {"id": "fin", "state": "thinking", "text": "수정 보고서 작성 중..."})
        fin = ask(
            "피드백 반영 수정 보고서를 작성하세요.\n형식:\n[수정된 핵심 아이디어]\n[변경 사항]\n[주차별 실행 계획]\n[최종 결론]",
            f"주제: {topic}\n피드백: {user_feedback}\n수정 공격안: {r}\n수정 보수안: {r2}\n기존 보고서: {last_results.get('fin','')}"
        )
        yield send("msg", {"id": "fin", "text": fin, "tag": "수정 보고서"})
        yield send("status", {"id": "fin", "state": "done", "text": "완료"})
        yield send("report", {"text": fin, "topic": f"{topic} (수정본)"})
        yield send("done", {})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/generate-code")
def generate_code():
    topic = request.args.get("topic", last_topic)

    def generate():
        yield send("status", {"id": "d1", "state": "thinking", "text": "코드 생성 중..."})
        yield send("status", {"id": "d2", "state": "thinking", "text": "코드 생성 중..."})
        yield send("status", {"id": "d3", "state": "thinking", "text": "코드 생성 중..."})
        code = ask(
            "시니어 풀스택 개발자로서 Python Flask + SQLite로 실제 실행 가능한 MVP 코드를 작성하세요. app.py 전체 코드만 주세요.",
            f"주제: {topic}\n최적안: {last_results.get('r2','')}\n기술: {last_results.get('d1','')}\nDB: {last_results.get('d3','')}"
        )
        yield send("status", {"id": "d1", "state": "done", "text": "완료"})
        yield send("status", {"id": "d2", "state": "done", "text": "완료"})
        yield send("status", {"id": "d3", "state": "done", "text": "완료"})
        yield send("code", {"text": code})
        yield send("done", {})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

HTML = '''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>AI 컴퍼니 v3</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,sans-serif;background:#f5f7fa;color:#1a1a2e;}
.layout{display:flex;min-height:100vh;}
.sidebar{width:210px;background:#0f172a;padding:20px 0;flex-shrink:0;position:fixed;height:100vh;overflow-y:auto;}
.sidebar-logo{color:white;font-size:13px;font-weight:600;padding:0 14px 14px;border-bottom:1px solid rgba(255,255,255,0.1);}
.sidebar-logo span{font-size:9px;color:#94a3b8;display:block;margin-top:2px;}
.agent-list{padding:10px 6px;}
.agent-item{display:flex;align-items:center;gap:7px;padding:6px 8px;border-radius:7px;margin-bottom:2px;transition:background 0.2s;}
.agent-item.thinking{background:rgba(245,158,11,0.15);}
.agent-item.done{background:rgba(16,185,129,0.12);}
.a-avatar{width:22px;height:22px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:7px;font-weight:600;flex-shrink:0;}
.a-info{flex:1;min-width:0;}
.a-name{font-size:10px;font-weight:500;color:#e2e8f0;}
.a-status{font-size:9px;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.a-dot{width:5px;height:5px;border-radius:50%;background:#334155;flex-shrink:0;}
.a-dot.thinking{background:#f59e0b;animation:blink 0.8s infinite;}
.a-dot.done{background:#10b981;}
.hist-btn{margin:6px 8px;padding:6px 10px;background:rgba(255,255,255,0.05);border:0.5px solid rgba(255,255,255,0.1);border-radius:7px;color:#94a3b8;font-size:10px;cursor:pointer;width:calc(100% - 16px);text-align:left;}
.hist-btn:hover{background:rgba(255,255,255,0.1);color:white;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.main{flex:1;margin-left:210px;padding:20px;}
.top{background:white;border-radius:12px;padding:18px;margin-bottom:14px;border:1px solid #e5e7eb;}
.top h1{font-size:15px;font-weight:600;margin-bottom:10px;}
.input-row{display:flex;gap:8px;}
.input-row input{flex:1;padding:9px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;outline:none;}
.input-row input:focus{border-color:#0f172a;}
.btn{padding:8px 18px;background:#0f172a;color:white;border:none;border-radius:8px;font-size:12px;cursor:pointer;}
.btn:hover{background:#1e293b;}
.btn:disabled{opacity:0.5;cursor:not-allowed;}
.btn-green{background:#10b981;}.btn-green:hover{background:#059669;}
.btn-blue{background:#3b82f6;}.btn-blue:hover{background:#2563eb;}
.btn-outline{background:white;color:#0f172a;border:1px solid #e5e7eb;}.btn-outline:hover{background:#f8fafc;}
canvas{display:block;width:100%;border-radius:12px;border:1px solid #e5e7eb;background:#0f172a;margin-bottom:14px;}
.temp-wrap{background:white;border-radius:12px;border:1px solid #e5e7eb;padding:12px 16px;margin-bottom:14px;display:none;}
.temp-wrap.show{display:block;}
.temp-label{display:flex;justify-content:space-between;font-size:10px;color:#6b7280;margin-bottom:5px;}
.temp-bar-bg{height:8px;background:#f1f5f9;border-radius:4px;overflow:hidden;}
.temp-bar{height:8px;border-radius:4px;transition:width 1s ease;background:linear-gradient(90deg,#3b82f6,#ef4444);}
.temp-marker{text-align:center;font-size:10px;font-weight:600;margin-top:3px;}
.vote-wrap{background:white;border-radius:12px;border:1px solid #e5e7eb;padding:12px 16px;margin-bottom:14px;display:none;}
.vote-wrap.show{display:block;}
.vote-title{font-size:11px;font-weight:600;color:#6b7280;margin-bottom:8px;}
.vote-bar-bg{height:24px;background:#fee2e2;border-radius:6px;overflow:hidden;margin-bottom:4px;}
.vote-bar{height:24px;background:#10b981;border-radius:6px;transition:width 0.8s ease;display:flex;align-items:center;padding-left:8px;font-size:11px;color:white;font-weight:600;}
.vote-result{font-size:12px;font-weight:600;text-align:center;}
.round-badge{background:#0f172a;color:white;border-radius:20px;padding:2px 9px;font-size:9px;font-weight:600;margin-bottom:6px;display:inline-block;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px;}
.card{background:white;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;}
.card-title{font-size:11px;font-weight:600;color:#6b7280;padding:10px 14px;border-bottom:1px solid #e5e7eb;text-transform:uppercase;letter-spacing:0.5px;}
.convo{height:380px;overflow-y:auto;padding:10px;}
.msg{margin-bottom:10px;animation:fadeIn 0.3s ease;}
@keyframes fadeIn{from{opacity:0;transform:translateY(3px)}to{opacity:1}}
.msg-head{display:flex;align-items:center;gap:5px;margin-bottom:3px;}
.msg-avatar{width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:7px;font-weight:600;}
.msg-name{font-size:10px;font-weight:600;}
.msg-tag{font-size:8px;padding:1px 5px;border-radius:20px;background:#f1f5f9;color:#6b7280;margin-left:3px;}
.msg-tag.찬성{background:#d1fae5;color:#065f46;}
.msg-tag.반대{background:#fee2e2;color:#991b1b;}
.msg-body{font-size:11px;color:#374151;line-height:1.7;margin-left:23px;background:#f8fafc;border-radius:0 7px 7px 7px;padding:6px 9px;}
.report-wrap{height:380px;overflow-y:auto;padding:14px;}
.report-content{font-size:11px;line-height:1.9;color:#374151;white-space:pre-wrap;}
.feedback-box{background:white;border-radius:12px;border:1px solid #3b82f6;padding:14px;margin-bottom:14px;display:none;}
.feedback-box.show{display:block;}
.feedback-q{font-size:12px;font-weight:500;color:#1d4ed8;margin-bottom:8px;}
.feedback-row{display:flex;gap:8px;}
.feedback-row input{flex:1;padding:7px 11px;border:1px solid #e5e7eb;border-radius:8px;font-size:12px;outline:none;}
.action-row{display:none;gap:8px;margin-bottom:14px;}
.action-row.show{display:flex;}
.code-box{background:white;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;margin-bottom:14px;display:none;}
.code-box.show{display:block;}
.code-header{font-size:11px;font-weight:600;color:#6b7280;padding:10px 14px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;}
.code-box pre{padding:14px;font-size:10px;overflow-x:auto;background:#0f172a;color:#e2e8f0;line-height:1.6;max-height:380px;overflow-y:auto;}
.rejected-box{background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:14px;margin-bottom:14px;display:none;}
.rejected-box.show{display:block;}
.rejected-title{font-size:12px;font-weight:600;color:#dc2626;margin-bottom:3px;}
.rejected-reason{font-size:11px;color:#7f1d1d;}
.hist-panel{background:white;border-radius:12px;border:1px solid #e5e7eb;padding:14px;margin-bottom:14px;display:none;}
.hist-panel.show{display:block;}
.hist-item{padding:9px;border-radius:7px;border:1px solid #e5e7eb;margin-bottom:7px;cursor:pointer;}
.hist-item:hover{background:#f8fafc;}
.hist-topic{font-size:12px;font-weight:500;}
.hist-date{font-size:10px;color:#6b7280;margin-top:1px;}
.empty{display:flex;align-items:center;justify-content:center;height:100%;font-size:11px;color:#9ca3af;text-align:center;padding:16px;}
</style></head>
<body>
<div class="layout">
  <div class="sidebar">
    <div class="sidebar-logo">AI 컴퍼니<span>멀티 에이전트 v3</span></div>
    <div class="agent-list" id="agent-list"></div>
    <button class="hist-btn" onclick="toggleHistory()">히스토리 보기</button>
  </div>
  <div class="main">
    <div class="top">
      <h1>AI 직원팀에게 주제를 던져보세요</h1>
      <div class="input-row">
        <input type="text" id="topic" placeholder="예) 동네 세탁소 AI 자동화 서비스" />
        <button class="btn" id="run-btn" onclick="runAgents()">실행</button>
      </div>
    </div>
    <div class="rejected-box" id="rejected-box">
      <div class="rejected-title">주제 반려됨</div>
      <div class="rejected-reason" id="rejected-reason"></div>
    </div>
    <canvas id="nc" height="200"></canvas>
    <div class="temp-wrap" id="temp-wrap">
      <div class="temp-label"><span>보수적</span><span>공격적</span></div>
      <div class="temp-bar-bg"><div class="temp-bar" id="temp-bar" style="width:50%"></div></div>
      <div class="temp-marker" id="temp-marker">팽팽 (50)</div>
    </div>
    <div class="vote-wrap" id="vote-wrap">
      <div class="vote-title">전체 AI 투표 결과</div>
      <div class="vote-bar-bg"><div class="vote-bar" id="vote-bar" style="width:0%">0명 찬성</div></div>
      <div class="vote-result" id="vote-result"></div>
    </div>
    <div class="grid">
      <div class="card">
        <div class="card-title">실시간 대화</div>
        <div class="convo" id="convo"><div class="empty">실행하면 AI들이 토론을 시작해요</div></div>
      </div>
      <div class="card">
        <div class="card-title">최종 보고서</div>
        <div class="report-wrap" id="report-wrap"><div class="empty">최종검토가 완료되면 보고서가 나와요</div></div>
      </div>
    </div>
    <div class="feedback-box" id="feedback-box">
      <div class="feedback-q" id="feedback-q"></div>
      <div class="feedback-row">
        <input type="text" id="feedback-input" placeholder="피드백을 입력하세요..." />
        <button class="btn btn-blue" onclick="sendFeedback()">반영하기</button>
        <button class="btn btn-outline" onclick="document.getElementById('feedback-box').className='feedback-box'">괜찮아요</button>
      </div>
    </div>
    <div class="action-row" id="action-row">
      <button class="btn btn-green" onclick="generateCode()">코드 짜줘</button>
      <button class="btn btn-outline" onclick="runAgents()">다시 토론</button>
    </div>
    <div class="code-box" id="code-box">
      <div class="code-header">생성된 코드
        <button class="btn btn-outline" style="font-size:10px;padding:3px 9px;" onclick="copyCode()">복사</button>
      </div>
      <pre id="code-content"></pre>
    </div>
    <div class="hist-panel" id="hist-panel">
      <div class="card-title" style="margin-bottom:10px;">이전 토론 기록</div>
      <div id="hist-list"></div>
    </div>
  </div>
</div>
<script>
const AGENTS=[
  {id:"p1",name:"기획자1",role:"불도저",color:"#ef4444",bg:"#FEE2E2",tc:"#991b1b",x:0.07,y:0.3},
  {id:"p2",name:"기획자2",role:"안전제일",color:"#3b82f6",bg:"#DBEAFE",tc:"#1d4ed8",x:0.07,y:0.7},
  {id:"r1",name:"검토자1",role:"분석가",color:"#f59e0b",bg:"#FEF3C7",tc:"#92400e",x:0.27,y:0.25},
  {id:"r2",name:"검토자2",role:"조율자",color:"#f59e0b",bg:"#FEF3C7",tc:"#92400e",x:0.27,y:0.75},
  {id:"d1",name:"개발자1",role:"백엔드",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.18},
  {id:"d2",name:"개발자2",role:"풀스택",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.5},
  {id:"d3",name:"개발자3",role:"DB",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.82},
  {id:"t1",name:"테스터1",role:"QA",color:"#ec4899",bg:"#FCE7F3",tc:"#9d174d",x:0.74,y:0.3},
  {id:"t2",name:"테스터2",role:"악마변호인",color:"#7c3aed",bg:"#EDE9FE",tc:"#4c1d95",x:0.74,y:0.7},
  {id:"fin",name:"최종검토",role:"보고",color:"#a855f7",bg:"#EDE9FE",tc:"#6b21a8",x:0.93,y:0.5},
];
const EDGES=[["p1","p2"],["p1","r1"],["p1","r2"],["p2","r1"],["p2","r2"],["r1","d1"],["r1","d2"],["r2","d2"],["r2","d3"],["d1","t1"],["d2","t1"],["d2","t2"],["d3","t2"],["t1","fin"],["t2","fin"]];
const aMap={};AGENTS.forEach(a=>aMap[a.id]=a);
const glows={};AGENTS.forEach(a=>glows[a.id]=0);
const states={};AGENTS.forEach(a=>states[a.id]="idle");
const pulses=[];
const canvas=document.getElementById("nc");
const ctx=canvas.getContext("2d");
function resize(){canvas.width=canvas.offsetWidth;canvas.height=200;}
resize();window.addEventListener("resize",resize);
function px(a){return{x:a.x*canvas.width,y:a.y*canvas.height};}
function frame(){
  ctx.fillStyle="#0f172a";ctx.fillRect(0,0,canvas.width,canvas.height);
  EDGES.forEach(([a,b])=>{
    const na=px(aMap[a]),nb=px(aMap[b]);
    ctx.beginPath();ctx.moveTo(na.x,na.y);ctx.lineTo(nb.x,nb.y);
    ctx.strokeStyle="rgba(255,255,255,0.06)";ctx.lineWidth=0.8;ctx.stroke();
  });
  for(let i=pulses.length-1;i>=0;i--){
    const p=pulses[i];
    const na=px(aMap[p.from]),nb=px(aMap[p.to]);
    const x=na.x+(nb.x-na.x)*p.t,y=na.y+(nb.y-na.y)*p.t;
    ctx.globalAlpha=0.9-p.t*0.4;
    ctx.beginPath();ctx.arc(x,y,4,0,Math.PI*2);ctx.fillStyle=p.color;ctx.fill();
    ctx.globalAlpha=0.2;ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.fillStyle=p.color;ctx.fill();
    ctx.globalAlpha=1;p.t+=0.015;if(p.t>=1)pulses.splice(i,1);
  }
  AGENTS.forEach(a=>{
    const{x,y}=px(a);const r=13;const g=glows[a.id]||0;
    if(g>0){
      const gr=ctx.createRadialGradient(x,y,r,x,y,r*3.5);
      gr.addColorStop(0,a.color+Math.round(g*150).toString(16).padStart(2,"0"));
      gr.addColorStop(1,a.color+"00");
      ctx.beginPath();ctx.arc(x,y,r*3.5,0,Math.PI*2);ctx.fillStyle=gr;ctx.fill();
    }
    ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);
    const st=states[a.id];
    ctx.fillStyle=st==="idle"?"#1e293b":st==="thinking"?a.color+"44":a.color+"55";
    ctx.fill();
    ctx.strokeStyle=g>0.4?a.color:"rgba(255,255,255,0.15)";ctx.lineWidth=g>0.4?1.5:0.5;ctx.stroke();
    ctx.fillStyle=g>0.3?a.color:"rgba(255,255,255,0.5)";
    ctx.font="bold 7px sans-serif";ctx.textAlign="center";ctx.textBaseline="middle";
    ctx.fillText(a.name,x,y-2);
    ctx.font="6px sans-serif";ctx.fillStyle="rgba(255,255,255,0.3)";
    ctx.fillText(a.role,x,y+6);
  });
  requestAnimationFrame(frame);
}
frame();
function addPulse(from,to){if(aMap[from]&&aMap[to])pulses.push({from,to,color:aMap[from].color,t:0});}
const pulseMap={p1:["p2","r1","r2"],p2:["r1","r2"],r1:["d1","d2"],r2:["d2","d3"],d1:["t1"],d2:["t1","t2"],d3:["t2"],t1:["fin"],t2:["fin"]};
function buildSidebar(){
  document.getElementById("agent-list").innerHTML=AGENTS.map(a=>`
    <div class="agent-item" id="ai-${a.id}">
      <div class="a-avatar" style="background:${a.bg};color:${a.tc};">${a.name.slice(0,2)}</div>
      <div class="a-info"><div class="a-name">${a.name} <span style="font-size:8px;color:#475569;">${a.role}</span></div><div class="a-status" id="ast-${a.id}">대기중</div></div>
      <div class="a-dot" id="dot-${a.id}"></div>
    </div>`).join("");
}
buildSidebar();
function setAgent(id,state,text){
  const item=document.getElementById("ai-"+id);
  const st=document.getElementById("ast-"+id);
  const dot=document.getElementById("dot-"+id);
  if(item)item.className="agent-item "+(state==="thinking"?"thinking":state==="done"?"done":"");
  if(st)st.textContent=text||"대기중";
  if(dot)dot.className="a-dot "+(state==="thinking"?"thinking":state==="done"?"done":"");
  states[id]=state;glows[id]=state==="thinking"?0.8:state==="done"?0.3:0;
}
function addMsg(id,text,tag){
  const a=aMap[id];if(!a)return;
  const convo=document.getElementById("convo");
  const empty=convo.querySelector(".empty");if(empty)empty.remove();
  const d=document.createElement("div");d.className="msg";
  const tagClass=tag==="찬성"?"찬성":tag==="반대"?"반대":"";
  d.innerHTML=`<div class="msg-head"><div class="msg-avatar" style="background:${a.bg};color:${a.tc};">${a.name.slice(0,2)}</div><span class="msg-name" style="color:${a.color}">${a.name}</span>${tag?`<span class="msg-tag ${tagClass}">${tag}</span>`:""}</div><div class="msg-body">${text}</div>`;
  convo.appendChild(d);
}
function addRound(text){
  const convo=document.getElementById("convo");
  const d=document.createElement("div");d.style.margin="6px 0";
  d.innerHTML=`<span class="round-badge">${text}</span>`;
  convo.appendChild(d);convo.scrollTop=convo.scrollHeight;
}
function setTemp(val){
  document.getElementById("temp-wrap").className="temp-wrap show";
  document.getElementById("temp-bar").style.width=val+"%";
  const label=val<35?"보수 우세":val>65?"공격 우세":"팽팽";
  document.getElementById("temp-marker").textContent=`${label} (${val})`;
}
function setVote(yes,total){
  document.getElementById("vote-wrap").className="vote-wrap show";
  const pct=Math.round(yes/total*100);
  document.getElementById("vote-bar").style.width=pct+"%";
  document.getElementById("vote-bar").textContent=`${yes}명 찬성`;
  document.getElementById("vote-result").textContent=`${yes}/${total} 찬성 (${pct}%) — ${pct>=60?"통과":"부결"}`;
  document.getElementById("vote-result").style.color=pct>=60?"#10b981":"#ef4444";
}
function listenSSE(url,onDone){
  const es=new EventSource(url);
  es.addEventListener("status",e=>{
    const d=JSON.parse(e.data);
    setAgent(d.id,d.state,d.text);
    if(pulseMap[d.id]&&d.state==="thinking") pulseMap[d.id].forEach(to=>addPulse(d.id,to));
  });
  es.addEventListener("msg",e=>{const d=JSON.parse(e.data);addMsg(d.id,d.text,d.tag);});
  es.addEventListener("round",e=>{const d=JSON.parse(e.data);addRound(d.text);});
  es.addEventListener("temperature",e=>{const d=JSON.parse(e.data);setTemp(d.value);});
  es.addEventListener("vote_result",e=>{const d=JSON.parse(e.data);setVote(d.yes,d.total);});
  es.addEventListener("report",e=>{
    const d=JSON.parse(e.data);
    document.getElementById("report-wrap").innerHTML=`<div class="report-content">${d.text}</div>`;
  });
  es.addEventListener("rejected",e=>{
    const d=JSON.parse(e.data);
    document.getElementById("rejected-reason").textContent=d.reason;
    document.getElementById("rejected-box").className="rejected-box show";
  });
  es.addEventListener("feedback_question",e=>{
    const d=JSON.parse(e.data);
    document.getElementById("feedback-q").textContent=d.text;
    document.getElementById("feedback-box").className="feedback-box show";
  });
  es.addEventListener("code",e=>{
    const d=JSON.parse(e.data);
    document.getElementById("code-content").textContent=d.text;
    document.getElementById("code-box").className="code-box show";
  });
  es.addEventListener("done",e=>{
  es.close();
  if(onDone)onDone();
});
es.onerror=function(){es.close();};
}
function runAgents(){
  const topic=document.getElementById("topic").value.trim();
  if(!topic)return;
  document.getElementById("run-btn").disabled=true;
  document.getElementById("feedback-box").className="feedback-box";
  document.getElementById("action-row").className="action-row";
  document.getElementById("code-box").className="code-box";
  document.getElementById("rejected-box").className="rejected-box";
  document.getElementById("temp-wrap").className="temp-wrap";
  document.getElementById("vote-wrap").className="vote-wrap";
  document.getElementById("convo").innerHTML="";
  document.getElementById("report-wrap").innerHTML='<div class="empty">작성 중...</div>';
  AGENTS.forEach(a=>setAgent(a.id,"idle","대기중"));
  listenSSE("/run?topic="+encodeURIComponent(topic),()=>{
    document.getElementById("run-btn").disabled=false;
    document.getElementById("action-row").className="action-row show";
  });
}
function sendFeedback(){
  const fb=document.getElementById("feedback-input").value.trim();
  if(!fb)return;
  document.getElementById("feedback-box").className="feedback-box";
  document.getElementById("convo").innerHTML="";
  AGENTS.forEach(a=>setAgent(a.id,"idle","대기중"));
  listenSSE("/feedback?feedback="+encodeURIComponent(fb),()=>{
    document.getElementById("action-row").className="action-row show";
  });
}
function generateCode(){
  const topic=document.getElementById("topic").value.trim();
  AGENTS.forEach(a=>setAgent(a.id,"idle","대기중"));
  listenSSE("/generate-code?topic="+encodeURIComponent(topic),()=>{});
}
function copyCode(){
  navigator.clipboard.writeText(document.getElementById("code-content").textContent)
    .then(()=>alert("복사됐어요!"));
}
function toggleHistory(){
  const panel=document.getElementById("hist-panel");
  if(panel.classList.contains("show")){panel.className="hist-panel";return;}
  fetch("/history").then(r=>r.json()).then(data=>{
    const list=document.getElementById("hist-list");
    if(!data.length){list.innerHTML='<p style="font-size:11px;color:#9ca3af;">아직 기록이 없어요</p>';panel.className="hist-panel show";return;}
    list.innerHTML=data.map(d=>`
      <div class="hist-item" onclick="loadHistory(${JSON.stringify(d.report).replace(/'/g,"\\'")}, '${d.topic}')">
        <div class="hist-topic">${d.topic}</div>
        <div class="hist-date">${d.created_at}</div>
      </div>`).join("");
    panel.className="hist-panel show";
  });
}
function loadHistory(report,topic){
  document.getElementById("report-wrap").innerHTML=`<div class="report-content">${report}</div>`;
  document.getElementById("topic").value=topic;
  document.getElementById("hist-panel").className="hist-panel";
}
</script>
</body></html>'''

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port,debug=True)