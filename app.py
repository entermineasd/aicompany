from flask import Flask, render_template_string, request, Response, stream_with_context
from openai import OpenAI
import os
import json

app = Flask(__name__)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

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

@app.route("/run")
def run():
    global last_results, last_topic
    topic = request.args.get("topic", "")
    last_topic = topic
    last_results = {}

    def generate():
        global last_results
        results = {}

        yield send("status", {"id": "p1", "state": "thinking", "text": "아이디어 구상 중..."})
        r = ask("당신은 스타트업 기획자입니다. 핵심 아이디어, 타깃, MVP 범위를 2-3문장으로 제안하세요.", f"주제: {topic}")
        results["p1"] = r
        yield send("msg", {"id": "p1", "text": r})
        yield send("status", {"id": "p1", "state": "done", "text": "완료"})

        yield send("status", {"id": "p2", "state": "thinking", "text": "보완 검토 중..."})
        r = ask("당신은 비판적 기획자입니다. 동료 아이디어의 리스크와 개선점을 2-3문장으로 제시하세요.", f"주제: {topic}\n동료 의견: {results['p1']}")
        results["p2"] = r
        yield send("msg", {"id": "p2", "text": r})
        yield send("status", {"id": "p2", "state": "done", "text": "완료"})

        yield send("status", {"id": "r1", "state": "thinking", "text": "리스크 분석 중..."})
        r = ask("당신은 리스크 관리 전문가입니다. 기술적/비즈니스 리스크와 해결책을 2-3문장으로 분석하세요.", f"주제: {topic}\n기획: {results['p1']}\n보완: {results['p2']}")
        results["r1"] = r
        yield send("msg", {"id": "r1", "text": r})
        yield send("status", {"id": "r1", "state": "done", "text": "완료"})

        yield send("status", {"id": "r2", "state": "thinking", "text": "시장성 분석 중..."})
        r = ask("당신은 시장 분석가입니다. 시장성과 경쟁 환경, 차별화 포인트를 2-3문장으로 분석하세요.", f"주제: {topic}\n기획: {results['p1']}\n보완: {results['p2']}")
        results["r2"] = r
        yield send("msg", {"id": "r2", "text": r})
        yield send("status", {"id": "r2", "state": "done", "text": "완료"})

        yield send("status", {"id": "d1", "state": "thinking", "text": "기술 스택 검토 중..."})
        r = ask("당신은 시니어 백엔드 개발자입니다. 적합한 기술 스택을 추천하고 이유를 2-3문장으로 설명하세요.", f"주제: {topic}\n기획: {results['p1']}\n리스크: {results['r1']}")
        results["d1"] = r
        yield send("msg", {"id": "d1", "text": r})
        yield send("status", {"id": "d1", "state": "done", "text": "완료"})

        yield send("status", {"id": "d2", "state": "thinking", "text": "개발 일정 산정 중..."})
        r = ask("당신은 풀스택 개발자입니다. MVP 개발 기간과 주요 단계를 2-3문장으로 제시하세요.", f"주제: {topic}\n기획: {results['p1']}\n시장성: {results['r2']}")
        results["d2"] = r
        yield send("msg", {"id": "d2", "text": r})
        yield send("status", {"id": "d2", "state": "done", "text": "완료"})

        yield send("status", {"id": "d3", "state": "thinking", "text": "DB 설계 중..."})
        r = ask("당신은 데이터베이스 전문가입니다. 핵심 데이터 구조와 DB 설계 방향을 2-3문장으로 제시하세요.", f"주제: {topic}\n기술스택: {results['d1']}")
        results["d3"] = r
        yield send("msg", {"id": "d3", "text": r})
        yield send("status", {"id": "d3", "state": "done", "text": "완료"})

        yield send("status", {"id": "t1", "state": "thinking", "text": "QA 기준 수립 중..."})
        r = ask("당신은 QA 엔지니어입니다. 핵심 테스트 항목과 품질 기준을 2-3문장으로 제시하세요.", f"주제: {topic}\n기술: {results['d1']}\n일정: {results['d2']}")
        results["t1"] = r
        yield send("msg", {"id": "t1", "text": r})
        yield send("status", {"id": "t1", "state": "done", "text": "완료"})

        yield send("status", {"id": "t2", "state": "thinking", "text": "사용성 검토 중..."})
        r = ask("당신은 UX 테스터입니다. 사용성 관점에서 주의할 점과 개선 방향을 2-3문장으로 제시하세요.", f"주제: {topic}\n기획: {results['p1']}\nQA: {results['t1']}")
        results["t2"] = r
        yield send("msg", {"id": "t2", "text": r})
        yield send("status", {"id": "t2", "state": "done", "text": "완료"})

        yield send("status", {"id": "fin", "state": "thinking", "text": "최종 보고서 작성 중..."})
        r = ask(
            "당신은 최종 보고 담당자입니다. 팀 전체 논의를 취합해 대표에게 보고할 최종 요약을 작성하세요.\n형식:\n[핵심 아이디어]\n[MVP 기능 3가지]\n[기술 스택]\n[개발 일정]\n[리스크 대응]\n[최종 결론]",
            f"주제: {topic}\n기획1: {results['p1']}\n기획2: {results['p2']}\n리스크: {results['r1']}\n시장성: {results['r2']}\n기술: {results['d1']}\n일정: {results['d2']}\nDB: {results['d3']}\nQA: {results['t1']}\nUX: {results['t2']}"
        )
        results["fin"] = r
        last_results = results.copy()
        yield send("msg", {"id": "fin", "text": r})
        yield send("status", {"id": "fin", "state": "done", "text": "보고 완료"})
        yield send("report", {"text": r, "topic": topic})

        feedback_q = ask(
            "당신은 프로젝트 매니저입니다. 보고서를 대표에게 전달한 뒤, 방향성 확인을 위해 짧고 명확한 질문 하나만 하세요.",
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
        yield send("status", {"id": "p2", "state": "thinking", "text": "재검토 중..."})

        r = ask(
            "당신은 스타트업 기획자입니다. 대표의 피드백을 반영해서 기획을 수정하세요. 2-3문장으로.",
            f"원래 주제: {topic}\n기존 기획: {last_results.get('p1','')}\n대표 피드백: {user_feedback}"
        )
        yield send("msg", {"id": "p1", "text": f"[피드백 반영] {r}"})
        yield send("status", {"id": "p1", "state": "done", "text": "수정 완료"})

        fin = ask(
            "당신은 최종 보고 담당자입니다. 피드백이 반영된 수정 보고서를 작성하세요.\n형식:\n[수정된 핵심 아이디어]\n[변경된 MVP 기능]\n[최종 결론]",
            f"주제: {topic}\n피드백: {user_feedback}\n수정 기획: {r}\n기존 보고서: {last_results.get('fin','')}"
        )
        yield send("status", {"id": "fin", "state": "thinking", "text": "수정 보고서 작성 중..."})
        yield send("msg", {"id": "fin", "text": f"[수정 보고서] {fin}"})
        yield send("status", {"id": "fin", "state": "done", "text": "수정 완료"})
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
            "당신은 시니어 풀스택 개발자입니다. Python Flask로 MVP 코드를 작성하세요. app.py 전체 코드를 주세요. OpenAI API는 gpt-4o-mini를 사용하고, SQLite로 DB를 구성하세요. 실제 실행 가능한 완전한 코드를 주세요.",
            f"주제: {topic}\n기획: {last_results.get('p1','')}\n기술스택: {last_results.get('d1','')}\nDB설계: {last_results.get('d3','')}"
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
.sidebar{width:200px;background:#0f172a;padding:20px 0;flex-shrink:0;position:fixed;height:100vh;overflow-y:auto;}
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
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.main{flex:1;margin-left:200px;padding:24px;}
.top{background:white;border-radius:12px;padding:20px;margin-bottom:16px;border:1px solid #e5e7eb;}
.top h1{font-size:16px;font-weight:600;margin-bottom:12px;}
.input-row{display:flex;gap:8px;}
.input-row input{flex:1;padding:9px 12px;border:1px solid #e5e7eb;border-radius:8px;font-size:13px;outline:none;}
.input-row input:focus{border-color:#0f172a;}
.btn{padding:9px 20px;background:#0f172a;color:white;border:none;border-radius:8px;font-size:13px;cursor:pointer;}
.btn:hover{background:#1e293b;}
.btn:disabled{opacity:0.5;cursor:not-allowed;}
.btn-green{background:#10b981;}
.btn-green:hover{background:#059669;}
.btn-blue{background:#3b82f6;}
.btn-blue:hover{background:#2563eb;}
.btn-outline{background:white;color:#0f172a;border:1px solid #e5e7eb;}
.btn-outline:hover{background:#f8fafc;}
canvas{display:block;width:100%;border-radius:12px;border:1px solid #e5e7eb;background:#0f172a;margin-bottom:16px;}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px;}
.card{background:white;border-radius:12px;border:1px solid #e5e7eb;overflow:hidden;}
.card-title{font-size:12px;font-weight:600;color:#6b7280;padding:12px 16px;border-bottom:1px solid #e5e7eb;text-transform:uppercase;letter-spacing:0.5px;}
.convo{height:300px;overflow-y:auto;padding:12px;}
.msg{margin-bottom:12px;animation:fadeIn 0.3s ease;}
@keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1}}
.msg-head{display:flex;align-items:center;gap:6px;margin-bottom:4px;}
.msg-avatar{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:600;}
.msg-name{font-size:11px;font-weight:600;}
.msg-body{font-size:12px;color:#374151;line-height:1.7;margin-left:26px;background:#f8fafc;border-radius:0 8px 8px 8px;padding:8px 10px;}
.report-wrap{height:300px;overflow-y:auto;padding:16px;}
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
.empty{display:flex;align-items:center;justify-content:center;height:100%;font-size:12px;color:#9ca3af;text-align:center;padding:20px;}
</style></head>
<body>
<div class="layout">
  <div class="sidebar">
    <div class="sidebar-logo">AI 컴퍼니<span>멀티 에이전트</span></div>
    <div class="agent-list" id="agent-list"></div>
  </div>
  <div class="main">
    <div class="top">
      <h1>AI 직원팀에게 주제를 던져보세요</h1>
      <div class="input-row">
        <input type="text" id="topic" placeholder="예) 중소기업용 재고관리 SaaS 만들기" />
        <button class="btn" id="run-btn" onclick="runAgents()">실행</button>
      </div>
    </div>
    <canvas id="nc" height="200"></canvas>
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
      <div class="code-header">
        생성된 코드
        <button class="btn btn-outline" style="font-size:11px;padding:4px 10px;" onclick="copyCode()">복사</button>
      </div>
      <pre id="code-content"></pre>
    </div>
  </div>
</div>
<script>
const AGENTS=[
  {id:"p1",name:"기획자1",role:"기획",color:"#3b82f6",bg:"#DBEAFE",tc:"#1d4ed8",x:0.08,y:0.35},
  {id:"p2",name:"기획자2",role:"기획",color:"#3b82f6",bg:"#DBEAFE",tc:"#1d4ed8",x:0.08,y:0.65},
  {id:"r1",name:"검토자1",role:"검토",color:"#f59e0b",bg:"#FEF3C7",tc:"#92400e",x:0.28,y:0.25},
  {id:"r2",name:"검토자2",role:"검토",color:"#f59e0b",bg:"#FEF3C7",tc:"#92400e",x:0.28,y:0.75},
  {id:"d1",name:"개발자1",role:"개발",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.2},
  {id:"d2",name:"개발자2",role:"개발",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.5},
  {id:"d3",name:"개발자3",role:"개발",color:"#10b981",bg:"#D1FAE5",tc:"#065f46",x:0.52,y:0.8},
  {id:"t1",name:"테스터1",role:"테스트",color:"#ec4899",bg:"#FCE7F3",tc:"#9d174d",x:0.74,y:0.3},
  {id:"t2",name:"테스터2",role:"테스트",color:"#ec4899",bg:"#FCE7F3",tc:"#9d174d",x:0.74,y:0.7},
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
    ctx.fillStyle=g>0.3?a.color:"rgba(255,255,255,0.4)";
    ctx.font="bold 8px sans-serif";ctx.textAlign="center";ctx.textBaseline="middle";
    ctx.fillText(a.name,x,y-2);
    ctx.font="7px sans-serif";ctx.fillStyle="rgba(255,255,255,0.25)";
    ctx.fillText(a.role,x,y+7);
  });
  requestAnimationFrame(frame);
}
frame();
function addPulse(from,to){pulses.push({from,to,color:aMap[from].color,t:0});}
const pulseMap={p1:["p2","r1","r2"],p2:["r1","r2"],r1:["d1","d2"],r2:["d2","d3"],d1:["t1"],d2:["t1","t2"],d3:["t2"],t1:["fin"],t2:["fin"]};
function buildSidebar(){
  document.getElementById("agent-list").innerHTML=AGENTS.map(a=>`
    <div class="agent-item" id="ai-${a.id}">
      <div class="a-avatar" style="background:${a.bg};color:${a.tc};">${a.name.slice(0,2)}</div>
      <div class="a-info"><div class="a-name">${a.name}</div><div class="a-status" id="ast-${a.id}">대기중</div></div>
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
function addMsg(id,text){
  const a=aMap[id];if(!a)return;
  const convo=document.getElementById("convo");
  const empty=convo.querySelector(".empty");if(empty)empty.remove();
  const d=document.createElement("div");d.className="msg";
  d.innerHTML=`<div class="msg-head"><div class="msg-avatar" style="background:${a.bg};color:${a.tc};">${a.name.slice(0,2)}</div><span class="msg-name" style="color:${a.color}">${a.name}</span></div><div class="msg-body">${text}</div>`;
  convo.appendChild(d);convo.scrollTop=convo.scrollHeight;
}
function listenSSE(url,onDone){
  const es=new EventSource(url);
  es.addEventListener("status",e=>{
    const d=JSON.parse(e.data);
    setAgent(d.id,d.state,d.text);
    if(pulseMap[d.id]&&d.state==="thinking") pulseMap[d.id].forEach(to=>addPulse(d.id,to));
  });
  es.addEventListener("msg",e=>{const d=JSON.parse(e.data);addMsg(d.id,d.text);});
  es.addEventListener("report",e=>{
    const d=JSON.parse(e.data);
    document.getElementById("report-wrap").innerHTML=`<div class="report-content">${d.text}</div>`;
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
    es.close();if(onDone)onDone();
  });
}
function runAgents(){
  const topic=document.getElementById("topic").value.trim();
  if(!topic)return;
  document.getElementById("run-btn").disabled=true;
  document.getElementById("feedback-box").className="feedback-box";
  document.getElementById("action-row").className="action-row";
  document.getElementById("code-box").className="code-box";
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
</script>
</body></html>'''

if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port,debug=True)