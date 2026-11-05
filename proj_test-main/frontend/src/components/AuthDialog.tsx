import { useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight } from 'lucide-react'
import { api } from '../api/client'
import { useSession } from '../context'
import type { User } from '../types'
import { Dialog } from './Dialog'

export function AuthDialog() {
  const session = useSession()
  const [register, setRegister] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault(); setBusy(true); setError('')
    const data = Object.fromEntries(new FormData(e.currentTarget))
    try {
      const result = await api<{ access_token: string; user: User }>(`/auth/${register ? 'register' : 'login'}`, { method: 'POST', body: JSON.stringify(data) })
      session.acceptAuth(result.access_token, result.user)
      session.toast(register ? '가입을 완료했어요. 취향을 알려 주세요!' : '다시 만나 반가워요.')
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  return <Dialog open={session.authOpen} close={session.closeAuth} title={register ? '회원가입' : '로그인'}>
    <div className="dialog-symbol" aria-label="오디너리">O.</div><h2>{register ? '취향이 쌓이는 문화생활' : '나의 취향을 이어서'}</h2>
    <p className="muted">{register ? '마음에 드는 순간을 모으고, 새로운 문화를 만나세요.' : '찜한 콘텐츠와 나를 위한 추천을 만나보세요.'}</p>
    <div className="auth-tabs"><button className={!register ? 'selected' : ''} onClick={() => { setRegister(false); setError('') }}>로그인</button><button className={register ? 'selected' : ''} onClick={() => { setRegister(true); setError('') }}>회원가입</button></div>
    <form onSubmit={submit} className="stack">
      {register && <label>이름<input name="name" autoComplete="name" minLength={2} maxLength={40} required placeholder="문화생활에서 사용할 이름" /></label>}
      <label>이메일<input name="email" type="email" autoComplete="email" maxLength={254} required placeholder="you@example.com" /></label>
      <label>비밀번호<input name="password" type="password" autoComplete={register ? 'new-password' : 'current-password'} minLength={register ? 10 : 1} maxLength={128} required placeholder={register ? '10자 이상 입력해 주세요' : '비밀번호를 입력해 주세요'} /></label>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="button primary full" disabled={busy}>{busy ? '확인 중…' : register ? '가입하고 취향 찾기' : '로그인'}<ArrowRight size={18} /></button>
    </form>
    <p className="fine-print">취향 설문과 조회·찜 활동이 추천에 반영됩니다.<br />민감한 결제 정보는 저장하지 않습니다.</p>
  </Dialog>
}
