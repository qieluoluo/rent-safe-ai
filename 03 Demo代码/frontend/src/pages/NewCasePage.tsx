import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { createCase, DEMO_SAMPLE, ensureDemoUser } from '../api/client'
import { Layout } from '../components/Layout'

export function NewCasePage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const fillSample = () => {
    setTitle(DEMO_SAMPLE.title)
    setAmount(String(DEMO_SAMPLE.amount))
    setDescription(DEMO_SAMPLE.description)
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const userId = await ensureDemoUser()
      const created = await createCase({
        user_id: userId,
        case_title: title || '押金纠纷',
        case_type: 'DEPOSIT',
        description,
        amount: amount ? Number(amount) : undefined,
      })
      navigate(`/case/${created.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建案件失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-2xl font-bold">描述你的押金纠纷</h1>
        <p className="mt-2 text-sm text-slate-600">
          请尽量包含：押金金额、扣款理由、租约是否到期、对方身份（房东/中介）以及已有证据。
        </p>
        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">案件标题</span>
            <input
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="例如：押金被扣 2000 元"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">押金金额（元）</span>
            <input
              type="number"
              min="0"
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              placeholder="3000"
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-slate-700">纠纷描述</span>
            <textarea
              required
              rows={8}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-teal-500"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="请描述租期、押金金额、对方扣款理由和现有证据……"
            />
          </label>
          {error ? <p className="text-sm text-red-600">{error}</p> : null}
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={fillSample}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
            >
              填入演示样例
            </button>
            <button
              type="submit"
              disabled={loading}
              className="rounded-lg bg-teal-600 px-5 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-60"
            >
              {loading ? '创建中…' : '创建并分析'}
            </button>
          </div>
        </form>
      </section>
    </Layout>
  )
}
