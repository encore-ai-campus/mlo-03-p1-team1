import { PreferenceForm } from '../components/PreferenceForm'

export function Preferences() {
  return <section aria-labelledby="preferences-title">
    <div className="account-section-heading"><div><h2 id="preferences-title">취향 설정</h2><p>좋아하는 분야와 키워드를 바꾸면 다음 추천에 반영됩니다.</p></div></div>
    <PreferenceForm />
  </section>
}
