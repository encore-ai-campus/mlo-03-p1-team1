// Rebuild the report from the copied server evidence; no network or credentials.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const rel = 'reports/server-[IP_REDACTED]-2026-11-09';
const dir = path.join(root, rel);
const lines = fs.readFileSync(path.join(dir, 'scheduler.log'), 'utf8').split(/\r?\n/);
const kst = t => new Date(new Date(t).getTime()+9*3600000).toISOString().slice(0,19).replace('T',' ');
const esc = s => String(s ?? '').replace(/\|/g,'\\|').replace(/[\r\n]+/g,' ');
const rounds = []; let current = null; const active = new Set();
const issues = [];
for(let i=0;i<lines.length;i++) {
  const line=lines[i]; let m;
  if(m=line.match(/^\[([^\]]+)\] 시작 (persona_\d+);/)) {
    if(!current) current={ordinal:rounds.length+1,start:m[1],line_start:i+1,people:{},actions:{},counts:{},events:[]};
    if(current.people[m[2]]) issues.push(`duplicate start ${i+1}`);
    current.people[m[2]]={id:m[2],start:m[1],start_line:i+1,save_lines:[],events:[]}; active.add(m[2]);
  } else if(m=line.match(/^\[([^\]]+)\] 종료 (persona_\d+);/)) {
    const p=current?.people[m[2]]; if(!p) throw Error(`orphan end ${i+1}`);
    p.end=m[1];p.end_line=i+1;active.delete(m[2]);
  } else if(m=line.match(/^실행 결과 저장: runs\/(persona_\d+)_simulation.json/)) {
    current.people[m[1]].save_lines.push(i+1);
  } else if(m=line.match(/^\[([^\]]+)\] 회차 (\d+): 100명 전원 종료/)) {
    current.end=m[1];current.server_cycle=Number(m[2]);current.line_end=i+1;
    if(active.size) issues.push(`active at cycle end ${i+1}`);
    rounds.push(current);current=null;
  } else if(current && (m=line.match(/^\[([^\]]+)\] (.+?): (성공|건너뜀|실패|시작|완료) - (.*)$/))) {
    const event={timestamp:m[1],action:m[2],status:m[3],detail:m[4],line:i+1,candidates:[...active]};
    current.events.push(event);
    current.counts[m[3]]=(current.counts[m[3]]||0)+1;
    const key=m[2]+' / '+m[3];current.actions[key]=(current.actions[key]||0)+1;
    if(active.size===1) current.people[[...active][0]].events.push(event);
  }
}
if(current) issues.push('unfinished round');
for(const r of rounds) {
  r.complete = Object.keys(r.people).length===100 && Array.from({length:100},(_,i)=>r.people[`persona_${String(i+1).padStart(3,'0')}`]).every(p=>p?.end && p.save_lines.length===1);
  r.unattributed = r.events.filter(e=>e.candidates.length!==1).length;
  r.pageFailures = r.events.filter(e=>e.action==='페이지 실행' && e.status==='실패').length;
  if(!r.complete) issues.push(`incomplete ${r.ordinal}`);
}
if(issues.length) throw Error(JSON.stringify(issues));
for(const r of rounds.slice(5)) {
  if(r.unattributed!==0 || r.events.length!==200 || Object.values(r.people).some(p=>p.events.length!==2 || p.events.some(e=>e.status!=='실패' || !e.detail.includes('net::ERR_ADDRESS_UNREACHABLE')))) throw Error(`Unexpected failure pattern ${r.ordinal}`);
}
const knownHashes = { 'scheduler.log':'7df955f4c24de60cc0e93d18ba72111be3bc9fe3140ec9f7640ca26eb0131d1b', 'scheduler_cycle.json':'ed239c3f12879031e684416cb7eaf8fd050132db737af9e4b2b5c07db95e8b6c', 'scheduler.py':'aa502e29ad9300c2a442da8ed3ee1a781697b1a7d0ee34967d84b15c27ef7fb5', 'simulator.py':'21e32f4b5f496393c8bf197a89a33b179106b184dc3578c9ede5c858047664ad' };
const files=fs.readdirSync(dir).filter(f=>/^(persona_\d+_(behavior|simulation)\.json|scheduler\.(log|py)|scheduler_cycle\.json|simulator\.py)$/.test(f));
if(files.length!==204) throw Error(`Expected 204 source files, found ${files.length}`);
const manifest=files.map(name=>{const data=fs.readFileSync(path.join(dir,name));const sha256=crypto.createHash('sha256').update(data).digest('hex');if(knownHashes[name] && sha256!==knownHashes[name])throw Error(`Hash mismatch ${name}`);return {name,bytes:data.length,sha256,remote_hash_verified:!!knownHashes[name]};});
const latest=JSON.parse(fs.readFileSync(path.join(dir,'scheduler_cycle.json'),'utf8'));
const last=rounds.at(-1);
for(const p of Object.values(last.people)) {
  const data=JSON.parse(fs.readFileSync(path.join(dir,`${p.id}_simulation.json`),'utf8'));
  if(data.persona_id!==p.id || new Date(data.started_at)<new Date(p.start) || new Date(data.ended_at)>new Date(p.end))throw Error(`latest mismatch ${p.id}`);
  p.original_result=data;
}
if(latest.cycle!==last.server_cycle || latest.results.length!==100)throw Error('latest cycle mismatch');
fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify({source:'test@[IP_REDACTED]:/home/test/oddinary_persona_starter',observed_at_utc:'2026-11-09T01:14:51Z',process_observation:'scheduler.pid PID absent; pgrep python.*src.main returned no processes',files},null,2));
// Store hashes separately so source files remain byte-for-byte copies.
fs.writeFileSync(path.join(dir,'sha256.json'),JSON.stringify(manifest,null,2));
const out=path.join(dir,'analysis');fs.mkdirSync(out,{recursive:true});
const summaries=[];const csv=[['통산회차','서버회차','페르소나','시작_KST','종료_KST','시작_로그행','종료_로그행','저장_로그행','단독활동_성공','단독활동_건너뜀','단독활동_실패','개인별_상세범위']];
for(const r of rounds) {
  const id=String(r.ordinal).padStart(2,'0');
  const allSingle=r.unattributed===0;
  let md=`# 통산 ${r.ordinal}회차 / 서버 표기 ${r.server_cycle}회차\n\n- 시간(KST): ${kst(r.start)} ~ ${kst(r.end)}\n- persona_001~100 각각 시작·종료·결과 저장 기록 확인: 100명.\n- 원본 로그 행: ${r.line_start}~${r.line_end}. [회차 로그](cycle-${id}.log), [분석 JSON](cycle-${id}.json).\n- 행동 로그 상태별 건수: 성공 ${r.counts['성공']||0}, 건너뜀 ${r.counts['건너뜀']||0}, 실패 ${r.counts['실패']||0}, 네트워크 등 시작 ${r.counts['시작']||0}, 완료 ${r.counts['완료']||0}.\n- 개인 식별이 불확실한 동시 활동 로그: ${r.unattributed}건.\n\n`;
  md+=`개인별 행동 수는 로그 시점에 활동 중인 페르소나가 1명인 행만 집계했습니다. ${allSingle?'이 회차는 모든 행동 행이 단독 활동 구간에 있어 개인별 연결이 가능합니다.':'동시 활동 구간의 행동은 식별자가 없어 개인별 전체 결과를 복원할 수 없습니다. 아래 0건은 행동이 없었다는 뜻이 아닙니다.'} ${r.ordinal===last.ordinal?'최신 회차는 보존된 100개 원본 JSON도 대조했습니다.':'이 회차의 원본 개별 JSON은 현재 서버에서 확인되지 않았습니다.'}\n\n`;
  md+='## 100명별 기록\n\n| 페르소나 | 시작 KST | 종료 KST | 저장 로그 행 | 단독 활동 성공/건너뜀/실패 | 개인별 상세 범위 |\n|---|---|---|---:|---|---|\n';
  for(const p of Object.values(r.people)) {
    const c={};for(const e of p.events)c[e.status]=(c[e.status]||0)+1;
    const scope=r.ordinal===last.ordinal?'원본 JSON + 로그':allSingle?'단독 활동 로그 전체':'단독 활동 로그 일부; 동시 활동 상세 귀속 불가';
    md+=`| ${p.id} | ${kst(p.start)} | ${kst(p.end)} | ${p.save_lines.join(', ')} | ${c['성공']||0}/${c['건너뜀']||0}/${c['실패']||0} | ${scope} |\n`;
    csv.push([r.ordinal,r.server_cycle,p.id,kst(p.start),kst(p.end),p.start_line,p.end_line,p.save_lines.join(';'),c['성공']||0,c['건너뜀']||0,c['실패']||0,scope]);
  }
  md+='\n## 회차 전체 행동별 집계\n\n| 행동 / 상태 | 건수 |\n|---|---:|\n';
  for(const [key,n] of Object.entries(r.actions).sort())md+=`| ${esc(key)} | ${n} |\n`;
  const failures={};for(const e of r.events.filter(e=>e.status==='실패'))failures[e.action+' — '+e.detail]=(failures[e.action+' — '+e.detail]||0)+1;
  md+='\n## 실패 내용\n\n';
  md+=Object.entries(failures).sort((a,b)=>b[1]-a[1]).map(([k,n])=>`- ${n}건: ${esc(k)}`).join('\n')||'실패 행 없음.';
  fs.writeFileSync(path.join(out,`cycle-${id}.md`),md+'\n');
  fs.writeFileSync(path.join(out,`cycle-${id}.log`),lines.slice(r.line_start-1,r.line_end).join('\n')+'\n');
  fs.writeFileSync(path.join(out,`cycle-${id}.json`),JSON.stringify(r,null,2));
  summaries.push({ordinal:r.ordinal,server_cycle:r.server_cycle,start_kst:kst(r.start),end_kst:kst(r.end),people:100,complete:r.complete,counts:r.counts,page_failures:r.pageFailures,unattributed:r.unattributed,line_start:r.line_start,line_end:r.line_end});
}
fs.writeFileSync(path.join(out,'personas-by-cycle.csv'),'\uFEFF'+csv.map(row=>row.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\r\n'));
fs.writeFileSync(path.join(out,'cycles.json'),JSON.stringify(summaries,null,2));
let report=`# Oddinary 페르소나 반복 실행 결과 보고서\n\n- 확인 시각: 2026-11-09 10:14:51 KST (UTC+9).\n- 서버: [IP_REDACTED], 프로젝트: /home/test/oddinary_persona_starter.\n- 조사 근거: 서버의 scheduler.log, 최신 scheduler_cycle.json, persona_001~100의 simulation/behavior JSON, 서버 실행 코드.\n\n## 확인 결과\n\n**페르소나 1~100 전체 실행은 총 ${rounds.length}회 확인됐습니다. 최초 1회 이후 추가 ${rounds.length-1}회이며, 총 ${(rounds.length*100).toLocaleString('en-US')}개 세션입니다.**\n\n로그의 회차 표기는 최초 1회 종료 후 다시 1부터 시작해 마지막 32에 도달합니다. 이 보고서는 시간순 통산 회차 1~33을 사용하고 서버 표기도 함께 표시합니다. 번호 재시작은 프로세스 재기동과 일치하는 정황이지만 재기동 원인 자체는 이 로그로 확인되지 않습니다. 각 회차에서 persona_001~persona_100 각각의 시작·종료·파일 저장 행을 대조했습니다. 33회 모두 100명씩이며 누락된 ID가 없습니다.\n\n통산 1~5회에는 사이트 이용과 성공 행동이 기록됐습니다. **통산 6~33회(28회, 2,800명 실행)는 모든 페르소나가 net::ERR_ADDRESS_UNREACHABLE로 페이지 진입에 실패**했습니다. 각 세션에는 네트워크 요청 실패와 페이지 실행 실패가 각각 1건씩 있습니다. 따라서 ‘100명 전원 종료’는 실행 절차의 종료이며 행동 성공을 의미하지 않습니다.\n\n마지막 완료 시각은 ${kst(last.end)} KST입니다. 조사 시 scheduler.pid의 프로세스와 python.*src.main 프로세스는 조회되지 않았으며 로그에 후속 회차 시작도 없습니다. 중지 시각·이유는 남은 자료에서 확인되지 않습니다.\n\n## 회차별 결과\n\n성공·건너뜀·실패는 로그에 기록된 상태별 행 수입니다. 네트워크 요청의 ‘시작’과 응답의 ‘완료’는 아래 세 열에서 제외했습니다. 페이지 방문·로그인·탐색 등 다양한 동작이 포함되므로 성공 건수는 성공 사용자 수가 아닙니다. 각 회차 링크에는 100명별 시작·종료·저장 행과 행동별 집계, 실패 상세가 있습니다.\n\n| 통산 회차 | 서버 회차 | 시작 KST | 종료 KST | 시작/종료/저장 | 성공 | 건너뜀 | 실패 | 페이지 실행 실패 |\n|---|---:|---|---|---|---:|---:|---:|---:|\n`;
for(const r of rounds)report+=`| [${r.ordinal}회](${rel}/analysis/cycle-${String(r.ordinal).padStart(2,'0')}.md) | ${r.server_cycle} | ${kst(r.start)} | ${kst(r.end)} | 100/100/100 | ${r.counts['성공']||0} | ${r.counts['건너뜀']||0} | ${r.counts['실패']||0} | ${r.pageFailures} |\n`;
report+=`\n## 서버에 저장된 결과물과 복원 가능한 범위\n\n서버에는 페르소나별 최신 실행 결과 JSON 100개, 행동 확률 JSON 100개, 최신 회차 요약 JSON 1개, 전체 누적 로그 1개가 있었습니다. 실행 코드 2개를 포함해 **원본 파일 204개**를 [프로젝트 결과 폴더](${rel}/)에 복사했습니다. 서버 원본은 유지했고 로그인 계정·비밀번호 파일은 복사하지 않았습니다.\n\n- simulation JSON에는 시작·종료 시각, 종료 사유, 행동별 시간·상태·상세, 조회 콘텐츠, 카테고리·태그 요약이 있습니다. 현재 100개 모두 서버 표기 32회차(통산 33회차)의 결과이며, 페이지 실행 실패·조회 콘텐츠 없음으로 기록돼 있습니다. [persona_001 예시](${rel}/persona_001_simulation.json).\n- behavior JSON은 행동·카테고리 선택 확률이며 실제 행동 결과가 아닙니다.\n- [최신 회차 요약](${rel}/scheduler_cycle.json)은 100명 모두 status=종료, end_reason=페이지 로딩 또는 실행 실패입니다.\n- [원본 누적 로그](${rel}/scheduler.log)에는 전 회차 실행과 행동 기록이 남아 있습니다.\n\n서버 코드 simulator.py의 437~438행은 같은 persona_*_simulation.json 경로에 매번 write_text를 수행합니다. scheduler.py의 130행도 scheduler_cycle.json을 덮어씁니다. /home/test 아래에서 가상환경을 제외하고 시뮬레이션·회차·스케줄러 로그 및 zip/tar 파일을 검색했을 때 별도 과거 결과 보관본은 발견되지 않았습니다. **각 회차 결과가 당시 저장됐다는 로그는 있으나, 회차별 JSON 3,300개가 보존된 상태는 아닙니다.**\n\n통산 1~5회에는 최대 5명의 행동이 같은 로그에 섞이고 행동 행에 persona_id가 없습니다. 그 때문에 이전 회차의 100명 각각이 조회한 콘텐츠·검색어·결제 등 전체 행동 내역을 정확히 복원할 수 없습니다. 회차별 집계는 전체 로그에서 산출하고, 개인별 표는 명시적인 시작·종료·저장 기록 및 단독 활동 중인 행만 연결했습니다. 동시 활동 중인 행동은 분석 JSON의 candidates에 후보 ID를 남겼으며 임의로 배정하지 않았습니다. 통산 6~33회는 행동 행이 모두 단독 활동 구간에 있어 개인별 접속 실패를 확인할 수 있습니다.\n\n## 자료 위치와 대조 방법\n\n- [3,300개 세션의 회차·페르소나별 표(CSV)](${rel}/analysis/personas-by-cycle.csv)\n- [33개 회차 집계(JSON)](${rel}/analysis/cycles.json)\n- [수집 정보와 원본 파일 목록](${rel}/manifest.json), [파일별 SHA-256](${rel}/sha256.json)\n- [집계 재생성 스크립트](scripts/summarize_server_results.cjs): 프로젝트에서 node scripts/summarize_server_results.cjs 실행.\n\n각 회차별 Markdown·JSON·로그 발췌는 원본에서 생성한 분석 파일이며 서버가 별도로 보관한 회차별 원본 JSON을 의미하지 않습니다. 원본 로그·최신 회차 JSON·실행 코드 2개의 SHA-256은 서버에서 읽은 값과 복사본이 일치했습니다. simulation JSON 100개는 마지막 회차의 페르소나 ID 및 실행 시간 범위와 대조했습니다.\n\n최초 회차 뒤 로그에는 2시간 휴식, 이후에는 30분 휴식이라고 기록돼 있으며 현재 서버 코드도 30분입니다. 최초 회차 이후 실제 다음 시작은 2시간보다 빨랐고 회차 번호도 재시작했습니다. 모든 회차에 2시간 휴식을 적용해 해석하면 안 됩니다.\n\n이 보고서는 실행 서버의 결과 파일과 로그를 근거로 합니다. 행동 성공이나 HTTP 202 응답만으로 MongoDB 저장 완료·실제 결제 승인을 확정하지 않았습니다. 기존 모니터링 보고서는 최초 회차의 보조 자료로 유지하며, 이번 회차 수 집계는 해당 모니터링 요청 건수에서 추정하지 않았습니다.\n`;
let behavior='## 통산 1~5회 행동별 결과\n\n서버 로그의 행동명·상태를 그대로 집계했습니다. 같은 사람이 여러 번 수행한 동작도 각각 세며, 콘텐츠 결제 성공은 시뮬레이터의 판정입니다. 실제 PG 승인 여부를 별도로 확인한 수치는 아닙니다.\n\n| 행동 / 상태 | 1회 | 2회 | 3회 | 4회 | 5회 |\n|---|---:|---:|---:|---:|---:|\n';
const actionKeys=[...new Set(rounds.slice(0,5).flatMap(r=>Object.keys(r.actions)))].filter(k=>!k.startsWith('네트워크')).sort();
for(const key of actionKeys)behavior+=`| ${esc(key)} | ${rounds.slice(0,5).map(r=>r.actions[key]||0).join(' | ')} |\n`;
behavior+='\n통산 6~33회는 매 회차 네트워크 요청 실패 100건과 페이지 실행 실패 100건이며, 검색·조회·찜·추천·결제 등 사이트 내 행동 성공 기록은 없습니다.\n\n';
report=report.replace('## 서버에 저장된 결과물과 복원 가능한 범위',behavior+'## 서버에 저장된 결과물과 복원 가능한 범위');
fs.writeFileSync(path.join(root,'reprt.md'),report);
fs.writeFileSync(path.join(root,'report.md'),report);
console.log(JSON.stringify({rounds:rounds.length,sessions:csv.length-1,files:files.length,verified_remote_hashes:Object.keys(knownHashes).length,first_5_counts:summaries.slice(0,5).map(s=>s.counts)},null,2));
