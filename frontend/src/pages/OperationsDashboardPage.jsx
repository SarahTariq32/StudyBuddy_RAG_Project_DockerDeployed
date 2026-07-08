import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchOpsDashboard, fetchOpsTraceById, fetchOpsTraces, getCachedOpsDashboard, getCachedOpsTraces } from '../api/ops.js'


const REQUEST_TIMEOUT_MS = 5000
const POLL_MS = 15000
const WINDOW_OPTIONS = [
  { label: '24h', value: 24 },
  { label: '7d', value: 24 * 7 },
]

function withTimeout(promise, timeoutMs = REQUEST_TIMEOUT_MS) {
  return Promise.race([
    promise,
    new Promise(resolve => setTimeout(() => resolve(null), timeoutMs)),
  ])
}

function fmtMs(value) {
  if (value == null || Number.isNaN(Number(value))) return 'N/A'
  const ms = Number(value)
  if (ms < 1000) return `${ms.toFixed(0)} ms`
  return `${(ms / 1000).toFixed(2)} s`
}

function fmtNum(value) {
  if (value == null || Number.isNaN(Number(value))) return 'N/A'
  return Number(value).toLocaleString()
}

function resolveTraceQuestion(trace) {
  const stageQuestion = trace?.pipeline_stages?.query_rewrite?.inputs?.question
    || trace?.pipeline_stages?.query_rewrite?.inputs?.query
    || trace?.pipeline_stages?.retrieval?.inputs?.query
  return trace?.question || stageQuestion || null
}

function sameTraceIds(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b)) return false
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i += 1) {
    if (a[i]?.id !== b[i]?.id) return false
  }
  return true
}

function yForValue(value, min, max, height) {
  if (max === min) return height / 2
  const pct = (value - min) / (max - min)
  return height - pct * (height - 16) - 8
}

function linePath(points, width, height) {
  if (!points || points.length === 0) return ''
  const values = points.map(p => Number(p.value || 0))
  const min = Math.min(...values)
  const max = Math.max(...values)
  const step = points.length > 1 ? (width - 16) / (points.length - 1) : 0

  return points
    .map((p, i) => {
      const x = 8 + i * step
      const y = yForValue(Number(p.value || 0), min, max, height)
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
    })
    .join(' ')
}

function cardStyle() {
  return {
    background: 'rgba(0, 10, 30, 0.55)',
    border: '1px solid rgba(0,180,255,0.2)',
    borderRadius: '14px',
    backdropFilter: 'blur(8px)',
    boxShadow: '0 0 28px rgba(0,120,255,0.12)',
    transition: 'transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease',
  }
}

function StatCard({ title, value, subtitle }) {
  return (
    <div className="ops-card" style={{ ...cardStyle(), padding: '0.95rem 1rem' }}>
      <div style={{ color: 'rgba(150,210,255,0.65)', fontSize: '0.74rem', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{title}</div>
      <div style={{ color: '#f4fbff', fontSize: '1.35rem', fontWeight: 700, marginTop: '0.2rem' }}>{value}</div>
      <div style={{ color: 'rgba(130,175,235,0.58)', fontSize: '0.75rem', marginTop: '0.25rem' }}>{subtitle}</div>
    </div>
  )
}

function LineChartCard({ title, points, color = '#00b7ff', yLabel = 'ms' }) {
  const width = 560
  const height = 170
  const path = useMemo(() => linePath(points || [], width, height), [points])

  return (
    <div className="ops-card" style={{ ...cardStyle(), padding: '0.9rem' }}>
      <div style={{ color: '#d5efff', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.7rem' }}>{title}</div>
      <div style={{ border: '1px solid rgba(0,130,255,0.15)', borderRadius: '10px', padding: '0.35rem', background: 'rgba(0,6,22,0.55)' }}>
        <svg viewBox={`0 0 ${width} ${height}`} style={{ width: '100%', height: '170px', display: 'block' }}>
          <rect x="0" y="0" width={width} height={height} fill="transparent" />
          <path d={path} fill="none" stroke={color} strokeWidth="2.2" />
        </svg>
      </div>
      <div style={{ color: 'rgba(145,200,245,0.62)', fontSize: '0.74rem', marginTop: '0.45rem' }}>
        {points?.length || 0} points · unit: {yLabel}
      </div>
    </div>
  )
}

function BarChartCard({ title, rows, xKey, yKey, color = '#2dd2ff' }) {
  const max = useMemo(() => Math.max(1, ...(rows || []).map(r => Number(r[yKey] || 0))), [rows, yKey])

  return (
    <div className="ops-card" style={{ ...cardStyle(), padding: '0.9rem' }}>
      <div style={{ color: '#d5efff', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.65rem' }}>{title}</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
        {(rows || []).slice(-12).map((row, idx) => {
          const value = Number(row[yKey] || 0)
          const pct = Math.max(4, (value / max) * 100)
          return (
            <div key={idx} style={{ display: 'grid', gridTemplateColumns: '84px 1fr 58px', gap: '0.5rem', alignItems: 'center' }}>
              <div style={{ color: 'rgba(145,200,245,0.75)', fontSize: '0.73rem' }}>{row[xKey]}</div>
              <div style={{ height: '9px', background: 'rgba(0,70,130,0.35)', borderRadius: '999px', overflow: 'hidden', border: '1px solid rgba(0,130,255,0.2)' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: `linear-gradient(90deg, ${color}, rgba(0,100,255,0.75))` }} />
              </div>
              <div style={{ color: '#d4eeff', fontSize: '0.72rem', textAlign: 'right' }}>{fmtNum(value)}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SuccessFailureCard({ rows }) {
  const success = Number((rows || []).find(r => r.label === 'success')?.value || 0)
  const failure = Number((rows || []).find(r => r.label === 'failure')?.value || 0)
  const total = Math.max(1, success + failure)
  const sPct = (success / total) * 100

  return (
    <div className="ops-card" style={{ ...cardStyle(), padding: '0.9rem' }}>
      <div style={{ color: '#d5efff', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>Success vs Failure</div>
      <div style={{ height: '14px', borderRadius: '999px', border: '1px solid rgba(0,160,255,0.25)', overflow: 'hidden', background: 'rgba(0,40,90,0.35)' }}>
        <div style={{ height: '100%', width: `${sPct.toFixed(1)}%`, background: 'linear-gradient(90deg, #0ed28f, #00b7ff)' }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.6rem', color: 'rgba(185,225,255,0.78)', fontSize: '0.78rem' }}>
        <span>Success: {fmtNum(success)}</span>
        <span>Failure: {fmtNum(failure)}</span>
      </div>
    </div>
  )
}

function stageLabel(name) {
  return String(name || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function stageLatencyMs(trace, stageName) {
  const stages = trace?.pipeline_stages || {}
  const stage = stages[stageName] || {}
  const direct = stage?.latency_ms
  if (direct != null) return direct

  if (stageName === 'retrieval') return trace?.durations_ms?.retrieval_ms
  if (stageName === 'llm_generation') return trace?.durations_ms?.llm_ms
  if (stageName === 'final_answer') {
    const total = Number(trace?.durations_ms?.overall_ms)
    const retrieval = Number(trace?.durations_ms?.retrieval_ms)
    const llm = Number(trace?.durations_ms?.llm_ms)
    if (Number.isFinite(total) && Number.isFinite(retrieval) && Number.isFinite(llm)) {
      const remainder = total - retrieval - llm
      return remainder > 0 ? remainder : 0
    }
  }
  return null
}


function TraceList({ traces, selectedId, onSelect }) {
  return (
    <div
      className="ops-card"
      style={{
        ...cardStyle(),
        padding: '0.85rem',
        height: '100%',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ color: '#d5efff', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.7rem' }}>Recent Requests</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', overflowY: 'auto', minHeight: 0, flex: 1, paddingRight: '0.2rem' }}>
        {traces.map(trace => {
          const isFailed = String(trace.status || '').toLowerCase() === 'failed'
          const isSelected = selectedId === trace.id
          const isSlow = Number(trace.durations_ms?.overall_ms || 0) > 10000
          const isSuccess = !isFailed && !isSlow
          const palette = isFailed
            ? {
              bg: isSelected ? 'rgba(214, 60, 82, 0.30)' : 'rgba(118, 40, 48, 0.34)',
              border: isSelected ? 'rgba(244, 114, 132, 0.70)' : 'rgba(226, 92, 110, 0.52)',
            }
            : isSlow
              ? {
                bg: isSelected ? 'rgba(202, 155, 54, 0.28)' : 'rgba(120, 98, 40, 0.34)',
                border: isSelected ? 'rgba(246, 206, 90, 0.72)' : 'rgba(214, 178, 78, 0.56)',
              }
              : {
                bg: isSelected ? 'rgba(30, 136, 93, 0.28)' : 'rgba(27, 94, 66, 0.32)',
                border: isSelected ? 'rgba(88, 217, 160, 0.70)' : 'rgba(72, 190, 140, 0.52)',
              }

          return (
          <button
            key={trace.id}
            onClick={() => onSelect(trace)}
            className="ops-trace-btn"
            style={{
              textAlign: 'left',
              width: '100%',
              background: palette.bg,
              border: `1px solid ${palette.border}`,
              borderRadius: '8px',
              padding: '0.65rem',
              color: '#e0f2ff',
              cursor: 'pointer',
            }}
          >
            <div style={{ fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.2rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{resolveTraceQuestion(trace) || 'No Question'}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.6rem', alignItems: 'center' }}>
              <div style={{ fontSize: '0.7rem', color: 'rgba(215,236,245,0.84)' }}>{new Date(trace.timestamp).toLocaleTimeString()}</div>
              <div style={{ fontSize: '0.68rem', color: isFailed ? '#ffc1cf' : isSlow ? '#ffe8b1' : '#c6f7df', textTransform: 'capitalize' }}>
                {isFailed ? 'failed' : isSlow ? 'slow' : isSuccess ? 'success' : 'pending'}
              </div>
            </div>
          </button>
          )
        })}
      </div>
    </div>
  )
}

function TraceDetails({ trace, loading }) {
  if (loading) {
    return (
      <div style={{ ...cardStyle(), padding: '1rem', minHeight: '240px', height: '100%', overflowY: 'auto', color: 'rgba(145,200,245,0.72)' }}>
        Loading trace details...
      </div>
    )
  }
  if (!trace) {
    return (
      <div style={{ ...cardStyle(), padding: '1rem', minHeight: '240px', height: '100%', overflowY: 'auto', color: 'rgba(145,200,245,0.72)' }}>
        Select a request to inspect trace details.
      </div>
    )
  }

  const stages = trace.pipeline_stages || {};
  const displayQuestion = resolveTraceQuestion(trace)
  const stageStatusSummary = [
    'query_rewrite',
    'retrieval',
    'llm_generation',
    'final_answer',
  ]

  return (
    <div className="ops-card" style={{ ...cardStyle(), padding: '0.85rem', height: '100%', overflowY: 'auto' }}>
      <div style={{ color: '#d5efff', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.6rem' }}>Trace Viewer</div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.62rem', marginBottom: '0.75rem' }}>
        <StatCard title="Status" value={trace.status || 'N/A'} subtitle={trace.timestamp ? new Date(trace.timestamp).toLocaleString() : 'No timestamp'} />
        <StatCard title="Total Time" value={fmtMs(trace?.durations_ms?.overall_ms)} subtitle="End-to-end latency" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.62rem' }}>
          <div className="ops-card" style={{ ...cardStyle(), padding: '0.7rem' }}>
            <div style={{ color: '#bfe9ff', fontSize: '0.76rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Question</div>
            <div style={{ color: '#effbff', fontSize: '0.82rem', marginTop: '0.4rem' }}>{displayQuestion || 'N/A'}</div>
          </div>

        <div className="ops-card" style={{ ...cardStyle(), padding: '0.7rem' }}>
          <div style={{ color: '#bfe9ff', fontSize: '0.76rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Retrieved Chunks</div>
          <div style={{ color: '#effbff', fontSize: '0.82rem', marginTop: '0.3rem', marginBottom: '0.55rem' }}>
            {fmtNum(trace.retrieved_chunk_count)}
          </div>

          <div style={{ maxHeight: '138px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.38rem' }}>
            {(trace.retrieved_documents || []).slice(0, 8).map((doc, i) => (
              <div key={i} style={{ border: '1px solid rgba(0,130,255,0.22)', borderRadius: '8px', padding: '0.4rem', background: 'rgba(0,13,35,0.55)' }}>
                <div style={{ color: '#d9f3ff', fontSize: '0.75rem', fontWeight: 600 }}>{doc.source || 'unknown'}</div>
                <div style={{ color: 'rgba(155,207,248,0.8)', fontSize: '0.72rem', marginTop: '0.2rem' }}>score: {doc.score == null ? 'N/A' : Number(doc.score).toFixed(4)}</div>
                <div style={{ color: 'rgba(171,213,246,0.78)', fontSize: '0.72rem', marginTop: '0.22rem' }}>{doc.text_preview || ''}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="ops-card" style={{ ...cardStyle(), padding: '0.7rem', marginTop: '0.65rem' }}>
        <div style={{ color: '#bfe9ff', fontSize: '0.76rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Status Summary</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.42rem', marginTop: '0.45rem' }}>
          {stageStatusSummary.map((name) => {
            const stage = stages[name] || {}
            const stageMs = stageLatencyMs(trace, name)
            const failed = stage?.status === 'failed'
            return (
              <div key={name} style={{ border: '1px solid rgba(0,130,255,0.2)', borderRadius: '8px', padding: '0.5rem 0.6rem', background: 'rgba(0,13,35,0.55)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.7rem', alignItems: 'center' }}>
                  <div style={{ color: '#d9f3ff', fontSize: '0.79rem', fontWeight: 600 }}>{stageLabel(name)}</div>
                  <div style={{ color: failed ? '#ff9eb1' : '#c7f5e0', fontSize: '0.82rem', fontWeight: 700 }}>
                    {fmtMs(stageMs)}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function OperationsDashboardPage() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dashboard, setDashboard] = useState(null)
  const [traceData, setTraceData] = useState([])
  const [selectedTrace, setSelectedTrace] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [windowHours, setWindowHours] = useState(24);
  const [traceLoading, setTraceLoading] = useState(false);

  const load = useCallback(async (hoursArg = windowHours) => {
    try {
      setError('')
      const dash = await withTimeout(fetchOpsDashboard({ hours: hoursArg, limit: 80 }))
      if (dash) {
        setDashboard(dash)
      } else {
        const cachedDashboard = getCachedOpsDashboard()
        if (cachedDashboard) {
          setDashboard(prev => prev || cachedDashboard)
        }
      }

      const traceResp = await withTimeout(fetchOpsTraces({ hours: hoursArg, limit: 80 }))
      const recentTraces = traceResp?.traces || []
      if (recentTraces.length > 0) {
        setTraceData(prev => (sameTraceIds(prev, recentTraces) ? prev : recentTraces))
        setSelectedTrace(prev => {
          if (prev && recentTraces.some(t => t.id === prev.id)) {
            return recentTraces.find(t => t.id === prev.id)
          }
          return recentTraces[0] || null
        })
      }

      if (dash) {
        setLastUpdated(new Date())
      }
      const cachedTraceList = getCachedOpsTraces()?.traces || []
      if (cachedTraceList.length > 0 && traceData.length === 0) {
        setTraceData(cachedTraceList)
      }
    } catch (err) {
      setError(err?.message || 'Failed to load operations data.')
    } finally {
      setLoading(false)
    }
  }, [windowHours])

  const handleTraceSelect = useCallback(async (trace) => {
    setSelectedTrace(trace)
    if (!trace?.id) {
      return
    }

    // Skip extra fetch only if multi‑queries already present (to avoid extra network)
    if (trace?.multi_queries?.length) {
      setTraceLoading(false)
      return
    }

    setTraceLoading(true)
    const detail = await withTimeout(fetchOpsTraceById(trace.id), 6000)
    setTraceLoading(false)
    const hydrated = detail?.trace
    if (!hydrated) {
      return
    }

    setTraceData(prev => prev.map(t => (t.id === hydrated.id ? hydrated : t)))
    setSelectedTrace(prev => (prev?.id === hydrated.id ? hydrated : prev))
  }, [])

  useEffect(() => {
    const cachedDashboard = getCachedOpsDashboard()
    const cachedTraces = getCachedOpsTraces()
    if (cachedDashboard) {
      setDashboard(cachedDashboard)
      setLoading(false)
      setLastUpdated(new Date())
    }
    if (cachedTraces?.traces?.length) {
      setTraceData(cachedTraces.traces)
      setSelectedTrace(cachedTraces.traces[0] || null)
    }

    load(windowHours)
    const timer = setInterval(() => {
      load(windowHours)
    }, POLL_MS)
    return () => clearInterval(timer)
  }, [load, windowHours])

  const metrics = dashboard?.metrics || {}
  const charts = dashboard?.charts || {}
  const effectiveWindow = Number(dashboard?.window_hours || windowHours || 24)

  return (
    <div style={{
      minHeight: '100dvh',
      width: '100%',
      background: 'radial-gradient(ellipse at 30% 50%, #000d1a 0%, #000208 60%, #000000 100%)',
      fontFamily: "'Segoe UI', sans-serif",
      color: '#eaf6ff',
      padding: '0.9rem',
      boxSizing: 'border-box',
      overflowX: 'hidden',
    }}>
      <div style={{
        maxWidth: '1320px',
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.8rem',
      }}>
        <div style={{ ...cardStyle(), padding: '0.9rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.7rem', flexWrap: 'wrap' }}>
          <div>
            <div style={{ color: 'rgba(0,200,255,0.8)', fontSize: '0.74rem', letterSpacing: '0.16em', textTransform: 'uppercase', marginBottom: '0.2rem' }}>StudyBuddy LLMOps</div>
            <h1 style={{ margin: 0, fontSize: '1.5rem', lineHeight: 1.2 }}>AI Operations Dashboard</h1>
            <div style={{ color: 'rgba(160,210,245,0.74)', fontSize: '0.78rem', marginTop: '0.3rem' }}>
              Provider: {dashboard?.active_provider || 'N/A'} · Project: {dashboard?.project || 'N/A'} · Window: last {effectiveWindow >= 24 ? `${Math.round(effectiveWindow / 24)} day(s)` : `${effectiveWindow} hour(s)`} · Last updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : 'N/A'}
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <select
              value={windowHours}
              onChange={(e) => setWindowHours(Number(e.target.value))}
              style={{
                border: '1px solid rgba(0,180,255,0.35)',
                background: 'rgba(0,14,30,0.75)',
                color: '#d7f4ff',
                borderRadius: '10px',
                padding: '0.52rem 0.72rem',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              {WINDOW_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label} window</option>
              ))}
            </select>
            <button
              className="ops-btn ops-btn-primary"
              onClick={() => load(windowHours)}
              style={{
                border: '1px solid rgba(0,180,255,0.35)',
                background: 'rgba(0,40,85,0.55)',
                color: '#d7f4ff',
                borderRadius: '10px',
                padding: '0.52rem 0.9rem',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Refresh
            </button>
            <button
              className="ops-btn ops-btn-secondary"
              onClick={() => navigate('/chat')}
              style={{
                border: '1px solid rgba(0,180,255,0.35)',
                background: 'rgba(0,14,30,0.75)',
                color: '#d7f4ff',
                borderRadius: '10px',
                padding: '0.52rem 0.9rem',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              Back To Chat
            </button>
          </div>
        </div>

        {loading && (
          <div style={{ ...cardStyle(), padding: '1rem', color: 'rgba(140,200,245,0.78)' }}>
            Loading observability metrics...
          </div>
        )}

        {!!error && (
          <div style={{ ...cardStyle(), padding: '1rem', border: '1px solid rgba(255,100,130,0.55)', color: '#ffd3dc' }}>
            {error}
          </div>
        )}

        {dashboard && dashboard.enabled === false && !loading && (
          <div style={{ ...cardStyle(), padding: '1rem', border: '1px solid rgba(255,180,80,0.45)', color: '#ffe4bc' }}>
            LangSmith is not enabled on the backend. Set LANGSMITH_API_KEY and LANGSMITH_PROJECT, then restart backend to populate this dashboard.
          </div>
        )}

        <div className="ops-stats-grid" style={{ display: 'grid', gap: '0.6rem' }}>
          <StatCard title="Total Questions" value={fmtNum(metrics.total_questions)} subtitle="Processed in selected window" />
          <StatCard title="Successful" value={fmtNum(metrics.successful_requests)} subtitle="Completed without errors" />
          <StatCard title="Failed" value={fmtNum(metrics.failed_requests)} subtitle="Trace-level failures" />
          <StatCard title="Avg Response" value={fmtMs(metrics.avg_response_time_ms)} subtitle="Overall request latency" />
          <StatCard title="Avg Retrieval" value={fmtMs(metrics.avg_retrieval_time_ms)} subtitle="Retriever stage latency" />
          <StatCard title="Avg Generation" value={fmtMs(metrics.avg_llm_generation_time_ms)} subtitle="LLM stage latency" />
          <StatCard title="Retrieved Chunks" value={fmtNum(metrics.avg_retrieved_chunks)} subtitle="Average chunks per request" />
          <StatCard title="Data Window" value={effectiveWindow >= 24 ? `${Math.round(effectiveWindow / 24)} day(s)` : `${effectiveWindow} hour(s)`} subtitle="Stats scope" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '0.65rem' }}>
          <LineChartCard title="Response Time Over Time" points={charts.response_time_over_time || []} yLabel="ms" color="#00d0ff" />
          <BarChartCard title="Questions Per Day" rows={charts.questions_per_day || []} xKey="day" yKey="count" color="#25c2ff" />
          <LineChartCard title="Average Retrieval Latency" points={charts.retrieval_latency_trend || []} yLabel="ms" color="#84b8ff" />
          <SuccessFailureCard rows={charts.success_failure || []} />
        </div>

        <div className="ops-trace-layout" style={{ display: 'grid', gridTemplateColumns: 'minmax(270px, 360px) 1fr', gap: '0.65rem', height: '100%' }}>
          <TraceList traces={traceData} selectedId={selectedTrace?.id} onSelect={handleTraceSelect} />
          <TraceDetails trace={selectedTrace} loading={traceLoading} />
        </div>
      </div>

      <style>{`
        .ops-card:hover {
          transform: translateY(-1px);
          border-color: rgba(0, 196, 255, 0.34);
          box-shadow: 0 0 34px rgba(0, 145, 255, 0.16);
        }

        .ops-btn {
          transition: transform 0.18s ease, box-shadow 0.2s ease, border-color 0.2s ease, background 0.2s ease;
          box-shadow: 0 0 0 rgba(0,0,0,0);
        }

        .ops-btn:hover {
          transform: translateY(-1px);
          border-color: rgba(0,210,255,0.56);
          box-shadow: 0 0 20px rgba(0,170,255,0.22);
        }

        .ops-btn:active {
          transform: translateY(0);
        }

        .ops-btn-primary:hover {
          background: rgba(0,58,110,0.72) !important;
        }

        .ops-btn-secondary:hover {
          background: rgba(0,28,56,0.9) !important;
        }

        .ops-trace-btn {
          transition: transform 0.18s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }

        .ops-trace-btn:hover {
          transform: translateY(-1px);
          border-color: rgba(0,200,255,0.55) !important;
          box-shadow: 0 0 16px rgba(0,140,255,0.18);
        }

        .ops-stats-grid {
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .ops-trace-layout {
          height: clamp(480px, 62vh, 760px);
          align-items: stretch;
        }

        @media (max-width: 1100px) {
          .ops-stats-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
        }

        @media (max-width: 980px) {
          .ops-grid {
            grid-template-columns: 1fr;
          }

          .ops-trace-layout {
            grid-template-columns: 1fr !important;
            min-height: auto;
          }
        }

        @media (max-width: 640px) {
          .ops-stats-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  )
}

export default OperationsDashboardPage
