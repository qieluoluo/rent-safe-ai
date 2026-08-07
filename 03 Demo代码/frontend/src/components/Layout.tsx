import { Link } from 'react-router-dom'

import { DemoBadge } from './DemoBadge'

interface LayoutProps {
  children: React.ReactNode
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-3">
            <span className="text-sm font-semibold tracking-[0.2em] text-teal-600">RENT SAFE AI</span>
            <span className="text-lg font-bold">租安 AI</span>
          </Link>
          <DemoBadge />
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  )
}
