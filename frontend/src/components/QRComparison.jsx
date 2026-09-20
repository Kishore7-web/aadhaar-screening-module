import React from 'react'

export default function QRComparison({ qr, qrConsistency }) {
  const status = qr?.status || 'QR_NOT_PRESENT'
  const items = qrConsistency?.items || []
  return (
    <div>
      <div style={{display:'flex', gap:12, alignItems:'center', marginBottom:12, flexWrap:'wrap'}}>
        <span className={`badge ${status==='QR_PRESENT'?'badge-success': status==='QR_UNREADABLE'?'badge-warn':'badge-neutral'}`}>{status}</span>
        <span style={{fontSize:12, color:'#64748b'}}>{qr?.notes || ''}</span>
        {qr?.decoded && <span style={{fontSize:12}}>Fields decoded: {Object.keys(qr.fields||{}).join(', ') || '—'}</span>}
      </div>
      {qr?.decoded && qr.fields && (
        <div style={{fontSize:12, background:'#f8fafc', padding:10, borderRadius:8, marginBottom:12}}>
          <strong>QR Fields:</strong>
          <div style={{marginTop:6, display:'grid', gridTemplateColumns:'1fr 1fr', gap:6}}>
            {Object.entries(qr.fields).slice(0,12).map(([k,v])=>(
              <div key={k}><span style={{fontWeight:600}}>{k}:</span> {String(v).slice(0,80)}</div>
            ))}
          </div>
        </div>
      )}
      {items.length>0 ? (
        <table className="table">
          <thead><tr><th>Field</th><th>Printed/OCR</th><th>QR</th><th>Result</th></tr></thead>
          <tbody>
            {items.map((it, i)=>(
              <tr key={i}>
                <td style={{fontWeight:600}}>{it.field}</td>
                <td className="mono" style={{fontSize:12}}>{it.printed_value || '—'}</td>
                <td className="mono" style={{fontSize:12}}>{it.qr_value || '—'}</td>
                <td><span className={`badge ${it.result==='MATCH'?'badge-success': it.result==='MISMATCH'?'badge-danger':'badge-neutral'}`}>{it.result}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div style={{fontSize:13, color:'#64748b'}}>No QR comparison available — {qrConsistency?.overall || 'NOT_CHECKED'}</div>
      )}
    </div>
  )
}
