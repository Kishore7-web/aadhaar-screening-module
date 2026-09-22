import { useRef, useState } from 'react'

export default function UploadPanel({ onSubmit, disabled }) {
  const inputRef = useRef(null)
  const faceRef = useRef(null)
  const ekycRef = useRef(null)
  const [file, setFile] = useState(null)
  const [referenceFace, setReferenceFace] = useState(null)
  const [offlineEkyc, setOfflineEkyc] = useState(null)
  const [caseId, setCaseId] = useState('')
  const [dragging, setDragging] = useState(false)

  function choose(f) {
    if (!f) return
    setFile(f)
  }

  function submit(e) {
    e.preventDefault()
    if (!file || disabled) return
    onSubmit({ document: file, referenceFace, offlineEkyc, caseId, persistArtifacts: false })
  }

  return (
    <form className="upload-panel" onSubmit={submit}>
      <div className="upload-title">
        <div>
          <div className="eyebrow">START A NEW CASE</div>
          <h2>Bring a document into review</h2>
          <p>Use a clear JPG, PNG or PDF. The system will use only the checks available for the submitted evidence.</p>
        </div>
        <span className="status-pill good">Local screening</span>
      </div>

      <div
        className={`dropzone ${dragging ? 'dragging' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); choose(e.dataTransfer.files?.[0]) }}
        onClick={() => inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".jpg,.jpeg,.png,.pdf" onChange={(e) => choose(e.target.files?.[0])} />
        <div>
          <div className="upload-icon">↑</div>
          <strong>{file ? 'Document selected' : 'Drop the Aadhaar document here'}</strong>
          <span>{file ? 'Click to choose a different file' : 'or click to browse • JPG, PNG, PDF'}</span>
        </div>
      </div>

      {file && <div className="selected-file">Selected: <strong>{file.name}</strong> • {(file.size / 1024 / 1024).toFixed(2)} MB</div>}

      <div className="form-row">
        <div className="field">
          <label>Case ID (optional)</label>
          <input value={caseId} onChange={(e) => setCaseId(e.target.value)} placeholder="e.g. CASE-001" />
        </div>
        <div className="field">
          <label>Reference face (optional)</label>
          <button type="button" className="file-button" onClick={() => faceRef.current?.click()}>
            {referenceFace ? referenceFace.name : 'Choose reference image'}
          </button>
          <input ref={faceRef} hidden type="file" accept=".jpg,.jpeg,.png" onChange={(e) => setReferenceFace(e.target.files?.[0] || null)} />
        </div>
      </div>

      <div className="field" style={{marginTop:13}}>
        <label>Offline eKYC evidence (optional)</label>
        <button type="button" className="file-button" onClick={() => ekycRef.current?.click()}>
          {offlineEkyc ? offlineEkyc.name : 'Choose XML / eKYC file'}
        </button>
        <input ref={ekycRef} hidden type="file" accept=".xml" onChange={(e) => setOfflineEkyc(e.target.files?.[0] || null)} />
      </div>

      <label className="check-option">
        <input type="checkbox" defaultChecked />
        <span>I understand this is an automated screening aid. Any final identity decision must follow the authorised verification process.</span>
      </label>

      <div className="privacy-note">
        <strong>Privacy by design.</strong> For development and demonstration, use synthetic or authorised test documents whenever possible. Avoid sending real Aadhaar data to unapproved third-party services.
      </div>

      <button className="primary-button" disabled={!file || disabled}>
        {disabled ? 'Connecting to screening service…' : 'Start document screening →'}
      </button>
    </form>
  )
}
