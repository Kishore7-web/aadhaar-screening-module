import React from 'react'
import { severityBadge } from '../utils/helpers'

export default function EvidenceTimeline({ evidence }) {
  if (!evidence || evidence.length===0) return <div style={{fontSize:13, color:'#64748b'}}>No evidence items</div>
  return (
    <div>
      {evidence.map(ev => (
        <div key={ev.evidence_id} className="evidence-item">
          <div style={{display:'flex', justifyContent:'space-between', gap:10, alignItems:'flex-start'}}>
            <div style={{fontWeight:700, fontSize:12, letterSpacing:0.4, color:'#0f4c81'}}>{ev.evidence_id} • {ev.source} • {ev.category}</div>
            <span className={`badge badge-${severityBadge(ev.severity)}`}>{ev.severity}</span>
          </div>
          <div style={{fontSize:13, marginTop:6}}>{ev.finding}</div>
          <div style={{fontSize:11, color:'#64748b', marginTop:6, display:'flex', gap:12, flexWrap:'wrap'}}>
            <span>Confidence: {ev.confidence ?? '—'} <em style={{opacity:0.7}}>({ev.confidence_basis})</em></span>
            <span>Group: {ev.group||'—'}</span>
            <span>{ev.independent_source ? 'Independent' : 'Correlated'}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
