import { QueryResponse, DocumentListResponse, FeedbackRequest, FeedbackResponse, IngestResponse } from '../types/api';

const API_BASE = '/api';

export async function submitQuery(question: string, sessionId: string): Promise<QueryResponse> {
  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId })
  });
  if (!response.ok) {
    throw new Error('Failed to fetch query response');
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
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error('Failed to submit feedback');
  }
  return response.json();
}

export async function ingestSamples(): Promise<IngestResponse> {
  const response = await fetch(`${API_BASE}/ingest/samples`, {
    method: 'POST'
  });
  if (!response.ok) {
    throw new Error('Failed to ingest sample documents');
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
    throw new Error('Failed to upload document');
  }
  return response.json();
}
