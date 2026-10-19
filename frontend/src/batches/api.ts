import { api } from '../services/api/client'
import type { BatchDetail, BatchListData, BatchSummary } from './types'

function queryString(params: Record<string, string | number | undefined>) {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value))
    }
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export function listBatches(params: Record<string, string | number | undefined>) {
  return api.get<BatchListData>(`/api/v1/batches${queryString(params)}`)
}

export function getBatchSummary() {
  return api.get<BatchSummary>('/api/v1/batches/summary')
}

export function getBatch(batchId: string) {
  return api.get<BatchDetail>(`/api/v1/batches/${batchId}`)
}

export function createBatch(body: unknown) {
  return api.post<BatchDetail>('/api/v1/batches', body)
}

export function updateBatch(batchId: string, body: unknown) {
  return api.patch<BatchDetail>(`/api/v1/batches/${batchId}`, body)
}

export function archiveBatch(batchId: string) {
  return api.post<BatchDetail>(`/api/v1/batches/${batchId}/archive`)
}

export function assignStudents(batchId: string, studentIds: string[]) {
  return api.post<BatchDetail>(`/api/v1/batches/${batchId}/students`, { student_ids: studentIds })
}

export function removeStudent(batchId: string, studentId: string) {
  return api.delete<BatchDetail>(`/api/v1/batches/${batchId}/students/${studentId}`)
}
