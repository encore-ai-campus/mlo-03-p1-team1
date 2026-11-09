import { Link } from 'react-router-dom'

export function Brand({ footer = false }: { footer?: boolean }) {
  return <Link to="/" className={`brand${footer ? ' brand-footer' : ''}`} aria-label="Oddinary 홈">
    <span className="brand-symbol" aria-hidden="true">✳</span><span>Oddinary</span>
  </Link>
}
