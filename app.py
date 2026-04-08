from flask import Flask, render_template_string, request, Response, stream_with_context, jsonify
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
    return jsonify([{"id": d.id, "topic": d.topic, "created_at": d.created_at.strftime("%Y-%m-%d %H:%M"), "report": d.report} for d in discussions])

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

        # 기획자1 — 공격적
        yield send("status", {"id": "p1", "state": "thinking", "text": "공격안 구상 중..."})
        r = ask(
            "당신은 공격적 성향의 스타트업 기획자입니다. 별명은 '불도저'예요. 리스크를 감수하고 크고 빠르게 가는 방향을 제안하세요. 시장 선점, 빠른 확장, 대담한 MVP를 강조하세요. 2-3문장으로.",
            f"주제: {topic}"
        )
        results["p1"] = r
        yield send("msg", {"id": "p1", "text": r, "tag": "공격안"})
        yield send("status", {"id": "p1", "state": "done", "text": "공격안 완료"})

        # 기획자2 — 보수적
        yield send("status", {"id": "p2", "state": "thinking", "text": "보수안 구상 중..."})
        r = ask(
            "당신은 보수적 성향의 스타트업 기획자입니다. 별명은 '안전제일'이에요. 검증하고 단계적으로 가는 방향을 제안하세요. 리스크 최소화, 작게 시작해서 검증하는 방식을 강조하세요. 2-3문장으로.",
            f"주제: {topic}\n공격안 참고: {results['p1']}"
        )
        results["p2"] = r
        yield send("msg", {"id": "p2", "text": r, "tag": "보수안"})
        yield send("status", {"id": "p2", "state": "done", "text": "보수안 완료"})

        # 1라운드 토론 — 기획자1이 기획자2 반박
        yield send("round", {"round": 1, "text": "1라운드 — 기획자 맞토론"})
        yield send("status", {"id": "p1", "state": "thinking", "text": "반박 중..."})
        r = ask(
            "당신은 공격적 기획자 '불도저'입니다. 보수적 동료의 의견에 반박하세요. 왜 빠르게 가야 하는지 구체적 근거를 들어 설득하세요. 2문장으로.",
            f"주제: {topic}\n보수안: {results['p2']}"
        )
        results["p1_rebuttal"] = r
        yield send("msg", {"id": "p1", "text": r, "tag": "반박"})
        yield send("status", {"id": "p1", "state": "done", "text": "반박 완료"})

        # 기획자2 재반박
        yield send("status", {"id": "p2", "state": "thinking", "text": "재반박 중..."})
        r = ask(
            "당신은 보수적 기획자 '안전제일'입니다. 공격적 동료의 반박에 맞서세요. 왜 신중하게 가야 하는지 구체적 근거를 들어 설득하세요. 2문장으로.",
            f"주제: {topic}\n공격적 반박: {results['p1_rebuttal']}"
        )
        results["p2_rebuttal"] = r
        yield send("msg", {"id": "p2", "text": r, "tag": "재반박"})
        yield send("status", {"id": "p2", "state": "done", "text": "재반박 완료"})

        # 토론 온도 측정
        temp = ask(
            "당신은 토론 분석가입니다. 공격안과 보수안 중 어느 쪽이 더 설득력 있는지 0~100 숫자 하나만 답하세요. 0=완전 보수, 100=완전 공격, 50=팽팽.",
            f"공격안: {results['p1']}\n보수안: {results['p2']}\n공격 반박: {results['p1_rebuttal']}\n보수 재반박: {results['p2_rebuttal']}"
        )
        try:
            temp_val = int(''.join(filter(str.isdigit, temp)))
            temp_val = max(0, min(100, temp_val))
        except:
            temp_val = 50
        yield send("temperature", {"value": temp_val})

        # 검토자1 — 비교 분석
        yield send("status", {"id": "r1", "state": "thinking", "text": "양측 분석 중..."})
        r = ask(
            "당신은 냉철한 전략 분석가입니다. 공격안과 보수안을 비교 분석하고 각각의 장단점을 명확히 짚으세요. 만약 두 안 모두 심각한 문제가 있으면 '재검토 필요'를 명시하세요. 3-4문장으로.",
            f"주제: {topic}\n공격안: {results['p1']}\n보수안: {results['p2']}\n토론: {results['p1_rebuttal']} / {results['p2_rebuttal']}"
        )
        results["r1"] = r
        yield send("msg", {"id": "r1", "text": r, "tag": "비교분석"})
        yield send("status", {"id": "r1", "state": "done", "text": "분석 완료"})

        # 검토자2 — 최적안 조합
        yield send("status", {"id": "r2", "state": "thinking", "text": "최적안 조합 중..."})
        r = ask(
            "당신은 의사결정 전문가입니다. 공격안 장점 + 보수안 장점을 합치고 단점은 제거해서 최적안을 만드세요. 조합이 불가능하면 기획자들에게 재검토를 요청하세요. 3-4문장으로.",
            f"주제: {topic}\n공격안: {results['p1']}\n보수안: {results['p2']}\n분석: {results['r1']}"
        )
        results["r2"] = r
        needs_redo = "재검토" in results["r1"] or "재검토" in r
        yield send("msg", {"id": "r2", "text": r, "tag": "최적안"})
        yield send("status", {"id": "r2", "state": "done", "text": "최적안 도출"})

        if needs_redo:
            yield send("round", {"round": 2, "text": "2라운드 — 재검토 요청"})
            yield send("status", {"id": "p1", "state": "thinking", "text": "재검토 중..."})
            r = ask(
                "당신은 공격적 기획자입니다. 검토자 피드백을 반영해 공격안을 수정하세요. 2-3문장으로.",
                f"주제: {topic}\n기존안: {results['p1']}\n피드백: {results['r2']}"
            )
            results["p1"] = r
            yield send("msg", {"id": "p1", "text": r, "tag": "수정 공격안"})
            yield send("status", {"id": "p1", "state": "done", "text": "수정 완료"})

            yield send("status", {"id": "p2", "state": "thinking", "text": "재검토 중..."})
            r = ask(
                "당신은 보수적 기획자입니다. 검토자 피드백을 반영해 보수안을 수정하세요. 2-3문장으로.",
                f"주제: {topic}\n기존안: {results['p2']}\n피드백: {results['r2']}"
            )
            results["p2"] = r
            yield send("msg", {"id": "p2", "text": r, "tag": "수정 보수안"})
            yield send("status", {"id": "p2", "state": "done", "text": "수정 완료"})

            yield send("status", {"id": "r2", "state": "thinking", "text": "최적안 재조합 중..."})
            r = ask(
                "수정된 두 기획안을 바탕으로 최적안을 도출하세요. 3-4문장으로.",
                f"주제: {topic}\n수정 공격안: {results['p1']}\n수정 보수안: {results['p2']}"
            )
            results["r2"] = r
            yield send("msg", {"id": "r2", "text": r, "tag": "최종 최적안"})
            yield send("status", {"id": "r2", "state": "done", "text": "최적안 확정"})

        # 개발자들
        yield send("status", {"id": "d1", "state": "thinking", "text": "기술 스택 검토 중..."})
        r = ask("당신은 시니어 백엔드 개발자입니다. 최적안 구현에 적합한 기술 스택을 추천하세요. 2-3문장으로.",
                f"주제: {topic}\n최적안: {results['r2']}")
        results["d1"] = r
        yield send("msg", {"id": "d1", "text": r, "tag": "기술스택"})
        yield send("status", {"id": "d1", "state": "done", "text": "완료"})

        yield send("status", {"id": "d2", "state": "thinking", "text": "개발 일정 산정 중..."})
        r = ask("당신은 풀스택 개발자입니다. MVP 개발 기간과 주요 단계를 2-3문장으로 제시하세요.",
                f"주제: {topic}\n최적안: {results['r2']}\n기술: {results['d1']}")
        results["d2"] = r
        yield send("msg", {"id": "d2", "text": r, "tag": "개발일정"})
        yield send("status", {"id": "d2", "state": "done", "text": "완료"})

        yield send("status", {"id": "d3", "state": "thinking", "text": "DB 설계 중..."})
        r = ask("당신은 DB 전문가입니다. 핵심 데이터 구조와 DB 설계 방향을 2-3문장으로 제시하세요.",
                f"주제: {topic}\n기술: {results['d1']}")
        results["d3"] = r
        yield send("msg", {"id": "d3", "text": r, "tag": "DB설계"})
        yield send("status", {"id": "d3", "state": "done", "text": "완료"})

        # 테스터들
        yield send("status", {"id": "t1", "state": "thinking", "text": "QA 기준 수립 중..."})
        r = ask("당신은 QA 엔지니어입니다. 핵심 테스트 항목과 품질 기준을 2-3문장으로 제시하세요.",
                f"주제: {topic}\n기술: {results['d1']}\n일정: {results['d2']}")
        results["t1"] = r
        yield send("msg", {"id": "t1", "text": r, "tag": "QA"})
        yield send("status", {"id": "t1", "state": "done", "text": "완료"})

        yield send("status", {"id": "t2", "state": "thinking", "text": "UX 검토 중..."})
        r = ask("당신은 UX 테스터입니다. 사용성 관점 주의사항과 개선 방향을 2-3문장으로 제시하세요.",
                f"주제: {topic}\n최적안: {results['r2']}\nQA: {results['t1']}")
        results["t2"] = r
        yield send("msg", {"id": "t2", "text": r, "tag": "UX"})
        yield send("status", {"id": "t2", "state": "done", "text": "완료"})

        # 최종검토
        yield send("status", {"id": "fin", "state": "thinking", "text": "최종 보고서 작성 중..."})
        r = ask(
            "당신은 최종 보고 담당자입니다. 팀 전체 논의를 취합해 대표에게 보고하세요.\n형식:\n[핵심 아이디어]\n[공격안 vs 보수안 핵심 차이]\n[최적안 — 두 안의 장점 결합]\n[MVP 기능 3가지]\n[기술 스택]\n[개발 일정]\n[리스크 대응]\n[최종 결론]",
            f"주제: {topic}\n공격안: {results['p1']}\n보수안: {results['p2']}\n최적안: {results['r2']}\n기술: {results['d1']}\n일정: {results['d2']}\nDB: {results['d3']}\nQA: {results['t1']}\nUX: {results['t2']}"
        )
        results["fin"] = r
        last_results = results.copy()

        # DB 저장
        with app.app_context():
            d = Discussion(topic=topic, report=r)
            db.session.add(d)
            db.session.commit()

        yield send("msg", {"id": "fin", "text": r, "tag": "최종보고"})
        yield send("status", {"id": "fin", "state": "done", "text": "보고 완료"})
        yield send("report", {"text": r, "topic": topic})

        feedback_q = ask(
            "당신은 프로젝트 매니저입니다. 보고서 전달 후 대표에게 방향성 확인을 위한 짧은 질문 하나만 하세요.",
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
            "당신은 공격적 기획자입니다. 대표 피드백을 반영해 공격안을 수정하세요. 2-3문장으로.",
            f"주제: {topic}\n기존안: {last_results.get('p1','')}\n피드백: {user_feedback}"
        )
        yield send("msg", {"id": "p1", "text": r, "tag": "수정 공격안"})
        yield send("status", {"id": "p1", "state": "done", "text": "수정 완료"})

        yield send("status", {"id": "p2", "state": "thinking", "text": "피드백 반영 중..."})
        r2 = ask(
            "당신은 보수적 기획자입니다. 대표 피드백을 반영해 보수안을 수정하세요. 2-3문장으로.",
            f"주제: {topic}\n기존안: {last_results.get('p2','')}\n피드백: {user_feedback}"
        )
        yield send("msg", {"id": "p2", "text": r2, "tag": "수정 보수안"})
        yield send("status", {"id": "p2", "state": "done", "text": "수정 완료"})

        yield send("status", {"id": "fin", "state": "thinking", "text": "수정 보고서 작성 중..."})
        fin = ask(
            "대표 피드백이 반영된 수정 보고서를 작성하세요.\n형식:\n[수정된 핵심 아이디어]\n[변경 사항]\n[최종 결론]",
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
            "당신은 시니어 풀스택 개발자입니다. Python Flask로 실제 실행 가능한 MVP 코드를 작성하세요. SQLite DB 포함. app.py 전체 코드만 주세요.",
            f"주제: {topic}\n기획: {last_results.get('r2','')}\n기술스택: {last_results.get('d1','')}\nDB: {last_results.get('d3','')}"
        )
        yield send("status", {"id": "d1", "state": "done", "text": "완료"})
        yield send("status", {"id": "d2", "state": "done", "text": "완료"})
        yield send("status", {"id": "d3", "state": "done", "text": "완료"})
        yield send("code", {"text": code})
        yield send("done", {})

    return Response(stream_with_context(generate()), mimetype="text/event-stream")

HTML = '''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8"><title>AI 컴퍼니</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:-apple-system,sans-serif;background:#f5f7fa;color:#1a1a2e;}
.layout{display:flex;min-height:100vh;}
.sidebar{width:210px;background:#0f172a;padding:20px 0;flex-shrink:0;position:fixed;height:100vh;overflow-y:auto;}
.sidebar-logo{color:white;font-size:14px;font-weight:600;padding:0 16px 16px;border-bottom:1px solid rgba(255,255,255,0.1);}
.sidebar-logo span{font-size:10px;color:#94a3b8;display:block;margin-top:2px;}
.agent-list{padding:12px 8px;}
.agent-item{display:flex;align-items:center;gap:8px;padding:7px 8px;border-radius:8px;margin-bottom:3px;transition:background 0.2s;}
.agent-item.thinking{background:rgba(245,158,11,0.15);}
.agent-item.done{background:rgba(16,185,129,0.12);}
.a-avatar{width:24px;height:24px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:600;flex-shrink:0;}
.a-info{flex:1;min-width:0;}
.a-name{font-size:11px;font-weight:500;color:#e2e8f0;}
.a-status{font-size:10px;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.a-dot{width:6px;height:6px;border-radius:50%;background:#334155;flex-shrink:0;}
.a-dot.thinking{background:#f59e0b;animation:blink 0.8s infinite;}
.a-dot.done{background:#10b981;}
.hist-btn{margin:8px;padding:7px 10px;background:rgba(255,255,255,0.05);border:0.5px solid rgba(255,255,255,0.1);border-radius:8px;color:#94a3b8;font-size:11px;cursor:pointer;width:calc(100% - 16px);text-align:left;}
.hist-btn:hover{background:rgba(255,255,255,0.1);color:white;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.main{flex:1;margin-left:210px;padding:24px;}
.top{background:white;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid #e5e7eb;}
.top h1{font-size:16px;font-weight:600;margin-bottom:12px;}
.input-row{display:flex;gap:8px;}
.input-row input{flex:1;padding:9px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;outline:none;}
.input-row input:focus{border-color:#0f172a;}
.btn{padding:9px 20px;background:#0f172a;color:white;border:none;border-radius:8px;font-size:13px;cursor:pointer;}
.btn:hover{background:#1e293b;}
.btn:disabled{opacity:0.5;cursor:not-allowed;}
.btn-green{background:#10b981;}.btn-green:hover{background:#059669;}
.btn-blue{background:#3b82f6;}.btn-blue:hover{background:#2563eb;}
.btn-outline{background:white;color:#0f172a;border:1px solid #e5e7eb;}.btn-outline:hover{background:#f8fafc;}
canvas{display:block;width:100%;border-radius:12px;border:1px solid #e5e7eb;background:#0f172a;margin-bottom:16px;}
.temp-wrap{background:white;border-radius:12px;border:1px solid #e5e7eb;padding:14px 16px;margin-bottom:16px;display:none;}
.temp-wrap.show{display:block;}
.temp-label{display:flex;justify-content:space-between;font-size:11px;color:#6b7280;margin-bottom:6px;}
.temp-bar-bg{height:10px;background:#f1f5f9;border-radius:5px;overflow:hidden;}
.temp-bar{height:10px;border-radius:5px;transition:width 1s ease;background:linear-gradient(90deg,#3b82f6,#ef4444);}
.temp-marker{text-align:center;font-size:11px;font-weight:600;margin-top:4px;}
.round-badge{background:#0f172a;color:white;border-radius:20px;padding:3px 10px;font-size:10px;font-weight:600;margin-bottom:8px;display:inline-block;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.card{background:white;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;}
.card-title{font-size:12px;font-weight:600;color:#6b7280;padding:12px 16px;border-bottom:1px solid #e5e7eb;text-transform:uppercase;letter-spacing:0.5px;}
.convo{height:340px;overflow-y:auto;padding:12px;}
.msg{margin-bottom:12px;animation:fadeIn 0.3s ease;}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1}}
.msg-head{display:flex;align-items:center;gap:6px;margin-bottom:4px;}
.msg-avatar{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:600;}
.msg-name{font-size:11px;font-weight:600;}
.msg-tag{font-size:9px;padding:1px 6px;border-radius:20px;background:#f1f5f9;color:#6b7280;margin-left:4px;}
.msg-body{font-size:12px;color:#374151;line-height:1.7;margin-left:26px;background:#f8fafc;border-radius:0 8px 8px 8px;padding:8px 10px;}
.report-wrap{height:340px;overflow-y:auto;padding:16px;}
.report-content{font-size:12px;line-height:1.9;color:#374151;white-space:pre-wrap;}
.feedback-box{background:white;border-radius:12px;border:1px solid #3b82f6;padding:16px;margin-bottom:16px;display:none;}
.feedback-box.show{display:block;}
.feedback-q{font-size:13px;font-weight:500;color:#1d4ed8;margin-bottom:10px;}
.feedback-row{display:flex;gap:8px;}
.feedback-row input{flex:1;padding:8px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;outline:none;}
.action-row{display:none;gap:8px;margin-bottom:16px;}
.action-row.show{display:flex;}
.code-box{background:white;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;margin-bottom:16px;display:none;}
.code-box.show{display:block;}
.code-header{font-size:12px;font-weight:600;color:#6b7280;padding:12px 16px;border-bottom:1px solid #e5e7eb;display:flex;align-items:center;justify-content:space-between;}
.code-box pre{padding:16px;font-size:11px;overflow-x:auto;background:#0f172a;color:#e2e8f0;line-height:1.6;max-height:400px;overflow-y:auto;}
.rejected-box{background:#fef2f2;border:1px solid #fecaca;border-radius:12px;padding:16px;margin-bottom:16px;display:none;}
.rejected-box.show{display:block;}
.rejected-title{font-size:13px;font-weight:600;color:#dc2626;margin-bottom:4px;}
.rejected-reason{font-size:12px;color:#7f1d1d;}
.hist-panel{background:white;border-radius:12px;border:1px solid #e5e7eb;padding:16px;margin-bottom:16px;display:none;}
.hist-panel.show{display:block;}
.hist-item{padding:10px;border-radius:8px;border:1px solid #e5e7eb;margin-bottom:8px;cursor:pointer;}
.hist-item:hover{background:#f8fafc;}
.hist-topic{font-size:13px;font-weight:500;}
.hist-date{font-size:11px;color:#6b7280;margin-top:2px;}
.empty{display:flex;align-items:center;justify-content:center;height:100%;font-size:12px;color:#9ca3af;text-align:center;padding:20px;}
</style></head>
<body>
<div class="layout">
  <div class="sidebar">
    <div class="sidebar-logo">AI 컴퍼니<span>멀티 에이전트 v2</span></div>
    <div class="agent-list" id="agent-list"></div>
    <button class="hist-btn" onclick="toggleHistory()">히스토리 보기</button>
  </div>
  <div class="main">
    <div class="top">
      <h1>AI 직원팀에게 주제를 던져보세요</h1>
      <div class="input-row">
        <input type="text" id="topic" placeholder="예) 중소기업용 재고관리 SaaS 만들기" />
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
        <button class="btn btn-outline" style="font-size:11px;padding:4px 10px;" onclick="copyCode()">복사</button>
      </div>
      <pre id="code-content"></pre>
    </div>

    <div class="hist-panel" id="hist-panel">
      <div class="card-title" style="margin-bottom:12px;">이전 토론 기록</div>
      <div id="hist-list"></div>
    </div>
  </div>
</div>
<script>
const AGENTS=[
  {id:"p1",name:"기획자1",role:"불도저",color:"#ef4444",bg:"#FEE2E2",tc:"#991b1b",x:0.08,y:0.35},
  {id:"p2",name:"기획자2",role:"안전제일",color:"#3b82f6",bg:"#DBEAFE",tc:"#1d4ed8",x:0.08,y:0.65},
  {id:"r1",name:"검토자1",role:"분석가",color:"#f59e0b",bg:"#FEF3C7",tc:"#92400e",x:0.28,y:0.25},
  {id:"r2",name:"검토자2",role:"조율자",color:"#f59e0b",bg:"#FEF3C7",tc:"#92400e",x:0.28,y:0.75},
  {id:"d1",name:"개발자1",role:"백엔드",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.2},
  {id:"d2",name:"개발자2",role:"풀스택",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.5},
  {id:"d3",name:"개발자3",role:"DB",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.8},
  {id:"t1",name:"테스터1",role:"QA",color:"#ec4899",bg:"#FCE7F3",tc:"#9d174d",x:0.74,y:0.3},
  {id:"t2",name:"테스터2",role:"UX",color:"#ec4899",bg:"#FCE7F3",tc:"#9d174d",x:0.74,y:0.7},
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
    const{x,y}=px(a);const r=14;const g=glows[a.id]||0;
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
    ctx.font="bold 8px sans-serif";ctx.textAlign="center";ctx.textBaseline="middle";
    ctx.fillText(a.name,x,y-2);
    ctx.font="7px sans-serif";ctx.fillStyle="rgba(255,255,255,0.3)";
    ctx.fillText(a.role,x,y+7);
  });
  requestAnimationFrame(frame);
}
frame();
function addPulse(from,to){pulses.push({from,to,color:aMap[from]?aMap[from].color:"#fff",t:0});}
const pulseMap={p1:["p2","r1","r2"],p2:["r1","r2"],r1:["d1","d2"],r2:["d2","d3"],d1:["t1"],d2:["t1","t2"],d3:["t2"],t1:["fin"],t2:["fin"]};
function buildSidebar(){
  document.getElementById("agent-list").innerHTML=AGENTS.map(a=>`
    <div class="agent-item" id="ai-${a.id}">
      <div class="a-avatar" style="background:${a.bg};color:${a.tc};">${a.name.slice(0,2)}</div>
      <div class="a-info"><div class="a-name">${a.name} <span style="font-size:9px;color:#475569;">${a.role}</span></div><div class="a-status" id="ast-${a.id}">대기중</div></div>
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
  d.innerHTML=`<div class="msg-head"><div class="msg-avatar" style="background:${a.bg};color:${a.tc};">${a.name.slice(0,2)}</div><span class="msg-name" style="color:${a.color}">${a.name}</span>${tag?`<span class="msg-tag">${tag}</span>`:""}</div><div class="msg-body">${text}</div>`;
  convo.appendChild(d);convo.scrollTop=convo.scrollHeight;
}
function addRound(text){
  const convo=document.getElementById("convo");
  const d=document.createElement("div");d.style.margin="8px 0";
  d.innerHTML=`<span class="round-badge">${text}</span>`;
  convo.appendChild(d);convo.scrollTop=convo.scrollHeight;
}
function setTemp(val){
  const wrap=document.getElementById("temp-wrap");
  const bar=document.getElementById("temp-bar");
  const marker=document.getElementById("temp-marker");
  if(wrap)wrap.className="temp-wrap show";
  if(bar)bar.style.width=val+"%";
  const label=val<30?"보수 우세":val>70?"공격 우세":"팽팽";
  if(marker)marker.textContent=`${label} (${val})`;
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
  es.addEventListener("done",e=>{es.close();if(onDone)onDone();});
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
    if(!data.length){list.innerHTML='<p style="font-size:12px;color:#9ca3af;">아직 기록이 없어요</p>';panel.className="hist-panel show";return;}
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