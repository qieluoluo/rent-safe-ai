import { Link } from 'react-router-dom'

import { Layout } from '../components/Layout'

export function HomePage() {
  return (
    <Layout>
      <section className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-sm font-medium text-teal-600">V1.0 · 押金纠纷黄金路径</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight">租房押金纠纷智能分析</h1>
        <p className="mt-4 max-w-2xl leading-7 text-slate-600">
          输入你的押金纠纷描述，系统将按六步可观测工作流整理事实、评估信息完整度、检索法律依据，并输出风险提示与行动建议。
        </p>
        <div className="mt-6 rounded-xl bg-slate-50 p-4 text-sm text-slate-600">
          <p className="font-medium text-slate-800">能力状态说明</p>
          <ul className="mt-2 list-inside list-disc space-y-1">
            <li>
              <strong>已实现：</strong>案件创建、六步 Mock 分析、报告落库、Agent 轨迹查询
            </li>
            <li>
              <strong>演示模式：</strong>当前使用规则 Mock 基线（mock-v1.2），非真实大模型
            </li>
            <li>
              <strong>规划中：</strong>向量 RAG、真实 LLM 接入、OCR 证据解析
            </li>
          </ul>
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/case/new"
            className="rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-teal-700"
          >
            开始分析
          </Link>
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100"
          >
            查看 API 文档
          </a>
        </div>
        <p className="mt-6 text-xs text-slate-500">
          本工具仅提供信息整理与风险提示，不构成法律意见。涉及真实证据时请遵守授权与隐私要求。
        </p>
      </section>
    </Layout>
  )
}
