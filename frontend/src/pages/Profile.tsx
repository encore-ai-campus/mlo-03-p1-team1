import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Pencil } from 'lucide-react'
import { updateProfile } from '../api/users'
import type { ProfilePatch } from '../api/users'
import { useSession } from '../context'
import { useApi } from '../hooks'
import { GENDERS, MBTI_TYPES, RESIDENCES } from '../types'
import type { User } from '../types'
import { ErrorState, Loading } from '../components/States'

export function Profile() {
  const s = useSession()
  const result = useApi<User>('/users/me')
  const [editing, setEditing] = useState(false)
  useEffect(() => { if (result.data) s.updateUser(result.data) }, [result.data, s.updateUser])
  if (result.loading) return <Loading />
  if (result.error) return <ErrorState error={result.error} retry={result.retry} />
  const user = result.data
  if (!user) return null

  return <section aria-labelledby="profile-title">
    <div className="account-section-heading"><div><h2 id="profile-title">나의 정보</h2><p>나를 소개하는 정보를 확인하고 수정하세요.</p></div>{!editing && <button className="button outline" onClick={() => setEditing(true)}><Pencil size={16} />정보 수정</button>}</div>
    {editing ? <ProfileForm user={user} cancel={() => setEditing(false)} saved={next => { s.updateUser(next); setEditing(false); result.retry(); s.toast('프로필을 저장했어요.') }} /> : <>
      <dl className="profile-details">
        <div><dt>이름</dt><dd>{user.name}</dd></div>
        <div><dt>이메일</dt><dd>{user.email}</dd></div>
        <div><dt>성별</dt><dd>{user.gender ? GENDERS[user.gender] : <span className="muted">미입력</span>}</dd></div>
        <div><dt>나이</dt><dd>{user.age === null ? <span className="muted">미입력</span> : `만 ${user.age}세`}</dd></div>
        <div><dt>거주지</dt><dd>{user.residence || <span className="muted">미입력</span>}</dd></div>
        <div><dt>직업</dt><dd>{user.occupation || <span className="muted">미입력</span>}</dd></div>
        <div><dt>성향 (MBTI)</dt><dd>{user.mbti || <span className="muted">미입력</span>}</dd></div>
      </dl>
      <p className="profile-note">추가 정보는 선택 사항이에요. 입력한 정보는 나의 취향을 이해하고 추천 서비스를 개선하는 데 활용할 수 있어요.</p>
    </>}
  </section>
}

function ProfileForm({ user, cancel, saved }: { user: User; cancel: () => void; saved: (user: User) => void }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setBusy(true); setError('')
    const form = new FormData(e.currentTarget)
    const age = String(form.get('age') || '').trim()
    const next = {
      name: String(form.get('name')).trim(), gender: (form.get('gender') || null) as User['gender'],
      age: age === '' ? null : Number(age), residence: (form.get('residence') || null) as User['residence'],
      occupation: String(form.get('occupation') || '').trim() || null, mbti: String(form.get('mbti') || '') || null,
    }
    const changes = Object.fromEntries(Object.entries(next).filter(([key, value]) => user[key as keyof typeof next] !== value)) as ProfilePatch
    try { saved(await updateProfile(changes)) } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <form className="profile-form" onSubmit={submit}>
    <p className="profile-note">이름 외 항목은 선택 입력입니다. ‘미입력’을 선택하거나 내용을 비우면 저장된 정보를 지울 수 있어요.</p>
    <fieldset disabled={busy}><legend className="sr-only">프로필 정보 수정</legend><div className="profile-form-grid">
      <label>이름 <span className="field-required">필수</span><input name="name" autoComplete="name" defaultValue={user.name} minLength={2} maxLength={40} required /></label>
      <label>성별<select name="gender" defaultValue={user.gender || ''}><option value="">미입력</option>{Object.entries(GENDERS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      <label>나이 (만 나이)<input name="age" type="number" inputMode="numeric" min={0} max={120} step={1} defaultValue={user.age ?? ''} placeholder="예: 28" /></label>
      <label>거주지<select name="residence" defaultValue={user.residence || ''}><option value="">미입력</option>{RESIDENCES.map(region => <option key={region} value={region}>{region}</option>)}</select></label>
      <label>직업<input name="occupation" list="occupation-options" defaultValue={user.occupation || ''} maxLength={80} placeholder="직업을 입력하거나 선택해 주세요" /><datalist id="occupation-options">{['학생', '회사원', '공무원', '전문직', '자영업', '프리랜서', '주부', '구직 중', '은퇴', '기타'].map(job => <option key={job} value={job} />)}</datalist></label>
      <label>성향 (MBTI)<select name="mbti" defaultValue={user.mbti || ''}><option value="">미입력</option>{MBTI_TYPES.map(type => <option key={type} value={type}>{type}</option>)}</select></label>
    </div></fieldset>
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="profile-form-actions"><button type="button" className="button outline" onClick={cancel} disabled={busy}>취소</button><button className="button primary" disabled={busy}>{busy ? '저장 중…' : '프로필 저장'}</button></div>
  </form>
}
