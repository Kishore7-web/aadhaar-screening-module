import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 120000,
})

export async function screenAadhaar({ document, referenceFace, offlineEkyc, caseId, persistArtifacts }) {
  const fd = new FormData()
  fd.append('document', document)
  if (referenceFace) fd.append('reference_face', referenceFace)
  if (offlineEkyc) fd.append('offline_ekyc', offlineEkyc)
  if (caseId) fd.append('case_id', caseId)
  if (persistArtifacts) fd.append('persist_artifacts', 'true')
  const res = await api.post('/api/modules/aadhaar', fd, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return res.data
}

export async function getHealth() {
  const res = await api.get('/api/health')
  return res.data
}
export async function getHealthDetails() {
  const res = await api.get('/api/health/details')
  return res.data
}
export async function listCases(limit=20) {
  const res = await api.get(`/api/cases?limit=${limit}`)
  return res.data
}
export async function getCase(caseId) {
  const res = await api.get(`/api/cases/${caseId}`)
  return res.data
}
export default api
