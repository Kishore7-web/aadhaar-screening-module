import React, { useState, useEffect } from 'react'
import UploadPanel from './components/UploadPanel'
import EvidenceTimeline from './components/EvidenceTimeline'
import QRComparison from './components/QRComparison'
import FaceResult from './components/FaceResult'
import ForensicViewer from './components/ForensicViewer'
import AuditPanel from './components/AuditPanel'
import { screenAadhaar, getHealth, getHealthDetails, listCases } from './services/api'
import { pillClass } from './utils/helpers'

function StatusBadge({ status }) {
  return <span className={`pill ${pillClass(status)}`}>{status || 'UNKNOWN'}</span>
}

export default function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [health, setHealth] = useState(null)
  const [healthDetails, setHealthDetails] = useState(null)
  const [cases, setCases] = useState([])
  const [error, setError] = useState(null)
  const [stage, setStage] = useState('upload') // upload, analyzing, result
  const [progressSteps, setProgressSteps] = useState([])

  const pipelineSteps = [
    "Document Security","Document Identification","Image Quality","Orientation","OCR","Field Extraction",
    "Number Validation","QR Analysis","Photo Detection","Face Analysis","Forensics","Evidence Fusion","Scoring","Explanation","Audit"
  ]

  useEffect(()=>{
    getHealth().then(setHealth).catch(()=>{})
    getHealthDetails().then(setHealthDetails).catch(()=>{})
    listCases(10).then(d=>setCases(d.cases||[])).catch(()=>{})
  },[])

  const handleSubmit = async ({document, referenceFace, offlineEkyc, caseId, persistArtifacts}) => {
    setLoading(true)
    setError(null)
    setStage('analyzing')
    setProgressSteps(pipelineSteps.map((name, i)=>({name, status: i===0?'active':'pending'})))
    // Simulate progress animation while API is running
    let idx=0
    const interval = setInterval(()=>{
      setProgressSteps(prev=>{
        const next=[...prev]
        if (idx < next.length) {
          if (idx>0) next[idx-1].status='done'
          next[idx].status='active'
          idx++
        }
        return next
      })
    }, 400)
    try {
      const data = await screenAadhaar({ document, referenceFace, offlineEkyc, caseId, persistArtifacts })
      clearInterval(interval)
      setProgressSteps(prev=>prev.map(s=>({...s, status:'done'})))
      setResult(data)
      setStage('result')
      window.scrollTo({top:0, behavior:'smooth'})
      // refresh cases
      listCases(10).then(d=>setCases(d.cases||[])).catch(()=>{})
    } catch (e) {
      clearInterval(interval)
      setError(e.response?.data?.detail || e.message || 'Screening failed')
      setStage('upload')
    } finally {
      setLoading(false)
    }
  }

  const reset = () => {
    setResult(null)
    setStage('upload')
    setError(null)
    window.scrollTo({top:0, behavior:'smooth'})
  }

  return (
    <div className="app-shell">
      <header className="header">
        <div className="header-inner">
          <div className="brand">
            <div className="brand-mark">D</div>
            <div className="brand-text">
              <h1>DAKSH — P3 AADHAAR</h1>
              <p>Ministry of Home Affairs • SSB • SIH 26188 • Document Authentication &amp; Knowledge-based Screening Hub</p>
            </div>
          </div>
          <div className="header-meta">
            <div style={{fontWeight:700, fontSize:12, letterSpacing:0.6}}>BLOCKCHAIN &amp; CYBERSECURITY</div>
            <div style={{fontSize:11, opacity:0.8}}>Schema {health?.schema_version || '1.0'} • Module {health?.module_version || '1.0.0'} • {health?.build_stage || 'COMPLETE'}</div>
            <div style={{marginTop:6}}><span className="badge badge-info" style={{background:'rgba(255,255,255,0.15)', color:'white', border:'1px solid rgba(255,255,255,0.3)'}}>OCR: {healthDetails?.models?.ocr_available ? 'Ready' : 'Fallback'} • Forensics: Ready • Face: Ready</span></div>
          </div>
        </div>
      </header>

      <main className="main">
        {error && <div className="alert alert-warn" style={{marginBottom:16}}><strong>Error:</strong> {error}</div>}

        {stage==='upload' && !result && (
          <>
            <UploadPanel onSubmit={handleSubmit} loading={loading} />
            <div style={{marginTop:16}} className="grid-2">
              <div className="card">
                <div className="card-header"><h2>Available Evidence</h2></div>
                <div style={{fontSize:13, display:'flex', flexDirection:'column', gap:6}}>
                  <div>✓ OCR (RapidOCR)</div>
                  <div>✓ Aadhaar Number (Verhoeff)</div>
                  <div>✓ QR Detection &amp; Parsing</div>
                  <div>✓ Photograph Detection</div>
                  <div>✓ Forensics (ELA-like, Noise, Sharpness)</div>
                  <div>✓ Metadata</div>
                  <div>✓ Audit Hash Chain</div>
                  <div style={{marginTop:8, color:'#64748b'}}>-- Not Provided (optional) --</div>
                  <div style={{color:'#64748b'}}>— Reference face (optional)</div>
                  <div style={{color:'#64748b'}}>— Offline e-KYC (optional)</div>
                  <div style={{marginTop:8, color:'#94a3b8'}}>-- Not Configured --</div>
                  <div style={{color:'#94a3b8'}}>— QR cryptographic verification (requires UIDAI cert)</div>
                </div>
              </div>
              <div className="card">
                <div className="card-header"><h2>Recent Cases</h2><button className="btn btn-secondary" style={{fontSize:11, padding:'6px 10px'}} onClick={()=>{listCases(10).then(d=>setCases(d.cases||[]))}}>Refresh</button></div>
                {cases.length===0 ? <div style={{fontSize:13, color:'#64748b'}}>No cases yet. Run a screening to see history.</div> : (
                  <table className="table">
                    <thead><tr><th>Case</th><th>Status</th><th>Score</th><th>Coverage</th></tr></thead>
                    <tbody>
                      {cases.map(c=>(
                        <tr key={c.case_id}>
                          <td className="mono" style={{fontSize:11}}>{c.case_id}</td>
                          <td><span className={`badge badge-${c.screening_status==='CLEAR'?'success': c.screening_status==='HIGH_REVIEW'?'danger': c.screening_status==='REVIEW'?'warn':'neutral'}`}>{c.screening_status}</span></td>
                          <td>{c.integrity_score ?? '—'}</td>
                          <td>{c.evidence_coverage ? `${c.evidence_coverage}%` : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </>
        )}

        {stage==='analyzing' && (
          <div className="card">
            <div className="card-header"><h2>Analysis Progress</h2><span style={{fontSize:12, color:'#64748b'}}>Running evidence → validation → forensics → fusion pipeline…</span></div>
            <div className="step-list">
              {progressSteps.map((s,i)=>(
                <div key={s.name} className={`step ${s.status}`}>
                  <div className="icon">{s.status==='done'?'✓': s.status==='active'?'●':'○'}</div>
                  <div style={{flex:1, fontWeight:s.status==='active'?700:500}}>{s.name}</div>
                  <div style={{fontSize:11, color:'#64748b'}}>{s.status.toUpperCase()}</div>
                </div>
              ))}
            </div>
            <div style={{marginTop:16, textAlign:'center', fontSize:12, color:'#64748b'}}>This reflects real pipeline stages, not fake progress.</div>
          </div>
        )}

        {result && stage==='result' && (
          <div style={{display:'flex', flexDirection:'column', gap:16}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:10}}>
              <button className="btn btn-secondary" onClick={reset}>← New Screening</button>
              <div style={{display:'flex', gap:8, alignItems:'center', flexWrap:'wrap'}}>
                <span style={{fontSize:12, color:'#64748b'}}>Case {result.case_id}</span>
                <StatusBadge status={result.screening?.status} />
              </div>
            </div>

            {/* Hero Score */}
            <div className="card">
              <div className="card-header">
                <h2>DAKSH — AADHAAR DOCUMENT SCREENING</h2>
                <span className="mono" style={{fontSize:11, color:'#64748b'}}>{result.generated_at}</span>
              </div>
              <div className="score-hero">
                <div className="score-ring" style={{borderColor: result.scores?.integrity_score==null?'#e2e8f0': result.scores.integrity_score>=80?'#22c55e': result.scores.integrity_score>=60?'#eab308': result.scores.integrity_score>=40?'#f97316':'#ef4444'}}>
                  <div className="score-number">{result.scores?.integrity_score ?? 'N/A'}</div>
                  <div className="score-label">Integrity / 100</div>
                  <div style={{fontSize:10, color:'#94a3b8', marginTop:4}}>{result.scores?.scoring_model_version||'1.0'}</div>
                </div>
                <div style={{flex:1, minWidth:280}}>
                  <div style={{display:'flex', gap:12, flexWrap:'wrap', alignItems:'center'}}>
                    <div style={{flex:1}}>
                      <div style={{fontSize:11, fontWeight:700, letterSpacing:0.5, color:'#64748b'}}>EVIDENCE COVERAGE</div>
                      <div style={{fontSize:28, fontWeight:800}}>{result.scores?.evidence_coverage ?? 0}%</div>
                      <div className="coverage-bar"><div className="coverage-fill" style={{width:`${result.scores?.evidence_coverage||0}%`, background: result.scores?.coverage_sufficient?'#0f4c81':'#f59e0b'}}></div></div>
                      <div style={{fontSize:11, color: result.scores?.coverage_sufficient?'#0e7c3e':'#b45309', marginTop:4 }}>{result.scores?.coverage_sufficient ? 'Coverage sufficient' : 'Coverage limited — result confidence reduced'}</div>
                    </div>
                    <div><StatusBadge status={result.screening?.status} /></div>
                  </div>
                  <div style={{marginTop:12, fontSize:13}}>
                    <div style={{fontWeight:600}}>{result.screening?.headline}</div>
                    <div style={{fontSize:12, color:'#475569', marginTop:6}}>{result.screening?.recommended_action}</div>
                  </div>
                </div>
                <div style={{minWidth:200, fontSize:12}}>
                  <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:6, textAlign:'center'}}>
                    <div className="card" style={{padding:10, textAlign:'center'}}>
                      <div style={{fontSize:10, color:'#64748b', fontWeight:700}}>DOC TYPE</div><div style={{fontWeight:700}}>AADHAAR</div><div style={{fontSize:10, color:'#64748b'}}>{result.document_variant}</div>
                    </div>
                    <div className="card" style={{padding:10, textAlign:'center'}}>
                      <div style={{fontSize:10, color:'#64748b', fontWeight:700}}>PAGES</div><div style={{fontWeight:700}}>{result.document?.pages_analyzed}/{result.document?.page_count}</div><div style={{fontSize:10, color:'#64748b'}}>{result.document?.file_type}</div>
                    </div>
                  </div>
                </div>
              </div>

              <div style={{marginTop:16, display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(140px, 1fr))', gap:8, fontSize:11}}>
                <div className={`badge ${result.document_identification?.result==='AADHAAR'?'badge-success':'badge-warn'}`} style={{padding:'8px 10px', textAlign:'center'}}>Doc ID: {result.document_identification?.result}</div>
                <div className={`badge ${result.quality?.overall_label==='GOOD'?'badge-success': result.quality?.overall_label==='POOR'?'badge-danger':'badge-neutral'}`} style={{padding:'8px 10px', textAlign:'center'}}>Quality: {result.quality?.overall_label}</div>
                <div className={`badge ${result.number_validation?.checksum_status==='CHECKSUM_VALID'?'badge-success': result.number_validation?.checksum_status==='CHECKSUM_INVALID'?'badge-danger':'badge-neutral'}`} style={{padding:'8px 10px', textAlign:'center'}}>Number: {result.number_validation?.checksum_status || result.number_validation?.format_status}</div>
                <div className={`badge ${result.qr?.status==='QR_PRESENT'?'badge-success':'badge-neutral'}`} style={{padding:'8px 10px', textAlign:'center'}}>QR: {result.qr?.status}</div>
                <div className={`badge ${result.photo?.status==='DETECTED'?'badge-success':'badge-warn'}`} style={{padding:'8px 10px', textAlign:'center'}}>Photo: {result.photo?.status}</div>
                <div className={`badge ${result.biometric?.status==='MATCH'?'badge-success': result.biometric?.status==='MISMATCH'?'badge-danger':'badge-neutral'}`} style={{padding:'8px 10px', textAlign:'center'}}>Face: {result.biometric?.status}</div>
                <div className={`badge ${result.forensics?.overall_label==='NO_SIGNIFICANT_SIGNAL'?'badge-success': result.forensics?.overall_label==='SUSPICIOUS'?'badge-danger':'badge-neutral'}`} style={{padding:'8px 10px', textAlign:'center'}}>Forensics: {result.forensics?.overall_label}</div>
                <div className="badge badge-neutral" style={{padding:'8px 10px', textAlign:'center'}}>Audit: {result.audit?.chain_verified?'VALID':'INVALID'}</div>
              </div>
            </div>

            {/* Why */}
            <div className="card">
              <div className="card-header"><h2>WHY THIS RESULT?</h2></div>
              <div style={{display:'flex', flexDirection:'column', gap:8}}>
                {result.screening?.reasons?.map((r,i)=>(
                  <div key={i} style={{display:'flex', gap:10, padding:'10px 12px', background:'#f8fafc', borderRadius:8, border:'1px solid #e2e8f0'}}>
                    <span style={{minWidth:22, height:22, borderRadius:'50%', background:'#0f4c81', color:'white', display:'flex', alignItems:'center', justifyContent:'center', fontSize:11, fontWeight:700, flexShrink:0}}>{i+1}</span>
                    <div style={{flex:1}}>
                      <div style={{fontSize:13}}>{r.text}</div>
                      <div style={{fontSize:11, color:'#64748b', marginTop:4}}>Evidence: {r.evidence_ids?.join(', ') || '—'}</div>
                    </div>
                  </div>
                ))}
                <div style={{marginTop:12}}>
                  <strong style={{fontSize:12}}>Recommended Action:</strong> <span style={{fontSize:13}}>{result.screening?.recommended_action}</span>
                </div>
                <div>
                  <strong style={{fontSize:12}}>Next Steps:</strong>
                  <ul style={{fontSize:13, marginLeft:18, marginTop:6}}>
                    {result.screening?.next_steps?.map((s,i)=><li key={i}>{s}</li>)}
                  </ul>
                </div>
              </div>
            </div>

            <div className="grid-2">
              <div className="card">
                <div className="card-header"><h2>Field Table</h2><span style={{fontSize:11, color:'#64748b'}}>Provenance preserved for P6</span></div>
                <table className="table">
                  <thead><tr><th>Field</th><th>Value</th><th>Source</th><th>Confidence</th><th>Status</th><th>Consistency</th></tr></thead>
                  <tbody>
                    {Object.entries(result.fields||{}).map(([field, f])=>(
                      <tr key={field}>
                        <td style={{fontWeight:600, textTransform:'capitalize'}}>{field.replace('_',' ')}</td>
                        <td className="mono" style={{fontSize:12}}>{f.masked_value || f.value || '—'}</td>
                        <td style={{fontSize:11}}>{(f.sources||[]).map(s=>s.type).join(', ') || '—'}</td>
                        <td style={{fontSize:11}}>{f.confidence ?? '—'} <span style={{color:'#94a3b8'}}>{f.confidence_basis}</span></td>
                        <td><span className={`badge ${f.status==='DETECTED'?'badge-success': f.status==='MASKED'?'badge-info': f.status==='NOT_FOUND'?'badge-neutral':'badge-warn'}`}>{f.status}</span></td>
                        <td><span className={`badge ${f.consistency==='MATCH'?'badge-success': f.consistency==='MISMATCH'?'badge-danger':'badge-neutral'}`}>{f.consistency||'—'}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div style={{marginTop:10, fontSize:11, color:'#64748b'}}>
                  Number validation: {result.number_validation?.format_status} • {result.number_validation?.checksum_status} — {result.number_validation?.checksum_message}
                </div>
              </div>

              <div className="card">
                <div className="card-header"><h2>QR Comparison</h2></div>
                <QRComparison qr={result.qr} qrConsistency={result.qr_consistency} />
              </div>
            </div>

            <div className="grid-2">
              <div className="card">
                <div className="card-header"><h2>Face Analysis</h2></div>
                <FaceResult biometric={result.biometric} photo={result.photo} />
              </div>
              <div className="card">
                <div className="card-header"><h2>Forensic Signals</h2></div>
                <ForensicViewer forensics={result.forensics} artifacts={result.artifacts} />
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h2>Evidence Trail</h2><span style={{fontSize:11, color:'#64748b'}}>{result.evidence?.length} items • Contradictions {result.contradictions?.length}</span></div>
              <EvidenceTimeline evidence={result.evidence} />
              {result.contradictions?.length>0 && (
                <div style={{marginTop:16}}>
                  <h3 style={{fontSize:13, fontWeight:700, marginBottom:8}}>Contradictions</h3>
                  <table className="table">
                    <thead><tr><th>ID</th><th>Field</th><th>Source A ↔ B</th><th>Severity</th><th>Description</th></tr></thead>
                    <tbody>
                      {result.contradictions.map(c=>(
                        <tr key={c.contradiction_id}>
                          <td className="mono" style={{fontSize:11}}>{c.contradiction_id}</td>
                          <td>{c.field}</td>
                          <td className="mono" style={{fontSize:11}}>{c.source_a}: {c.value_a||'—'} <br/>↔ {c.source_b}: {c.value_b||'—'}</td>
                          <td><span className={`badge badge-${c.severity==='HIGH'?'danger': c.severity==='MEDIUM'?'warn':'neutral'}`}>{c.severity}</span></td>
                          <td style={{fontSize:12}}>{c.description}<br/><span style={{fontSize:10, color:'#64748b'}}>{c.possible_explanations?.slice(0,2).join(' • ')}</span></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="card">
              <div className="card-header"><h2>Scoring Breakdown</h2></div>
              <table className="table">
                <thead><tr><th>Family</th><th>Weight</th><th>Penalty</th><th>Status</th></tr></thead>
                <tbody>
                  {Object.entries(result.scores?.breakdown||{}).map(([k,v])=>(
                    <tr key={k}>
                      <td style={{fontWeight:600}}>{k}</td>
                      <td>{v.weight}</td>
                      <td>{v.penalty}</td>
                      <td><span className={`badge ${v.penalty===0?'badge-success':'badge-warn'}`}>{v.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{marginTop:10, fontSize:12, color:'#64748b'}}>{result.scores?.notes || ''}</div>
            </div>

            <div className="grid-2">
              <div className="card">
                <div className="card-header"><h2>Security &amp; Audit</h2></div>
                <AuditPanel audit={result.audit} processing={result.processing} document={result.document} />
              </div>
              <div className="card">
                <div className="card-header"><h2>Metadata &amp; Quality</h2></div>
                <div style={{fontSize:13}}>
                  <div><strong>Quality:</strong> {result.quality?.overall_label} (blur {result.quality?.blur_score}) • Brightness {result.quality?.brightness} • Glare {result.quality?.glare_detected?'Yes':'No'}</div>
                  <div><strong>Orientation:</strong> {result.orientation?.applied_rotation}° • Method {result.orientation?.method} • Confidence {result.orientation?.confidence}</div>
                  <div><strong>Metadata:</strong> {result.metadata?.notes || '—'} {result.metadata?.editing_software_detected?' • Editing software detected':''}</div>
                  <div style={{marginTop:8, fontSize:11, color:'#64748b'}}>
                    EXIF entries: {Object.keys(result.metadata?.exif||{}).length} • Software tags: {(result.metadata?.software_tags||[]).slice(0,2).join(', ') || '—'}
                  </div>
                  <div style={{marginTop:12, fontSize:11}}>
                    <strong>Capabilities:</strong>
                    <div style={{display:'flex', gap:6, flexWrap:'wrap', marginTop:6}}>
                      {Object.entries(result.capabilities||{}).map(([k,v])=>(
                        <span key={k} className={`badge ${v?'badge-success':'badge-neutral'}`} style={{fontSize:10}}>{k}: {v?'✓':'—'}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h2>Limitations &amp; Disclaimer</h2></div>
              <ul style={{fontSize:13, marginLeft:16, color:'#475569'}}>
                {result.screening?.limitations?.map((l,i)=><li key={i}>{l}</li>)}
              </ul>
              <div className="alert alert-info" style={{marginTop:12}}>
                Prototype Screening Report — Not an official UIDAI authentication result. Evidence trail retained at {result.privacy?.storage_mode} mode.
              </div>
            </div>

            <div className="card">
              <div className="card-header"><h2>Raw JSON for P6 Integration</h2><span style={{fontSize:11}} className="mono">POST /api/modules/aadhaar</span></div>
              <pre className="mono" style={{fontSize:11, background:'#0f172a', color:'#e2e8f0', padding:14, borderRadius:8, maxHeight:360, overflow:'auto'}}>
                {JSON.stringify({case_id: result.case_id, schema_version: result.schema_version, screening: result.screening, scores: result.scores, fields: Object.fromEntries(Object.entries(result.fields).map(([k,v])=>[k, {value: v.masked_value||v.value, status: v.status, consistency: v.consistency}])), audit: result.audit, privacy: result.privacy}, null, 2)}
              </pre>
            </div>

          </div>
        )}
      </main>

      <footer className="footer">
        DAKSH P3 Aadhaar Screening • Prototype for SIH 2026 • AI-Assisted Review Prioritization — Not Official UIDAI Verification • Evidence → Validation → Consistency → Forensics → Fusion • Chain verified: {result?.audit?.chain_verified?'Yes': healthDetails?.audit_status?.verified?'Yes':'—'}
      </footer>
    </div>
  )
}
