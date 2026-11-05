import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { X } from 'lucide-react'

export function Dialog({ open, close, title, children, className = '' }: { open: boolean; close: () => void; title: string; children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open) { dialog.showModal(); document.body.style.overflow = 'hidden' }
    else if (dialog.open) dialog.close()
    return () => { document.body.style.overflow = ''; if (dialog.open) dialog.close() }
  }, [open])
  return <dialog ref={ref} className={className} aria-label={title} onCancel={close} onClick={e => { if (e.target === e.currentTarget) close() }}>
    <div className="dialog-inner"><button className="icon-button dialog-close" onClick={close} aria-label="닫기"><X size={22} /></button>{children}</div>
  </dialog>
}
