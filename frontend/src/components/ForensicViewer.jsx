import React from 'react'

export default function ForensicViewer({ forensics, artifacts }) {
  const f = forensics || {}
  const regions = f.regions || []
  const signals = f.signals || []
  const annotated = artifacts?.items?.find(i=>i.type==='annotated_image')
  return (
    <div>
      <div style={{display:'flex', gap:10, alignItems:'center', flexWrap:'wrap', marginBottom:12}}>
        <span className={`badge ${f.overall_label==='SUSPICIOUS'?'badge-danger': f.overall_label==='NO_SIGNIFICANT_SIGNAL'?'badge-success':'badge-neutral'}`}>{f.overall_label || 'UNKNOWN'}</span>
        <span style={{fontSize:12, color:'#64748b'}}>{f.notes || ''}</span>
      </div>
      {signals.length>0 && (
        <div style={{marginBottom:12}}>
          <div style={{fontSize:12, fontWeight:600, marginBottom:6}}>Signals:</div>
          <ul style={{fontSize:13, marginLeft:16}}>
            {signals.map((s,i)=><li key={i}>{s}</li>)}
          </ul>
        </div>
      )}
      {regions.length>0 ? (
        <table className="table">
          <thead><tr><th>Region</th><th>Reason</th><th>Severity</th><th>Confidence</th><th>Method</th></tr></thead>
          <tbody>
            {regions.map(r=>(
              <tr key={r.region_id}>
                <td className="mono">{r.region_id} <br/><span style={{fontSize:11, color:'#64748b'}}>{r.bounding_box?.join(', ')}</span></td>
                <td>{r.reason}</td>
                <td><span className={`badge ${r.severity==='HIGH'?'badge-danger': r.severity==='MEDIUM'?'badge-warn':'badge-neutral'}`}>{r.severity}</span></td>
                <td>{r.confidence} <span style={{fontSize:11, color:'#64748b'}}>({r.confidence_basis})</span></td>
                <td className="mono" style={{fontSize:11}}>{r.method}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div style={{fontSize:13, color:'#64748b'}}>No suspicious regions flagged.</div>
      )}
      <div style={{marginTop:12, fontSize:12, color:'#64748b'}}>
        ELA Score: {f.ela_score ?? '—'} • Noise: {f.noise_score ? f.noise_score.toFixed(1) : '—'} • Sharpness Var: {f.sharpness_variance ? f.sharpness_variance.toFixed(1) : '—'} • Recompression: {f.recompression_detected ? 'Yes' : 'No'}
      </div>
      {annotated && <div style={{marginTop:12, fontSize:12}}>Annotated forensic image artifact: <span className="mono">{annotated.file_name}</span> (hash {annotated.hash?.slice(0,16)}…)</div>}
    </div>
  )
}
