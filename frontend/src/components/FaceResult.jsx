import React from 'react'

export default function FaceResult({ biometric, photo }) {
  const b = biometric || {}
  const p = photo || {}
  const status = b.status || 'NOT_CHECKED'
  const badge = status==='MATCH' ? 'badge-success' : status==='MISMATCH' ? 'badge-danger' : status==='LOW_CONFIDENCE' ? 'badge-warn' : 'badge-neutral'
  return (
    <div>
      <div style={{display:'flex', gap:10, alignItems:'center', flexWrap:'wrap', marginBottom:12}}>
        <span className={`badge ${badge}`}>{status}</span>
        <span style={{fontSize:12, color:'#64748b'}}>{b.message || b.notes || ''}</span>
      </div>
      <div className="grid-2">
        <div className="card" style={{padding:12}}>
          <div style={{fontSize:11, fontWeight:700, letterSpacing:0.5, color:'#64748b', marginBottom:8}}>DOCUMENT PHOTO</div>
          <div style={{fontSize:13, color:'#334155'}}>
            <div>Status: <strong>{p.status || '—'}</strong></div>
            <div>Quality: {p.quality_label || '—'} {p.quality_score ? `(${p.quality_score.toFixed(1)})` : ''}</div>
            <div>Bounding Box: {p.bounding_box ? p.bounding_box.join(', ') : '—'}</div>
          </div>
        </div>
        <div className="card" style={{padding:12}}>
          <div style={{fontSize:11, fontWeight:700, letterSpacing:0.5, color:'#64748b', marginBottom:8}}>REFERENCE FACE</div>
          <div style={{fontSize:13, color:'#334155'}}>
            <div>Provided: {b.has_reference ? 'Yes' : 'No'}</div>
            <div>Reference Face Found: {b.reference_face_found ? 'Yes' : 'No'}</div>
            <div>Document Face Found: {b.document_face_found ? 'Yes' : 'No'}</div>
            <div>Similarity: {b.similarity ?? '—'} {b.distance ? ` (distance ${b.distance})` : ''}</div>
            <div>Threshold: {b.threshold} • Model: {b.model}</div>
            <div>Metric: {b.metric}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
