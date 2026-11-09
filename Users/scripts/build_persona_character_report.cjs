const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const dir = path.join(root, 'personas');
const files = Array.from({length:100},(_,i)=>`persona_${String(i+1).padStart(3,'0')}.md`);
const people = files.map(file => {
  const raw = fs.readFileSync(path.join(dir,file),'utf8');
  const match = raw.match(/```json\s*([\s\S]*?)\s*```/);
  if(!match) throw Error(`Missing JSON: ${file}`);
  const data=JSON.parse(match[1]);
  if(data.persona_id!==path.basename(file,'.md')) throw Error(`Persona ID mismatch: ${file}`);
  return data;
});
const tally = values => { const o={}; for(const v of values) for(const x of Array.isArray(v)?v:[v]) if(x!=null)o[x]=(o[x]||0)+1; return o; };
const table = (obj, name='항목') => Object.entries(obj).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'ko')).map(([k,v])=>`| ${k} | ${v} |`).join('\n') || `| 집계 없음 | 0 |`;
const budgets=people.map(p=>p.simulation_traits.monthly_culture_budget_krw).filter(Number.isFinite).sort((a,b)=>a-b);
const median=budgets.length%2?budgets[(budgets.length-1)/2]:(budgets[budgets.length/2-1]+budgets[budgets.length/2])/2;
let md=`# Oddinary 합성 페르소나 100명 특징 정리\n\n프로젝트의 personas/persona_001.md~persona_100.md JSON 프로필을 기준으로 정리했다. 연령·성별·지역·직업·MBTI와 가입 관심사는 가입 프로필이며, 예산·빈도·행동 성향은 시뮬레이터 판단 기준이다. 아래 집계는 입력 파일의 값을 센 결과다.\n\n## 전체 구성\n\n- 페르소나: ${people.length}명 (001~100)\n- 월 문화 예산: 평균 ${Math.round(budgets.reduce((a,b)=>a+b,0)/budgets.length).toLocaleString('ko-KR')}원, 중앙값 ${median.toLocaleString('ko-KR')}원, 범위 ${budgets[0].toLocaleString('ko-KR')}~${budgets.at(-1).toLocaleString('ko-KR')}원\n- 관심 문화 카테고리는 복수 선택을 포함하므로 카테고리별 인원수 합이 100명을 넘을 수 있다.\n\n| 문화 카테고리 | 인원 |\n|---|---:|\n${table(tally(people.map(p=>p.signup_profile.cultural_categories)))}\n\n## 인구·프로필 특성\n\n| 성별 | 인원 |\n|---|---:|\n${table(tally(people.map(p=>p.signup_profile.gender)))}\n\n| 거주 지역 | 인원 |\n|---|---:|\n${table(tally(people.map(p=>p.signup_profile.region)))}\n\n**연령대**\n\n| 연령대 | 인원 |\n|---|---:|\n${table(tally(people.map(p=>{const n=p.signup_profile.age; return n==null?'미입력':`${Math.floor(n/10)*10}대`;})))}\n\n**자주 등장하는 직업 (상위 15개)**\n\n| 직업 | 인원 |\n|---|---:|\n${table(Object.fromEntries(Object.entries(tally(people.map(p=>p.signup_profile.occupation))).slice(0,15)))}\n\n| MBTI | 인원 |\n|---|---:|\n${table(tally(people.map(p=>p.signup_profile.mbti)))}\n\n## 행동 성향 분포\n\n각 성향은 높음·보통·낮음으로 기록돼 있다.\n\n| 성향 | 높음 | 보통 | 낮음 |\n|---|---:|---:|---:|\n`;
for(const [label,key] of [['가격 민감도','price_sensitivity'],['문화 활동 빈도','culture_activity_frequency'],['검색 성향','search_tendency'],['찜 성향','favorite_tendency'],['후기 작성 성향','review_tendency'],['구매 성향','purchase_tendency']]) { const t=tally(people.map(p=>p.simulation_traits[key])); md+=`| ${label} | ${t.high||0} | ${t.medium||0} | ${t.low||0} |\n`; }
md+=`\n## 동행 유형\n\n| 동행 | 인원 |\n|---|---:|\n${table(tally(people.map(p=>p.simulation_traits.companions||[])))}\n\n## 페르소나별 특징\n\n`;
for(const p of people){const x=p.signup_profile,t=p.simulation_traits;md+=`### ${p.persona_id}\n\n- 프로필: ${x.age==null?'나이 미입력':`${x.age}세`} · ${x.gender||'성별 미입력'} · ${x.region||'지역 미입력'} · ${x.occupation||'직업 미입력'} · ${x.mbti||'MBTI 미입력'}\n- 관심 분야: ${(x.cultural_categories||[]).join(', ')||'미입력'}\n- 관심 키워드: ${(x.tags||[]).join(', ')||'없음'}\n- 월 예산: ${Number(t.monthly_culture_budget_krw||0).toLocaleString('ko-KR')}원 · 가격 민감도 ${t.price_sensitivity||'미입력'} · 활동 빈도 ${t.culture_activity_frequency||'미입력'}\n- 행동 성향: 검색 ${t.search_tendency||'미입력'} · 찜 ${t.favorite_tendency||'미입력'} · 후기 ${t.review_tendency||'미입력'} · 구매 ${t.purchase_tendency||'미입력'}\n- 동행: ${(t.companions||[]).join(', ')||'미입력'}\n- 성격: ${t.personality||'별도 서술 없음'}\n- 예상 행동: ${t.expected_behavior||'별도 서술 없음'}\n\n`;}
md+='## 해석 시 유의점\n\n- 합성 데이터이므로 실제 인구집단의 분포를 대표한다고 볼 수 없다.\n- 태그는 선호 입력이고, 실제 행동 결과나 사이트에서 해당 콘텐츠를 찾았다는 뜻은 아니다.\n- 예산과 행동 성향은 시뮬레이션 파라미터이며 가입 화면 정보로 사용되지 않는다.\n';
fs.writeFileSync(path.join(root,'report_cha.md'),md,'utf8');
console.log(JSON.stringify({personas:people.length,bytes:Buffer.byteLength(md),output:path.join(root,'report_cha.md'),categories:tally(people.map(p=>p.signup_profile.cultural_categories))}));
