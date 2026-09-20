import React from 'react'

export default function AuditPanel({ audit, processing, document }) {
  const a = audit || {}
  const d = document || {}
  return (
    <div style={{fontSize:13, lineHeight:1.8}}>
      <div><strong>Case ID:</strong> <span className="mono">{a.case_id || d.sha256?.slice(0,12) || '—'}</span></div>
      <div><strong>Document SHA-256:</strong> <span className="mono" style={{wordBreak:'break-all'}}>{a.document_hash || d.sha256 || '—'}</span></div>
      <div><strong>Manifest Hash:</strong> <span className="mono" style={{wordBreak:'break-all'}}>{a.manifest_hash || '—'}</span></div>
      <div><strong>Audit Event:</strong> {a.chain_event_id || '—'} <span className="mono" style={{fontSize:11}}>• {a.chain_event_hash?.slice(0,20)}…</span></div>
      <div><strong>Previous Hash:</strong> <span className="mono" style={{fontSize:11}}>{a.previous_hash || 'GENESIS'}</span></div>
      <div><strong>Chain Verified:</strong> {a.chain_verified ? '✅ VALID' : '❌ INVALID'}</div>
      <div><strong>Blockchain:</strong> {a.blockchain_status || 'NOT_CONFIGURED'}</div>
      <div><strong>Generated At:</strong> {a.timestamp || ''}</div>
      <div><strong>Processing:</strong> {processing?.duration_ms ? `${processing.duration_ms} ms` : '—'} • {processing?.pipeline_stage || ''}</div>
      <div style={{marginTop:8, fontSize:11, color:'#64748b'}}>{a.notes || ''}</div>
    </div>
  )
}
