import React, { useState, useRef } from 'react'

export default function UploadPanel({ onSubmit, loading }) {
  const [docFile, setDocFile] = useState(null)
  const [refFile, setRefFile] = useState(null)
  const [ekycFile, setEkycFile] = useState(null)
  const [caseId, setCaseId] = useState('')
  const [dragOver, setDragOver] = useState(false)
  const docInput = useRef(null)

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) setDocFile(f)
  }

  const submit = (e) => {
    e.preventDefault()
    if (!docFile) return alert('Please select an Aadhaar document file')
    onSubmit({ document: docFile, referenceFace: refFile, offlineEkyc: ekycFile, caseId: caseId || undefined, persistArtifacts: true })
  }

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2>DAKSH Aadhaar Screening</h2>
          <p>AI-Assisted Identity Document Analysis &amp; Evidence Screening</p>
        </div>
        <span className="badge badge-info">P3 Module • SIH 26188</span>
      </div>

      <form onSubmit={submit} style={{display:'flex', flexDirection:'column', gap:16}}>
        <div className={`upload-zone ${dragOver?'dragover':''}`}
          onDragOver={e=>{e.preventDefault(); setDragOver(true)}}
          onDragLeave={()=>setDragOver(false)}
          onDrop={handleDrop}
          onClick={()=>docInput.current?.click()}
        >
          <div style={{fontSize:28, marginBottom:8}}>📄</div>
          <div style={{fontWeight:600, fontSize:14}}>{docFile ? docFile.name : 'Drop Aadhaar document here or click to browse'}</div>
          <div style={{fontSize:12, color:'#64748b', marginTop:6}}>Supported: JPG / JPEG / PNG / PDF — Max 10 MB</div>
          <div style={{fontSize:11, color:'#94a3b8', marginTop:4}}>Prototype mode — use synthetic/sample identity documents. Official UIDAI authentication is not performed.</div>
          <input ref={docInput} type="file" accept=".jpg,.jpeg,.png,.pdf" style={{display:'none'}} onChange={e=>setDocFile(e.target.files?.[0]||null)} />
          {docFile && <div style={{marginTop:10}}><span className="badge badge-success">Selected: {docFile.name} • {(docFile.size/1024).toFixed(1)} KB</span></div>}
        </div>

        <div className="grid-2">
          <div>
            <label className="label">Reference / Current Face (optional)</label>
            <input type="file" accept=".jpg,.jpeg,.png" className="input" onChange={e=>setRefFile(e.target.files?.[0]||null)} />
            <div style={{fontSize:11, color:'#94a3b8', marginTop:4}}>Upload a live photo for face comparison</div>
            {refFile && <div style={{marginTop:6}}><span className="badge badge-info">{refFile.name}</span></div>}
          </div>
          <div>
            <label className="label">Offline e-KYC (optional)</label>
            <input type="file" accept=".xml,.zip" className="input" onChange={e=>setEkycFile(e.target.files?.[0]||null)} />
            <div style={{fontSize:11, color:'#94a3b8', marginTop:4}}>XML or ZIP from UIDAI offline eKYC</div>
            {ekycFile && <div style={{marginTop:6}}><span className="badge badge-info">{ekycFile.name}</span></div>}
          </div>
        </div>

        <div>
          <label className="label">Case ID (optional)</label>
          <input className="input" placeholder="e.g., CASE-2026-001  (auto-generated if empty)" value={caseId} onChange={e=>setCaseId(e.target.value)} />
        </div>

        <div style={{display:'flex', gap:10, alignItems:'center', flexWrap:'wrap'}}>
          <button type="submit" className="btn btn-primary" disabled={loading || !docFile}>
            {loading ? 'Screening…' : '▶ START SCREENING'}
          </button>
          <span style={{fontSize:12, color:'#64748b'}}>Secure • SHA-256 hashed • Audit logged</span>
        </div>

        <div className="alert alert-info">
          <strong>Privacy note:</strong> Documents are processed with HASH_ONLY storage by default. Synthetic test documents must include “SYNTHETIC TEST DOCUMENT” watermark. No official UIDAI verification is performed — this system prioritizes review.
        </div>
      </form>
    </div>
  )
}
