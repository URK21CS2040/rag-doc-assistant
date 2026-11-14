export interface SourceCitation {
  document_id: string;
  chunk_text: string;
  score: number;
}

export interface QueryResponse {
  answer: string;
  sources: SourceCitation[];
  retries: number;
  relevance_score?: number;
  query_intent?: string;
  rewritten_query?: string;
}

export interface DocumentItem {
  id: string;
  title: string;
  content_preview: string;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
}

export interface FeedbackRequest {
  session_id: string;
  rating: 'thumbs_up' | 'thumbs_down';
  comment?: string;
}

export interface FeedbackResponse {
  status: string;
  feedback_id: string;
}

export interface IngestResponse {
  status: string;
  chunks_indexed: number;
}
