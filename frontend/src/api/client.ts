import { QueryResponse, DocumentListResponse, FeedbackRequest, FeedbackResponse, IngestResponse, UrlIngestResponse } from '../types/api';

const API_BASE = '/api';

export async function submitQuery(
  question: string,
  sessionId: string,
  documentIds?: string[]
): Promise<QueryResponse> {
  const payload: { question: string; session_id: string; document_ids?: string[] } = {
    question,
    session_id: sessionId,
  };
  if (documentIds && documentIds.length > 0) {
    payload.document_ids = documentIds;
  }

  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let msg = 'Failed to fetch query response';
    try {
      const err = await response.json();
      if (err?.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return response.json();
}

export async function fetchDocuments(): Promise<DocumentListResponse> {
  const response = await fetch(`${API_BASE}/documents`);
  if (!response.ok) {
    throw new Error('Failed to fetch documents');
  }
  return response.json();
}

export async function submitFeedback(payload: FeedbackRequest): Promise<FeedbackResponse> {
  const response = await fetch(`${API_BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error('Failed to submit feedback');
  }
  return response.json();
}

export async function ingestSamples(): Promise<IngestResponse> {
  const response = await fetch(`${API_BASE}/ingest/samples`, {
    method: 'POST',
  });
  if (!response.ok) {
    let msg = 'Failed to ingest sample documents';
    try {
      const err = await response.json();
      if (err?.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return response.json();
}

export async function uploadDocument(file: File): Promise<IngestResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    let errorMsg = 'Failed to upload document';
    try {
      const err = await response.json();
      if (err?.detail) errorMsg = err.detail;
    } catch {}
    throw new Error(errorMsg);
  }
  return response.json();
}

export async function ingestUrl(url: string): Promise<UrlIngestResponse> {
  const response = await fetch(`${API_BASE}/ingest/url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!response.ok) {
    let errorMsg = 'Failed to index URL';
    try {
      const err = await response.json();
      if (err?.detail) errorMsg = err.detail;
    } catch {}
    throw new Error(errorMsg);
  }
  return response.json();
}

export async function deleteDocument(documentId: string): Promise<{ status: string; document_id: string }> {
  // If it's a URL, pass via query parameter to prevent slash mangling in path routing
  const isUrl = documentId.startsWith('http://') || documentId.startsWith('https://');
  const endpoint = isUrl
    ? `${API_BASE}/documents?document_id=${encodeURIComponent(documentId)}`
    : `${API_BASE}/documents/${encodeURIComponent(documentId.split('/').pop() || documentId)}`;

  const response = await fetch(endpoint, {
    method: 'DELETE',
  });
  if (!response.ok) {
    let msg = 'Failed to delete document';
    try {
      const err = await response.json();
      if (err?.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return response.json();
}

export async function deleteAllDocuments(): Promise<{ status: string; message: string; files_deleted: number; chunks_deleted: number }> {
  const response = await fetch(`${API_BASE}/documents`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    let msg = 'Failed to delete all documents';
    try {
      const err = await response.json();
      if (err?.detail) msg = err.detail;
    } catch {}
    throw new Error(msg);
  }
  return response.json();
}
