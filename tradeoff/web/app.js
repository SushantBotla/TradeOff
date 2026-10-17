"use strict";
const $ = id => document.getElementById(id);
const labels = {baseline:"Baseline shortage",primary_loss:"Primary capacity loss",combined_loss:"Combined disruption",no_scarcity:"No scarcity",no_alternate:"No alternate supply"};
const number = v => v == null ? "—" : new Intl.NumberFormat("en-US", {maximumFractionDigits:2}).format(v);
const money = v => v == null ? "—" : "$" + number(v);
let token = sessionStorage.getItem("tradeoff-token") || "", config, model, current = null, generation = 0;
const explored = new Map();
function status(message, error=false) { $("status").textContent=message; $("status").classList.toggle("error",error); }
function busy(value) { for(const id of ["run","scenario","reset"]) $(id).disabled=value; }
async function read(path, body, authenticated=false) {
  const options={headers:{},signal:AbortSignal.timeout(20000)};
  if(authenticated) options.headers.Authorization=`Bearer ${token}`;
  if(body!==undefined){options.method="POST";options.headers["Content-Type"]="application/json";options.body=JSON.stringify(body);}
  const response=await fetch(path,options); const data=await response.json();
  if(!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
const api=(path,body)=>read(path,body,true);
function textCell(row,value){const td=document.createElement("td");td.textContent=String(value);row.append(td);}
function clearResult(){
  current=null;$("export").disabled=true;
  for(const id of ["metric-cost","metric-disclosure","metric-solve","candidate-cost","oracle-cost"]) $(id).textContent="—";
  $("metric-accept").textContent="— / 2";$("metric-round").textContent="Waiting for a scenario";
  $("metric-gap").textContent="Privileged synthetic benchmark";$("metric-backend").textContent="Measured execution time";
  $("run-state").textContent="Ready to explore";$("run-state").className="pill";
  $("explanation").textContent="Select a scenario to inspect how a shortage becomes a decision.";
  $("ai-label").textContent="";$("allocations").replaceChildren();$("allocation-bars").replaceChildren();
  $("transcript").textContent="Run a scenario to inspect messages.";$("actions").replaceChildren();
  $("disclosure").textContent="Only approved business signals are exchanged.";
  $("benchmark").textContent="The evaluator compares synthetic true costs after coordination.";
  for(const phase of ["propose","validate","repair","agree"]) $("phase-"+phase).className="";
}
function render(run,evaluation){
  current={run,evaluation,provenance:config.mode==="demo" ? "Recorded execution on LinuxONE; loaded from a static public fixture" : "New execution from the connected runtime"};
  $("export").disabled=false;$("run-state").textContent=run.status==="completed"?"Agreement reached":run.status;
  $("run-state").className="pill"+(run.status==="completed"?" green":"");
  const last=run.rounds.at(-1), lastOptimal=[...run.rounds].reverse().find(r=>r.allocations);
  const accepted=Object.values(last?.feedback || {}).filter(f=>f.accept).length;
  $("metric-accept").textContent=`${accepted} / 2`;
  $("metric-round").textContent=`${run.rounds.length} solver round${run.rounds.length===1?"":"s"} · ${run.status}`;
  $("metric-cost").textContent=money(evaluation?.final_true_cost);
  $("metric-gap").textContent=evaluation?.optimality_gap_percent!=null?`${number(evaluation.optimality_gap_percent)}% gap to full-information optimum`:(evaluation?.oracle?.true_cost===0?`Zero-cost oracle · $${number(evaluation.absolute_regret)} regret`:"No accepted comparable cost");
  $("metric-disclosure").textContent=number(run.disclosure?.business_scalar_values_transmitted);
  $("metric-solve").textContent=`${number(run.rounds.reduce((sum,r)=>sum+(r.solve_ms || 0),0))} ms`;
  $("metric-backend").textContent=`${last?.backend || "pending"} · ${config.mode==="demo"?"recorded on s390x":"runtime measurement"}`;
  $("explanation").textContent=run.explanation || run.error || "Negotiation in progress…";
  const ai=run.ai || {};
  $("ai-label").textContent=ai.local_ml_inferences>0?`${ai.local_ml_inferences} learned-model predictions · ${ai.model} · validation order informed by delivery risk · ${number(run.elapsed_ms)} ms end to end`:ai.live_llm_calls>0?`${ai.live_llm_calls} successful LLM calls`:"Deterministic controller; no successful learned-model inference recorded.";
  if(ai.fallback_used) $("ai-label").textContent+=" · Fallback: "+ai.fallback_reason;
  $("phase-propose").className=run.rounds.length?"complete":"";
  $("phase-validate").className=run.transcript?.some(t=>t.path==="/validate")?"complete":"";
  $("phase-repair").className=run.rounds.length>1?"complete":"";
  $("phase-agree").className=run.status==="completed"?"complete":run.status!=="running"?"warn":"";
  $("allocations").replaceChildren();
  for(const round of run.rounds){const tr=document.createElement("tr");for(const value of [String(round.round_id).padStart(2,"0"),round.allocations?.factory_a??"—",round.allocations?.factory_b??"—",round.alternate_qty??"—",round.surrogate_cost==null?round.status:money(round.surrogate_cost)])textCell(tr,value);$("allocations").append(tr);}
  $("allocation-bars").replaceChildren();
  if(lastOptimal){
    const a=lastOptimal.allocations.factory_a,b=lastOptimal.allocations.factory_b,max=Math.max(a,b,lastOptimal.alternate_qty,1);
    for(const [label,value] of [["Factory A",a],["Factory B",b],["Alternate",lastOptimal.alternate_qty]]){
      const line=document.createElement("div"),name=document.createElement("span"),track=document.createElement("div"),fill=document.createElement("span"),qty=document.createElement("strong");
      line.className="allocation-line";name.textContent=label;track.className="allocation-track";fill.className="allocation-fill";fill.style.width=`${100*value/max}%`;qty.textContent=number(value);track.append(fill);line.append(name,track,qty);$("allocation-bars").append(line);
    }
    if(run.status!=="completed"){const note=document.createElement("p");note.className="scope-note";note.textContent="Last feasible proposal shown. This allocation was not mutually accepted.";$("allocation-bars").append(note);}
  }
  $("candidate-cost").textContent=money(evaluation?.final_true_cost);$("oracle-cost").textContent=money(evaluation?.oracle?.true_cost);
  $("benchmark").textContent=evaluation?.oracle?`Oracle: ${evaluation.oracle.status.replaceAll("_"," ")}. ${evaluation.rounds.map((r,i)=>`Round ${i+1} true cost ${money(r.true_cost)}`).join("; ")}. ${evaluation.absolute_regret!=null?`Accepted absolute regret ${money(evaluation.absolute_regret)}.`:"No accepted benchmark comparison."}`:"Waiting for the separate evaluator…";
  const d=run.disclosure;
  $("disclosure").textContent=d?`${d.participant_message_count} participant messages · ${d.business_scalar_values_transmitted} business scalar values · ${d.business_payload_bytes} business payload bytes. Counts include feedback and are not a privacy score.`:"Collecting approved messages…";
  $("transcript").textContent=JSON.stringify(run.transcript,null,2);$("actions").replaceChildren();
  for(const action of run.agent_actions || []){const li=document.createElement("li");li.textContent=`${action.name.replaceAll("_"," ")} · ${action.source} · ${number(action.latency_ms)} ms${action.validation_order?" · "+action.validation_order.join(" → "):""}`;$("actions").append(li);}
}
function history(items){
  $("run-history").replaceChildren();
  if(!items.length){const p=document.createElement("p");p.className="muted";p.textContent="Your explored scenarios appear here.";$("run-history").append(p);}
  for(const r of items){const button=document.createElement("button"),meta=document.createElement("span");button.className="history-button";button.textContent=labels[r.scenario_id] || r.scenario_id;meta.textContent=`${r.status} · ${config.mode==="demo"?"recorded LinuxONE":r.run_id.slice(0,8)}`;button.append(meta);button.addEventListener("click",()=>{if(config.mode==="demo"){const entry=explored.get(r.scenario_id);render(entry.run,entry.evaluation);$("scenario").value=r.scenario_id;status("Loaded recorded "+labels[r.scenario_id]+".");}else watch(r.run_id);});$("run-history").append(button);}
}
async function replay(){
  busy(true);const id=$("scenario").value;status("Loading recorded LinuxONE evidence…");
  try{const record=await read(`demo/${id}.json`);render(record.run,record.evaluation);explored.set(id,record);history([...explored.values()].map(r=>r.run).reverse());status(`Recorded ${labels[id]} · executed ${new Date(record.run.created_at*1000).toLocaleString()} · replay does not create a new VM run.`);}
  catch(error){status(error.message,true);}finally{busy(false);}
}
async function watch(runId){
  const active=++generation;busy(true);
  try{
    for(;;){const run=await api(`/api/runs/${runId}`);if(active!==generation)return;render(run,null);
      if(run.status!=="running"){
        for(let i=0;i<40;i++){const report=await api(`/api/runs/${runId}/evaluation`);if(active!==generation)return;if(report.oracle){render(run,report);break;}await new Promise(resolve=>setTimeout(resolve,400));}
        status(`${labels[run.scenario_id]} · ${run.status} · new runtime execution`,run.status==="failed");history(await api("/api/runs"));break;
      }status("Coordinating on the connected runtime…");await new Promise(resolve=>setTimeout(resolve,400));
    }
  }catch(error){status(error.message,true);}finally{if(active===generation)busy(false);}
}
function metrics(){const m=model.metrics;$("model-metrics").textContent=`Chronological holdout: ${number(model.holdout_rows)} line items · ${number(100*m.holdout_accuracy)}% accuracy vs ${number(100*m.majority_baseline_accuracy)}% majority baseline · ROC AUC ${number(m.holdout_roc_auc)}.`;}
async function connect(){await api("/api/runs");sessionStorage.setItem("tradeoff-token",token);$("token").value="";$("login").hidden=true;$("controls").hidden=false;$("logout").hidden=false;model=await api("/api/ml");metrics();history(await api("/api/runs"));status("Connected. Choose a scenario and run coordination.");}
$("login-form").addEventListener("submit",async event=>{event.preventDefault();token=$("token").value.trim();try{await connect();}catch(error){status(error.message,true);}});
$("run").addEventListener("click",async()=>{if(config.mode==="demo")return replay();busy(true);status("Starting a new runtime execution…");try{const run=await api("/api/runs",{scenario_id:$("scenario").value});await watch(run.run_id);}catch(error){status(error.message,true);busy(false);}});
$("reset").addEventListener("click",async()=>{try{if(config.mode==="live")await api("/api/demo/reset",{});++generation;clearResult();$("check-result").hidden=true;explored.clear();history(config.mode==="live"?await api("/api/runs"):[]);status("View reset. Runtime audit history is preserved.");}catch(error){status(error.message,true);}});
$("logout").addEventListener("click",()=>{token="";sessionStorage.removeItem("tradeoff-token");++generation;location.reload();});
$("export").addEventListener("click",()=>{if(!current)return;const url=URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:"application/json"}));const a=document.createElement("a");a.href=url;a.download=`tradeoff-${current.run.scenario_id}-${config.mode}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
for(const [id,path,body] of [["denial","/api/demo/denial-test",{}],["audit","/api/audit",undefined]]){$(id).addEventListener("click",async()=>{try{if(config.mode==="live"&&!token)throw new Error("Connect to the protected runtime first.");const result=config.mode==="demo"?(await read("demo/verification.json"))[id]:await api(path,body);$("check-result").hidden=false;$("check-result").textContent=JSON.stringify({provenance:config.mode==="demo"?"Recorded verification on LinuxONE; this click reads evidence, it does not run a new security test":"Fresh verification on the connected runtime",result},null,2);status(config.mode==="demo"?"Recorded verification evidence loaded.":"Runtime verification completed.");}catch(error){status(error.message,true);}});}
$("risk-form").addEventListener("submit",async event=>{event.preventDefault();try{if(!model)throw new Error("Connect to the runtime to load its model.");const inputs={shipping_mode:$("shipping-mode").value,scheduled_days:Number($("scheduled-days").value),market:$("market").value};let result;
  if(config.mode==="demo"){
    const modes=["Standard Class","Second Class","First Class","Same Day"],markets=["Africa","Europe","LATAM","Pacific Asia","USCA"];
    if(!modes.includes(inputs.shipping_mode)||!markets.includes(inputs.market)||!Number.isFinite(inputs.scheduled_days)||inputs.scheduled_days<0||inputs.scheduled_days>10)throw new Error("Use valid model inputs and promised days from 0 to 10.");
    const v=[1,inputs.scheduled_days/5,...modes.map(x=>Number(x===inputs.shipping_mode)),...markets.map(x=>Number(x===inputs.market))];const score=model.weights.reduce((sum,w,i)=>sum+w*v[i],0);result={delay_probability:1/(1+Math.exp(-Math.max(-35,Math.min(35,score)))),model:model.version};
  }else result=await api("/api/ml/predict",inputs);
  $("prediction").textContent=`${number(100*result.delay_probability)}% predicted delay risk`;
  const note=document.createElement("small");note.textContent=`${result.model} · ${config.mode==="demo"?"Fresh browser inference using learned coefficients":"Fresh inference on the connected runtime"}`;$("prediction").append(note);
}catch(error){status(error.message,true);}});
async function init(){
  config=await read("site-config.json");
  if(config.mode==="demo"){
    $("runtime").textContent="RECORDED LINUXONE DEMO";$("runtime").classList.add("green");$("mode-banner").textContent="Public showcase · Scenario replay loads recorded LinuxONE runs. Delivery-risk inference runs live in your browser. No private runtime connection is required.";
    $("run").textContent="Replay LinuxONE run ↗";$("denial").textContent="View denied-access evidence";$("audit").textContent="View audit verification";$("history-label").textContent="Explored this session";$("controls").hidden=false;model=await read("demo/model.json");metrics();await replay();
  }else{
    const h=await read("health");$("runtime").textContent=h.linuxone_architecture?"LIVE / s390x LINUXONE":"LIVE / LOCAL DEVELOPMENT";
    $("mode-banner").textContent=`Connected runtime · ${h.architecture} · Python ${h.python} · ${h.isolation} · New coordination jobs run here after you authenticate.`;
    $("history-label").textContent="Runtime history";$("login").hidden=false;status("Authenticate with your dashboard token to run coordination.");
    if(token){try{await connect();}catch(error){sessionStorage.removeItem("tradeoff-token");token="";status(error.message,true);}}
  }
}
init().catch(error=>status("Workspace could not load: "+error.message,true));
