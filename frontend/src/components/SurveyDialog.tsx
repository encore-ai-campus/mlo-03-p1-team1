import { useSession } from '../context'
import { Dialog } from './Dialog'
import { PreferenceForm } from './PreferenceForm'

export function SurveyDialog() {
  const s = useSession()
  return <Dialog open={s.surveyOpen} close={s.closeSurvey} title="나의 취향으로 시작하기" className="survey-dialog">
    <h2>나의 취향 찾기</h2>
    <p className="muted">{s.user ? '선택한 취향과 활동에 맞춰 문화를 추천해 드려요.' : '로그인 없이 시작해요. 취향은 이 브라우저에 저장돼요.'}</p>
    {s.surveyOpen && <PreferenceForm onSaved={s.closeSurvey} />}
    <button type="button" className="survey-skip" onClick={s.closeSurvey}>나중에 고르고 둘러볼게요</button>
  </Dialog>
}
