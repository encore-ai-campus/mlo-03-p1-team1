import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowLeft, ArrowRight } from 'lucide-react'
import { api } from '../api/client'
import { useSession } from '../context'
import type { User } from '../types'
import { GENDERS, MBTI_TYPES, RESIDENCES } from '../types'
import type { ProfilePatch } from '../api/users'
import type { TastePreferences } from '../preferences'
import { Dialog } from './Dialog'
import { PreferenceForm } from './PreferenceForm'

type RegistrationProfile = Omit<ProfilePatch, 'name'>
const REGISTRATION_STEPS = ['계정 정보', '프로필 정보', '취향 선택']

export function AuthDialog() {
  const session = useSession()
  const [register, setRegister] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState<0 | 1 | 2>(0)
  const [account, setAccount] = useState({ name: '', email: '', password: '' })
  const [profile, setProfile] = useState<RegistrationProfile>({})
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    if (session.authOpen) {
      setRegister(false); setError(''); setStep(0)
      setAccount({ name: '', email: '', password: '' }); setProfile({})
    }
  }, [session.authOpen])
  useEffect(() => {
    if (register && step > 0) heading.current?.focus()
  }, [register, step])
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setError('')
    if (register) { setStep(1); return }
    setBusy(true)
    try {
      const result = await api<{ access_token: string; user: User }>('/auth/login', {
        method: 'POST', body: JSON.stringify({ email: account.email, password: account.password }),
      })
      session.acceptAuth(result.access_token, result.user, 'login')
      setAccount(current => ({ ...current, password: '' }))
      session.toast('다시 만나 반가워요.')
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const finishRegistration = async (survey: TastePreferences) => {
    setBusy(true)
    try {
      const result = await api<{ access_token: string; user: User }>('/auth/register', {
        method: 'POST', body: JSON.stringify({ ...account, ...profile, survey }),
      })
      session.acceptAuth(result.access_token, result.user, 'register')
      setAccount(current => ({ ...current, password: '' }))
      session.toast('가입을 완료했어요. 프로필과 취향을 함께 저장했어요.')
    } finally { setBusy(false) }
  }
  const rememberProfile = (element: HTMLFormElement) => {
    const form = new FormData(element)
    const age = String(form.get('age') || '').trim()
    setProfile({
      gender: (form.get('gender') || null) as User['gender'], age: age === '' ? null : Number(age),
      residence: (form.get('residence') || null) as User['residence'],
      occupation: String(form.get('occupation') || '').trim() || null,
      mbti: String(form.get('mbti') || '') || null,
    })
  }
  return <Dialog open={session.authOpen} close={() => { if (!busy) session.closeAuth() }} title={register ? '회원가입' : '로그인'} className={register ? 'survey-dialog registration-dialog' : ''}>
    <h2 ref={heading} tabIndex={-1}>{!register ? '나의 취향을 이어서' : step === 0 ? '취향이 쌓이는 문화생활' : step === 1 ? '나를 조금 더 알려주세요' : '나의 취향으로 시작해요'}</h2>
    <p className="muted">{register ? '계정, 프로필, 취향을 한 번에 설정하고 시작하세요.' : '찜한 콘텐츠와 나를 위한 추천을 만나보세요.'}</p>
    <div className="auth-tabs" role="group" aria-label="로그인 또는 회원가입"><button aria-pressed={!register} className={!register ? 'selected' : ''} disabled={busy} onClick={() => { setRegister(false); setStep(0); setError('') }}>로그인</button><button aria-pressed={register} className={register ? 'selected' : ''} disabled={busy} onClick={() => { setRegister(true); setStep(0); setError('') }}>회원가입</button></div>
    {register && <ol className="registration-progress" aria-label="회원가입 단계">{REGISTRATION_STEPS.map((label, index) => <li key={label} className={index <= step ? 'complete' : ''} aria-current={index === step ? 'step' : undefined}><span>{index + 1}</span>{label}</li>)}</ol>}
    {(!register || step === 0) && <form onSubmit={submit} className="stack">
      {register && <label>이름<input name="name" autoComplete="name" minLength={2} maxLength={40} required placeholder="문화생활에서 사용할 이름" value={account.name} onChange={e => setAccount({ ...account, name: e.target.value })} /></label>}
      <label>이메일<input name="email" type="email" autoComplete="email" maxLength={254} required placeholder="you@example.com" value={account.email} onChange={e => setAccount({ ...account, email: e.target.value })} /></label>
      <label>비밀번호<input name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} minLength={register ? 10 : 1} maxLength={128} required placeholder={register ? '10자 이상 입력해 주세요' : '비밀번호를 입력해 주세요'} value={account.password} onChange={e => setAccount({ ...account, password: e.target.value })} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button primary full" disabled={busy}>{busy ? '확인 중…' : register ? '프로필 입력으로' : '로그인'}<ArrowRight size={18} /></button>
    </form>}
    {register && step === 1 && <form className="profile-form" onSubmit={e => {
      e.preventDefault()
      rememberProfile(e.currentTarget)
      setStep(2)
    }}>
      <p className="profile-note">모든 프로필 항목은 선택 입력이에요. 비워 두어도 가입할 수 있고, 마이페이지에서 언제든 수정할 수 있어요.</p>
      <fieldset><legend className="sr-only">회원가입 프로필 정보</legend><div className="profile-form-grid">
        <label>성별<select name="gender" defaultValue={profile.gender || ''}><option value="">선택 안 함</option>{Object.entries(GENDERS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label>나이 (만 나이)<input name="age" type="number" inputMode="numeric" min={0} max={120} step={1} defaultValue={profile.age ?? ''} placeholder="예: 28" /></label>
        <label>거주지<select name="residence" defaultValue={profile.residence || ''}><option value="">선택 안 함</option>{RESIDENCES.map(region => <option key={region} value={region}>{region}</option>)}</select></label>
        <label>직업<input name="occupation" list="registration-occupation-options" maxLength={80} defaultValue={profile.occupation || ''} placeholder="직접 입력하거나 선택해 주세요" /><datalist id="registration-occupation-options">{['학생', '회사원', '공무원', '전문직', '자영업', '프리랜서', '주부', '구직 중', '은퇴', '기타'].map(job => <option key={job} value={job} />)}</datalist></label>
        <label>성향 (MBTI)<select name="mbti" defaultValue={profile.mbti || ''}><option value="">선택 안 함</option>{MBTI_TYPES.map(type => <option key={type} value={type}>{type}</option>)}</select></label>
      </div></fieldset>
      <div className="survey-actions"><button type="button" className="button outline" onClick={e => { if (e.currentTarget.form) rememberProfile(e.currentTarget.form); setStep(0) }}><ArrowLeft size={17} />이전</button><button className="button primary">취향 선택으로<ArrowRight size={17} /></button></div>
    </form>}
    {register && <div hidden={step !== 2}><PreferenceForm onSubmitPreferences={finishRegistration} onBack={() => setStep(1)} submitLabel="회원가입 완료" /></div>}
    <p className="fine-print">프로필·취향과 조회·찜 활동이 추천에 반영됩니다.</p>
  </Dialog>
}
