// Primitivas visuales compartidas. Ninguna página define sus propios botones, tarjetas o
// etiquetas: todo sale de aquí y de los tokens de index.css.
import { Link } from 'react-router-dom'

const cx = (...parts) => parts.filter(Boolean).join(' ')

export function Button({ as: As = 'button', variant = 'primary', size = 'md', className, ...props }) {
  const base = 'inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap'
  const sizes = { sm: 'h-8 px-3 text-[13px]', md: 'h-10 px-4 text-sm', lg: 'h-12 px-5 text-[15px]' }
  const variants = {
    primary: 'bg-accent text-accent-ink hover:bg-accent-hover',
    secondary: 'border border-line bg-bg text-ink hover:bg-subtle',
    ghost: 'text-ink-2 hover:bg-subtle hover:text-ink',
  }
  return <As className={cx(base, sizes[size], variants[variant], className)} {...props} />
}

export function Card({ className, ...props }) {
  return <div className={cx('rounded-xl border border-line bg-bg', className)} {...props} />
}

export function PageHeader({ eyebrow, title, children, actions }) {
  return (
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl">
        {eyebrow && <p className="mb-2 text-[13px] text-ink-3">{eyebrow}</p>}
        <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.02em] sm:text-[32px]">{title}</h1>
        {children && <div className="mt-2 text-[15px] leading-relaxed text-ink-2">{children}</div>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  )
}

export function Stat({ value, label, hint }) {
  return (
    <div className="min-w-0">
      <div className="num text-2xl font-semibold tracking-tight sm:text-[26px]">{value}</div>
      <div className="mt-1 text-[13px] text-ink-2">{label}</div>
      {hint && <div className="mt-0.5 text-xs text-ink-3">{hint}</div>}
    </div>
  )
}

const STATUS_STYLE = {
  abierta: { color: 'var(--open)', bg: 'var(--open-bg)', dot: true },
  en_evaluacion: { color: 'var(--warn)', bg: 'var(--warn-bg)' },
  adjudicada: { color: 'var(--award)', bg: 'var(--award-bg)' },
  desierta: { color: 'var(--muted)', bg: 'var(--muted-bg)' },
  cancelada: { color: 'var(--danger)', bg: 'var(--danger-bg)' },
  suspendida: { color: 'var(--danger)', bg: 'var(--danger-bg)' },
  concluida: { color: 'var(--muted)', bg: 'var(--muted-bg)' },
  aviso: { color: 'var(--muted)', bg: 'var(--muted-bg)' },
  otro: { color: 'var(--muted)', bg: 'var(--muted-bg)' },
}

export function StatusBadge({ status, label, estimated }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.otro
  return (
    <span
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium"
      style={{ color: s.color, background: s.bg }}
      title={estimated ? 'Estimado: la fuente no publica este estatus' : undefined}
    >
      {s.dot && <span className="h-1.5 w-1.5 rounded-full" style={{ background: s.color }} />}
      {label}
      {estimated && <span aria-hidden>*</span>}
    </span>
  )
}

export function Tag({ children, to, tone = 'neutral', className }) {
  const tones = {
    neutral: 'bg-muted text-ink-2',
    accent: 'bg-accent-soft text-accent',
    warn: '',
  }
  const style = tone === 'warn' ? { color: 'var(--warn)', background: 'var(--warn-bg)' } : undefined
  const cls = cx('inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs', tones[tone], className)
  if (to) return <Link to={to} className={cx(cls, 'hover:underline')} style={style}>{children}</Link>
  return <span className={cls} style={style}>{children}</span>
}

export function Input({ className, ...props }) {
  return (
    <input
      className={cx('h-10 w-full rounded-lg border border-line bg-bg px-3 text-sm text-ink placeholder:text-ink-3 focus:border-accent focus:outline-none', className)}
      {...props}
    />
  )
}

export function Select({ className, children, ...props }) {
  return (
    <select
      className={cx('h-10 w-full rounded-lg border border-line bg-bg px-2.5 text-sm text-ink focus:border-accent focus:outline-none', className)}
      {...props}
    >
      {children}
    </select>
  )
}

export function Loading({ label = 'Cargando datos…' }) {
  return (
    <div className="flex items-center gap-3 py-16 text-sm text-ink-3" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-accent" />
      {label}
    </div>
  )
}

export function ErrorNote({ error }) {
  return (
    <Card className="p-5 text-sm text-ink-2">
      No se pudieron leer los datos. {error?.message}
    </Card>
  )
}

export function Empty({ title, children }) {
  return (
    <div className="rounded-xl border border-dashed border-line px-6 py-14 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mt-1 text-sm text-ink-2">{children}</div>}
    </div>
  )
}

export function Section({ title, aside, children, className }) {
  return (
    <section className={cx('mt-10', className)}>
      {(title || aside) && (
        <div className="mb-3 flex items-baseline justify-between gap-4">
          {title && <h2 className="text-lg font-semibold tracking-tight">{title}</h2>}
          {aside}
        </div>
      )}
      {children}
    </section>
  )
}

export function Pagination({ page, pages, onPage }) {
  if (pages <= 1) return null
  return (
    <nav className="mt-4 flex items-center justify-between gap-2 text-sm" aria-label="Paginación">
      <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>Anterior</Button>
      <span className="text-ink-3">Página <span className="num">{page}</span> de <span className="num">{pages}</span></span>
      <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Siguiente</Button>
    </nav>
  )
}

export { cx }
