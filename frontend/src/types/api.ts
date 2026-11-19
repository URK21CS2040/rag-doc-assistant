export interface SourceCitation {
  document_id: string;
  chunk_text: string;
  score: number;
}

export interface QueryRequest {
  question: string;
  session_id?: string;
  document_ids?: string[];
}

export interface QueryResponse {
  answer: string;
  sources: SourceCitation[];
  retries: number;
  route?: string;
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
  question?: string;
  answer?: string;
}

export interface FeedbackResponse {
  status: string;
  feedback_id: string;
}

export interface IngestResponse {
  status: string;
  chunks_indexed: number;
}
