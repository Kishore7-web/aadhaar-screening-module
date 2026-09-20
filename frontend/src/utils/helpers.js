export function statusColor(status) {
  if (!status) return 'neutral'
  const s = status.toUpperCase()
  if (s==='CLEAR') return 'success'
  if (s==='LOW_CONCERN') return 'info'
  if (s==='REVIEW') return 'warn'
  if (s==='HIGH_REVIEW') return 'danger'
  return 'neutral'
}
export function severityBadge(s) {
  const m = { INFO:'info', LOW:'neutral', MEDIUM:'warn', HIGH:'danger', CRITICAL:'danger' }
  return m[s] || 'neutral'
}
export function pillClass(status) {
  const s = (status||'').toUpperCase()
  if (s==='CLEAR') return 'pill-clear'
  if (s==='LOW_CONCERN') return 'pill-low'
  if (s==='REVIEW') return 'pill-review'
  if (s==='HIGH_REVIEW') return 'pill-high'
  return 'pill-inconclusive'
}
