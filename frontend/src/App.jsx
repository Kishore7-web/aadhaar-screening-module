import { useMemo, useRef, useState } from 'react'
import { screenAadhaar } from './services/api'

const pretty = (value) => {
  if (value === null || value === undefined || value === '') return 'Not available'
  return String(value).replaceAll('_', ' ')
}

const normalizeStatus = (value) => String(value ?? 'NOT_CHECKED').toUpperCase()

function statusTone(value) {
  const s = normalizeStatus(value)
  if (['PASS','PASSED','MATCH','VALID','GOOD','DETECTED','CHECKSUM_VALID','NO_SIGNIFICANT_SIGNAL','CLEAR','LOW_CONCERN'].some(x => s.includes(x))) return 'good'
  if (['WARN','WARNING','REVIEW','LOW_CONFIDENCE','MEDIUM','PARTIAL','NOT_CHECKED','NOT_AVAILABLE','INCONCLUSIVE'].some(x => s.includes(x))) return 'warn'
  if (['FAIL','FAILED','MISMATCH','INVALID','BAD','SUSPICIOUS','HIGH_REVIEW'].some(x => s.includes(x))) return 'bad'
  return 'neutral'
}

function Status({ value, label }) {
  return <span className={`status ${statusTone(value)}`}>{label || pretty(value)}</span>
}

function Score({ value }) {
  const score = Number.isFinite(Number(value)) ? Math.max(0, Math.min(100, Number(value))) : null
  return (
    <div className="score-wrap">
      <div className="score-ring" style={{ '--score': `${score ?? 0}%` }}>
        <div className="score-center">
          <strong>{score ?? '—'}</strong>
          <span>/ 100</span>
        </div>
      </div>
      <div className="score-caption">
        <strong>Document Integrity Score</strong>
        <span>Evidence-based screening signal, not an official authentication result.</span>
      </div>
    </div>
  )
}

function Stat({ label, value, hint }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </div>
  )
}

function Section({ eyebrow, title, children, action }) {
  return (
    <section className="section-card">
      <div className="section-top">
        <div>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

function valueForReason(reason) {
  if (typeof reason === 'string') return { text: reason, evidence: [] }
  return { text: reason?.text || reason?.message || JSON.stringify(reason), evidence: reason?.evidence_ids || [] }
}

function FieldRows({ fields }) {
  const entries = Object.entries(fields || {})
  if (!entries.length) return <div className="empty">No fields were returned by the backend.</div>
  return (
    <div className="field-list">
      {entries.map(([key, item]) => {
        const f = item && typeof item === 'object' ? item : { value: item }
        const sources = Array.isArray(f.sources) ? f.sources.map(s => s?.type || s).join(', ') : (f.source || '—')
        const display = f.masked_value || f.value || f.text || '—'
        return (
          <div className="field-item" key={key}>
            <div className="field-name">{key.replaceAll('_', ' ')}</div>
            <div className="field-value mono">{String(display)}</div>
            <div className="field-source">{sources}</div>
            <div className="field-meta">
              <span>{f.confidence ?? '—'}</span>
              <Status value={f.status || f.consistency || 'NOT_CHECKED'} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function EvidenceList({ evidence }) {
  if (!Array.isArray(evidence) || evidence.length === 0) {
    return <div className="empty">No separate evidence records were returned.</div>
  }
  return (
    <div className="timeline">
      {evidence.map((e, i) => (
        <div className="timeline-item" key={e?.evidence_id || i}>
          <div className="timeline-dot"></div>
          <div>
            <div className="timeline-title">
              <strong>{e?.evidence_id || `E-${i + 1}`}</strong>
              <Status value={e?.status || e?.result || 'RECORDED'} />
            </div>
            <p>{e?.description || e?.message || e?.finding || JSON.stringify(e)}</p>
            <small>{e?.type || e?.source || 'screening'}{e?.provenance ? ` • ${e.provenance}` : ''}</small>
          </div>
        </div>
      ))}
    </div>
  )
}

function TechnicalCheck({ label, value, detail }) {
  return (
    <div className="tech-row">
      <div>
        <strong>{label}</strong>
        {detail && <span>{detail}</span>}
      </div>
      <Status value={value} />
    </div>
  )
}

function ResultPage({ result, onNew }) {
  const screening = result?.screening || {}
  const score = result?.scores?.integrity_score
  const coverage = result?.scores?.evidence_coverage ?? 0
  const reasons = (screening.reasons || []).map(valueForReason)
  const [tab, setTab] = useState('overview')

  const checks = useMemo(() => ([
    ['Document identification', result?.document_identification?.result, 'Expected Aadhaar structure'],
    ['Image quality', result?.quality?.overall_label, 'Readability / image condition'],
    ['Aadhaar number', result?.number_validation?.checksum_status || result?.number_validation?.format_status, 'Format and checksum analysis'],
    ['QR analysis', result?.qr?.status, 'QR presence and decoding evidence'],
    ['Photo detection', result?.photo?.status, 'Photo region detection'],
    ['Face comparison', result?.biometric?.status, 'Runs only when a reference face is supplied'],
    ['Forensic analysis', result?.forensics?.overall_label, 'Image-level manipulation signals'],
    ['Audit chain', result?.audit?.chain_verified ? 'VALID' : 'NOT_VERIFIED', 'Tamper-evident local audit record']
  ]), [result])

  return (
    <div>
      <div className="result-head">
        <div>
          <div className="eyebrow">SCREENING REPORT</div>
          <h1>{screening.headline || 'Document screening completed.'}</h1>
          <p>{screening.recommended_action || 'Review the available evidence before making any final identity decision.'}</p>
          <div className="head-meta">
            <span>Case: <strong>{result?.case_id || 'Not assigned'}</strong></span>
            <span>Document: <strong>{result?.document_variant || 'Aadhaar'}</strong></span>
            <span>Generated: <strong>{result?.generated_at || '—'}</strong></span>
          </div>
        </div>
        <button className="button secondary" onClick={onNew}>← New screening</button>
      </div>

      <div className="decision-card">
        <div className="decision-primary">
          <Score value={score} />
        </div>
        <div className="decision-side">
          <div className="decision-status">
            <span className="label">SCREENING STATUS</span>
            <Status value={screening.status || 'INCONCLUSIVE'} />
          </div>
          <div className="coverage-block">
            <div className="coverage-head"><span>Evidence coverage</span><strong>{Math.round(Number(coverage) || 0)}%</strong></div>
            <div className="coverage-bar"><i style={{ width: `${Math.max(0, Math.min(100, Number(coverage) || 0))}%` }} /></div>
            <small>{result?.scores?.coverage_sufficient === false ? 'Some checks could not be completed. Interpret the score with caution.' : 'The available evidence was sufficient for the current screening.'}</small>
          </div>
        </div>
      </div>

      <div className="human-banner">
        <div className="human-icon">♡</div>
        <div>
          <strong>People deserve careful verification.</strong>
          <span>DAKSH brings multiple evidence sources together so a reviewer can see what was checked, what was not checked, and why further review may be needed.</span>
        </div>
      </div>

      <div className="tabs">
        {[
          ['overview', 'Overview'],
          ['evidence', 'Evidence'],
          ['technical', 'Technical'],
          ['integration', 'Integration']
        ].map(([id, text]) => (
          <button key={id} className={tab === id ? 'active' : ''} onClick={() => setTab(id)}>{text}</button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="content-grid">
          <Section eyebrow="DECISION CONTEXT" title="Why this result?">
            {reasons.length ? (
              <div className="reason-list">
                {reasons.map((r, i) => (
                  <div className="reason" key={i}>
                    <span>{String(i + 1).padStart(2, '0')}</span>
                    <div>
                      <strong>{r.text}</strong>
                      {r.evidence.length > 0 && <small>Evidence: {r.evidence.join(', ')}</small>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty">The backend did not return a detailed reason list.</div>
            )}
            <div className="recommend">
              <span>Recommended action</span>
              <strong>{screening.recommended_action || 'Review available evidence and use authorised secondary verification where required.'}</strong>
            </div>
          </Section>

          <Section eyebrow="AT A GLANCE" title="Screening checks">
            <div className="tech-list">
              {checks.map(([label, value, detail]) => <TechnicalCheck key={label} label={label} value={value || 'NOT_CHECKED'} detail={detail} />)}
            </div>
          </Section>

          <Section eyebrow="EXTRACTED INFORMATION" title="Field evidence" action={<span className="micro">Provenance preserved</span>}>
            <div className="field-header"><span>Field</span><span>Value</span><span>Source</span><span>Review</span></div>
            <FieldRows fields={result?.fields} />
          </Section>

          <Section eyebrow="QR CONSISTENCY" title="Printed information ↔ QR evidence">
            {result?.qr_consistency?.comparisons ? (
              <div className="compare-list">
                {Object.entries(result.qr_consistency.comparisons).map(([k, v]) => (
                  <div className="compare-row" key={k}><span>{k.replaceAll('_',' ')}</span><strong>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</strong><Status value={v?.status || v} /></div>
                ))}
              </div>
            ) : (
              <div className="compare-grid">
                <Stat label="QR status" value={pretty(result?.qr?.status)} />
                <Stat label="QR fields" value={result?.qr?.fields ? Object.keys(result.qr.fields).length : '—'} />
                <Stat label="Consistency" value={pretty(result?.qr_consistency?.status || 'NOT_CHECKED')} />
              </div>
            )}
          </Section>

          <Section eyebrow="FACE" title="Optional face comparison">
            <div className="face-box">
              <div className="face-symbol">◉</div>
              <div>
                <Status value={result?.biometric?.status || 'NOT_CHECKED'} />
                <p>{result?.biometric?.message || 'No reference face was supplied, so no face comparison was performed.'}</p>
                <small>This is an additional comparison signal, not biometric authentication.</small>
              </div>
            </div>
          </Section>

          <Section eyebrow="IMAGE FORENSICS" title="Manipulation signals">
            <div className="forensic-top">
              <Status value={result?.forensics?.overall_label || result?.forensics?.status || 'NOT_CHECKED'} />
              <span>{result?.forensics?.message || 'No forensic summary was returned.'}</span>
            </div>
            {Array.isArray(result?.forensics?.findings) && result.forensics.findings.length > 0 && (
              <div className="finding-list">{result.forensics.findings.slice(0, 10).map((x, i) => <div key={i}>{typeof x === 'string' ? x : JSON.stringify(x)}</div>)}</div>
            )}
          </Section>
        </div>
      )}

      {tab === 'evidence' && (
        <div className="single-column">
          <Section eyebrow="EVIDENCE TRAIL" title="What the system recorded" action={<span className="micro">{Array.isArray(result?.evidence) ? result.evidence.length : 0} evidence items</span>}>
            <EvidenceList evidence={result?.evidence} />
          </Section>
          <Section eyebrow="CONTRADICTIONS" title="Conflicting signals">
            {(result?.contradictions || []).length ? (
              <div className="contradiction-list">
                {result.contradictions.map((c, i) => (
                  <div className="contradiction" key={c?.contradiction_id || i}>
                    <div><strong>{c?.field || 'Field'}</strong><Status value={c?.severity || 'REVIEW'} /></div>
                    <p>{c?.description || 'Contradictory values were reported by different evidence sources.'}</p>
                    <small>{c?.source_a || 'Source A'}: {c?.value_a || '—'} ↔ {c?.source_b || 'Source B'}: {c?.value_b || '—'}</small>
                  </div>
                ))}
              </div>
            ) : <div className="empty">No contradictions were returned.</div>}
          </Section>
        </div>
      )}

      {tab === 'technical' && (
        <div className="content-grid">
          <Section eyebrow="SCORING" title="Transparent scoring breakdown">
            <div className="score-table">
              {Object.entries(result?.scores?.breakdown || {}).map(([k, v]) => (
                <div key={k} className="score-line">
                  <div><strong>{k.replaceAll('_',' ')}</strong><span>Weight {v?.weight ?? '—'}</span></div>
                  <strong>{v?.penalty ?? 0}</strong>
                  <Status value={v?.status || (Number(v?.penalty || 0) === 0 ? 'PASS' : 'REVIEW')} />
                </div>
              ))}
            </div>
            {result?.scores?.notes && <p className="muted">{result.scores.notes}</p>}
          </Section>

          <Section eyebrow="QUALITY & METADATA" title="Input condition">
            <div className="mini-grid">
              <Stat label="Quality" value={pretty(result?.quality?.overall_label)} hint={`Blur ${result?.quality?.blur_score ?? '—'}`} />
              <Stat label="Brightness" value={result?.quality?.brightness ?? '—'} hint={result?.quality?.glare_detected ? 'Glare detected' : 'No glare reported'} />
              <Stat label="Rotation" value={`${result?.orientation?.applied_rotation ?? 0}°`} hint={pretty(result?.orientation?.method)} />
              <Stat label="Software tag" value={result?.metadata?.editing_software_detected ? 'Detected' : 'Not detected'} hint={result?.metadata?.notes || ''} />
            </div>
          </Section>

          <Section eyebrow="CAPABILITIES" title="Available checks">
            <div className="capability-grid">
              {Object.entries(result?.capabilities || {}).map(([k, v]) => (
                <div key={k}><span>{k.replaceAll('_',' ')}</span><Status value={v ? 'AVAILABLE' : 'UNAVAILABLE'} /></div>
              ))}
            </div>
          </Section>
        </div>
      )}

      {tab === 'integration' && (
        <div className="single-column">
          <Section eyebrow="P6 HANDOFF" title="Machine-readable result">
            <div className="api-note">Primary endpoint: <code>POST /api/modules/aadhaar</code></div>
            <pre className="json-box">{JSON.stringify(result, null, 2)}</pre>
          </Section>
          <Section eyebrow="PRIVACY & TRUST" title="What this prototype does not claim">
            <div className="trust-grid">
              <div><span>UIDAI authentication</span><strong>Not performed</strong></div>
              <div><span>Official database lookup</span><strong>Not connected</strong></div>
              <div><span>Final identity decision</span><strong>Human review required</strong></div>
              <div><span>Raw PII retention</span><strong>{result?.privacy?.pii_stored === false ? 'Disabled' : 'Depends on configuration'}</strong></div>
            </div>
          </Section>
        </div>
      )}

      <div className="result-foot">
        <span>Prototype screening report • Evidence → validation → consistency → forensics → review</span>
        <span>Not an official UIDAI authentication result</span>
      </div>
    </div>
  )
}

function UploadPanel({ onSubmit, busy }) {
  const input = useRef(null)
  const faceInput = useRef(null)
  const ekycInput = useRef(null)
  const [file, setFile] = useState(null)
  const [face, setFace] = useState(null)
  const [ekyc, setEkyc] = useState(null)
  const [caseId, setCaseId] = useState('')
  const [drag, setDrag] = useState(false)

  const pick = (f) => { if (f) setFile(f) }

  function submit(e) {
    e.preventDefault()
    if (!file || busy) return
    onSubmit({ document: file, referenceFace: face, offlineEkyc: ekyc, caseId, persistArtifacts: false })
  }

  return (
    <form className="upload-card" onSubmit={submit}>
      <div className="upload-head">
        <div>
          <div className="eyebrow">NEW SCREENING CASE</div>
          <h2>Start with the document.</h2>
          <p>Bring in the evidence first. DAKSH will show what could actually be checked.</p>
        </div>
        <span className="status good">LOCAL PROTOTYPE</span>
      </div>

      <div
        className={`drop-area ${drag ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]) }}
        onClick={() => input.current?.click()}
      >
        <input ref={input} hidden type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => pick(e.target.files?.[0])} />
        <div className="upload-glyph">+</div>
        <strong>{file ? 'Document selected' : 'Drop your Aadhaar document here'}</strong>
        <span>{file ? 'Click to select another file' : 'JPG / JPEG / PNG / PDF'}</span>
      </div>

      {file && <div className="file-pill"><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></div>}

      <div className="upload-grid">
        <label className="input-box">
          <span>Case ID <small>optional</small></span>
          <input value={caseId} onChange={(e) => setCaseId(e.target.value)} placeholder="CASE-001" />
        </label>

        <div className="input-box">
          <span>Reference face <small>optional</small></span>
          <button type="button" className="file-select" onClick={() => faceInput.current?.click()}>{face ? face.name : 'Choose image'}</button>
          <input ref={faceInput} hidden type="file" accept=".jpg,.jpeg,.png" onChange={(e) => setFace(e.target.files?.[0] || null)} />
        </div>
      </div>

      <div className="input-box full">
        <span>Offline e-KYC <small>optional</small></span>
        <button type="button" className="file-select" onClick={() => ekycInput.current?.click()}>{ekyc ? ekyc.name : 'Choose XML file'}</button>
        <input ref={ekycInput} hidden type="file" accept=".xml" onChange={(e) => setEkyc(e.target.files?.[0] || null)} />
      </div>

      <div className="privacy-callout">
        <strong>Use test data for your demo.</strong>
        <span>Prefer synthetic or redacted documents. This prototype does not perform official UIDAI authentication.</span>
      </div>

      <button className="button primary wide" disabled={!file || busy}>
        {busy ? 'Screening document…' : 'START SCREENING  →'}
      </button>
    </form>
  )
}

export default function App() {
  const [page, setPage] = useState('upload')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  async function handleSubmit(payload) {
    setBusy(true)
    setError('')
    setPage('loading')
    try {
      const data = await screenAadhaar(payload)
      setResult(data)
      setPage('result')
    } catch (err) {
      const detail = err?.response?.data?.detail
      const message = typeof detail === 'string' ? detail : detail?.message || err?.message || 'The screening request failed.'
      setError(message)
      setPage('upload')
    } finally {
      setBusy(false)
    }
  }

  if (page === 'loading') {
    return (
      <div className="app">
        <Header />
        <main className="main loading-page">
          <div className="loading-line"></div>
          <div className="eyebrow">SECURE SCREENING</div>
          <h1>Reading the evidence<br/><em>one check at a time.</em></h1>
          <p>DAKSH is processing the submitted document.</p>
          <div className="loading-tags"><span>OCR</span><span>FIELDS</span><span>QR</span><span>FORENSICS</span><span>FACE</span><span>AUDIT</span></div>
        </main>
      </div>
    )
  }

  return (
    <div className="app">
      <Header />
      <main className="main">
        {page === 'upload' && (
          <>
            <div className="hero">
              <div className="hero-text">
                <div className="eyebrow">DAKSH • P3 AADHAAR SCREENING</div>
                <h1>See the document.<br/><em>See the evidence.</em></h1>
                <p>AI-assisted screening for identity documents — built to help a human reviewer understand what was detected, what is consistent, and where additional verification may be needed.</p>
                <div className="principles"><span>01 Read</span><span>02 Validate</span><span>03 Compare</span><span>04 Explain</span></div>
              </div>
              <div className="hero-side">
                <div className="quote-mark">“</div>
                <p>Every document represents a real person. The goal is not to replace judgment — it is to make the evidence easier to inspect.</p>
              </div>
            </div>

            {error && <div className="error"><strong>Screening error</strong><span>{error}</span></div>}
            <UploadPanel onSubmit={handleSubmit} busy={busy} />

            <div className="feature-row">
              <div><span>01</span><strong>Document analysis</strong><small>OCR, structure, quality and field extraction</small></div>
              <div><span>02</span><strong>Consistency checks</strong><small>Number, printed fields and QR evidence</small></div>
              <div><span>03</span><strong>Additional signals</strong><small>Face comparison, forensics and audit</small></div>
            </div>
          </>
        )}

        {page === 'result' && result && <ResultPage result={result} onNew={() => { setResult(null); setPage('upload'); setError('') }} />}
      </main>

      <footer>
        <span>DAKSH Identity Screening • Prototype</span>
        <span>Human review supported • No official UIDAI authentication</span>
      </footer>
    </div>
  )
}

function Header() {
  return (
    <header className="header">
      <div className="logo"><div className="logo-box">D</div><div><strong>DAKSH</strong><span>Identity Screening</span></div></div>
      <div className="header-right"><span className="dot"></span><span>Local screening service</span></div>
    </header>
  )
}
