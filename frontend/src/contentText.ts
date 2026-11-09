const internalNote = /^(?:\[(?:테스트(?:용)?|임시)[^\]]*\]|지역[·ㆍ]관람료\s*필터\s*(?:테스트|임시)\s*데이터)/

export function displayContentText(value: string): string {
  return value.split(/\r?\n\s*\r?\n/).map(paragraph => paragraph.trim())
    .filter(paragraph => !internalNote.test(paragraph)).join('\n\n')
}

export function displayPriceText(value: string): string {
  return value.replace(/\s*[(（](?:테스트(?:용)?|임시)[)）]/g, '').trim()
}
