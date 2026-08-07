import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getReport, runAnalysis } from '../api/client'
import { Layout } from '../components/Layout'
import type { AgentTrace, AnalysisResult, Report } from '../types/api'

const TASK_LABELS: Record<string, string> = {
  INTENT: '意图识别',
  EXTRACTION: '信息抽取',
  COMPLETENESS: '完整度评估',
  KNOWLEDGE: '知识检索',
  RISK: '风险评估',
  REPORT: '报告生成',
}

const RISK_LABELS: Record<string, string> = {
  HIGH: '高风险（信息不足）',
  MEDIUM: '中风险（证据不足）',
  LOW: '低风险（可进入核对）',
}

function ReportSection({ title, content }: { title: string; content: string | null | undefined }) {
  if (!content) return null
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold text-slate-900">{title}</h2>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-700">{content}</p>
    </section>
  )
}

function WorkflowTrace({ workflow }: { workflow: AgentTrace[] }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-base font-semibold text-slate-900">Agent 工作流轨迹</h2>
      <ol className="mt-4 space-y-3">
        {workflow.map((step, index) => (
          <li key={`${step.task_type}-${index}`} className="rounded-lg bg-slate-50 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-medium text-slate-800">{TASK_LABELS[step.task_type] ?? step.task_type}</span>
              <span className="text-xs text-slate-500">
                {step.status} · {step.latency}ms
              </span>
            </div>
            {step.output ? (
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words text-xs text-slate-600">
                {typeof step.output === 'string' ? step.output : JSON.stringify(step.output, null, 2)}
              </pre>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  )
}

export function CaseDetailPage() {
  const { caseId } = useParams()
  const numericCaseId = Number(caseId)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!numericCaseId) return
    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')
      try {
        const result = await runAnalysis(numericCaseId)
        if (cancelled) return
        setAnalysis(result)
        setReport(result.report)
      } catch (err) {
        if (cancelled) return
        try {
          const existing = await getReport(numericCaseId)
          setReport(existing)
        } catch {
          setError(err instanceof Error ? err.message : '分析失败')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [numericCaseId])

  return (
    <Layout>
      <div className="mb-4">
        <Link to="/case/new" className="text-sm text-teal-600 hover:underline">
          ← 新建案件
        </Link>
      </div>

      {loading ? (
        <section className="rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-600">
          正在运行六步分析工作流…
        </section>
      ) : null}

      {error ? (
        <section className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">{error}</section>
      ) : null}

      {analysis ? (
        <section className="mb-6 rounded-2xl border border-teal-200 bg-teal-50 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-teal-700">分析完成 · 案件 #{analysis.case_id}</p>
              <h1 className="mt-1 text-2xl font-bold text-slate-900">{analysis.dispute_type}</h1>
            </div>
            <div className="text-right text-sm text-slate-600">
              <p>模式：{analysis.analysis_mode === 'DEMO' ? '演示模式' : analysis.analysis_mode}</p>
              <p>Provider：{analysis.provider} / {analysis.model}</p>
              <p>Prompt：{analysis.prompt_version}</p>
            </div>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg bg-white p-3 text-sm">
              <p className="text-slate-500">风险等级</p>
              <p className="font-semibold text-slate-900">{RISK_LABELS[analysis.risk_level] ?? analysis.risk_level}</p>
            </div>
            <div className="rounded-lg bg-white p-3 text-sm">
              <p className="text-slate-500">信息完整度</p>
              <p className="font-semibold text-slate-900">
                {analysis.completeness ? '已达标' : '未达标'}（{Math.round(analysis.completeness_score * 100)}%）
              </p>
            </div>
            <div className="rounded-lg bg-white p-3 text-sm">
              <p className="text-slate-500">检索依据</p>
              <p className="font-semibold text-slate-900">{analysis.retrieved_knowledge.length} 条</p>
            </div>
          </div>
          {!analysis.completeness && analysis.follow_up_questions.length > 0 ? (
            <div className="mt-4 rounded-lg bg-white p-4">
              <p className="text-sm font-medium text-slate-800">建议补充</p>
              <ul className="mt-2 list-inside list-disc text-sm text-slate-700">
                {analysis.follow_up_questions.map((question) => (
                  <li key={question}>{question}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      ) : null}

      {report ? (
        <div className="space-y-4">
          <ReportSection title="事实摘要" content={report.summary} />
          <ReportSection title="风险分析" content={report.risk_analysis} />
          <ReportSection title="法律依据" content={report.legal_basis} />
          <ReportSection title="证据缺口" content={report.missing_evidence} />
          <ReportSection title="行动建议" content={report.action_plan} />
          {report.disclaimer ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-xs text-amber-900">{report.disclaimer}</p>
          ) : null}
        </div>
      ) : null}

      {analysis?.workflow?.length ? <div className="mt-6"><WorkflowTrace workflow={analysis.workflow} /></div> : null}
    </Layout>
  )
}
