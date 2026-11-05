import type { Category } from './types'

export const MAX_PREFERENCE_TAGS = 10
export type KeywordSectionId = 'genre' | 'mood' | 'style'

interface KeywordGroup {
  id: string
  title: string
  category?: Category
  keywords: readonly string[]
}

interface KeywordSection {
  id: KeywordSectionId
  label: string
  description: string
  groups: readonly KeywordGroup[]
}

export const KEYWORD_SECTIONS: readonly KeywordSection[] = [
  {
    id: 'genre', label: '세부 장르',
    description: '선택한 문화 분야에서 더 마음이 가는 장르를 골라보세요.',
    groups: [
      { id: 'exhibition', title: '전시', category: '전시', keywords: ['현대미술', '회화', '사진', '조각', '디자인', '미디어아트', '설치미술', '일러스트', '공예', '건축', '서예', '몰입형'] },
      { id: 'musical', title: '뮤지컬', category: '뮤지컬', keywords: ['창작뮤지컬', '라이선스뮤지컬', '오리지널뮤지컬', '주크박스뮤지컬', '넘버 중심', '댄스뮤지컬', '소극장뮤지컬', '대극장뮤지컬', '가족뮤지컬', '뮤지컬 갈라'] },
      { id: 'theatre', title: '연극', category: '연극', keywords: ['드라마극', '코미디극', '로맨스극', '스릴러극', '추리극', '고전극', '실험극', '창작극', '인형극', '넌버벌'] },
      { id: 'music', title: '음악', category: '음악', keywords: ['클래식', '재즈', '인디', '록', '팝', '힙합', 'R&B', '전자음악', '국악', '크로스오버', '어쿠스틱', '합창'] },
      { id: 'dance', title: '무용', category: '무용', keywords: ['발레', '현대무용', '한국무용', '스트리트댄스', '탭댄스', '세계민속무용', '비보잉', '댄스시어터'] },
      { id: 'festival', title: '축제', category: '축제', keywords: ['음악페스티벌', '영화제', '문화예술축제', '지역문화축제', '전통문화축제', '거리예술축제', '미디어축제', '문학축제', '공예축제', '복합문화축제'] },
    ],
  },
  {
    id: 'mood', label: '분위기·감성',
    description: '어떤 분위기와 이야기를 만날 때 가장 즐거운가요?',
    groups: [
      { id: 'atmosphere', title: '끌리는 분위기', keywords: ['잔잔한', '활기찬', '몽환적인', '유쾌한', '긴장감 있는', '서정적인', '실험적인', '웅장한'] },
      { id: 'story', title: '마음이 가는 이야기', keywords: ['이야기', '감동적인', '상상력', '사회적 메시지', '역사 이야기', '인간관계', '자연', '일상 속 발견'] },
    ],
  },
  {
    id: 'style', label: '관람 스타일',
    description: '함께하는 사람부터 공간과 경험까지, 나다운 관람을 골라보세요.',
    groups: [
      { id: 'companions', title: '누구와 함께', keywords: ['혼자 관람', '가족', '친구와', '연인과', '아이와'] },
      { id: 'space', title: '좋아하는 공간', keywords: ['야외', '실내', '소극장', '대극장', '미술관', '독립공간', '유서 깊은 공간'] },
      { id: 'experience', title: '즐기는 방식', keywords: ['체험형', '참여형', '해설과 함께', '깊이 감상', '새로운 시도', '입문자 친화', '사진 남기기', '여유로운 관람'] },
    ],
  },
]

export function getKeywordGroups(section: KeywordSectionId, categories: readonly string[]) {
  return KEYWORD_SECTIONS.find(item => item.id === section)!.groups.filter(group => !group.category || categories.includes(group.category))
}

export function togglePreferenceTag(tags: string[], keyword: string): string[] {
  if (tags.includes(keyword)) return tags.filter(tag => tag !== keyword)
  return tags.length < MAX_PREFERENCE_TAGS ? [...tags, keyword] : tags
}
