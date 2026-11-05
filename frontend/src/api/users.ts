import { api } from './client'
import type { User } from '../types'

export type ProfilePatch = Partial<Pick<User, 'name' | 'gender' | 'age' | 'residence' | 'occupation' | 'mbti'>>

export function updateProfile(data: ProfilePatch) {
  return api<User>('/users/me', { method: 'PATCH', body: JSON.stringify(data) })
}
