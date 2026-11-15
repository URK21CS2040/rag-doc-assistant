import React, { useState, useEffect, useRef } from 'react';
import {
  Send,
  FileText,
  ThumbsUp,
  ThumbsDown,
  BookOpen,
  RefreshCw,
  Cpu,
  Layers,
  Upload,
  Target,
  Globe,
  ExternalLink,
  Bot,
  User,
  Copy,
  Check,
  Sparkles,
  Activity,
  ChevronDown,
  ChevronRight,
  Lightbulb,
  Compass,
  Search
} from 'lucide-react';
import { submitQuery, fetchDocuments, submitFeedback, ingestSamples, uploadDocument } from './api/client';
import { SourceCitation, DocumentItem } from './types/api';
import { MarkdownView } from './components/MarkdownView';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceCitation[];
  retries?: number;
  relevance_score?: number;
  query_intent?: string;
  rewritten_query?: string;
}

function CopyResponseButton({ text }: { text: string }): React.JSX.Element {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(text).catch(() => {});
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="p-1.5 hover:text-slate-200 text-slate-400 hover:bg-slate-800 rounded-md transition-colors flex items-center gap-1 text-xs"
      title="Copy response"
    >
      {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
      <span className="text-[11px]">{copied ? 'Copied' : 'Copy'}</span>
    </button>
  );
}

function ExplainabilityDrawer({
  intent,
  rewrittenQuery,
  relevanceScore,
  retries,
  sourcesCount,
  isWebFallback
}: {
  intent?: string;
  rewrittenQuery?: string;
  relevanceScore?: number;
  retries?: number;
  sourcesCount: number;
  isWebFallback: boolean;
}): React.JSX.Element {
  const [open, setOpen] = useState(false);

  return (
    <div className="my-4 rounded-xl border border-slate-800/80 bg-slate-950/70 overflow-hidden text-xs shadow-inner">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3.5 py-2.5 text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 transition-colors"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <Activity className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-semibold text-slate-300">Pipeline Trace & Explainability</span>
          {intent && (
            <span className="bg-indigo-950 text-indigo-300 border border-indigo-800/80 px-2 py-0.5 rounded-full text-[10px] font-mono">
              Intent: {intent}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span>{open ? 'Hide details' : 'How this was generated'}</span>
          {open ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </div>
      </button>

      {open && (
        <div className="p-3.5 border-t border-slate-800/80 space-y-3 bg-slate-900/40">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {/* Intent Understanding */}
            <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1 flex items-center gap-1.5">
                <Lightbulb className="w-3.5 h-3.5 text-amber-400" /> Understood User Intent
              </div>
              <p className="font-semibold text-slate-200 text-xs">{intent || 'Technical Query'}</p>
              <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                The semantic analyzer categorized your prompt to shape the depth, code snippets, and structure of the explanation.
              </p>
            </div>

            {/* Execution Routing */}
            <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Compass className="w-3.5 h-3.5 text-cyan-400" /> Workflow Execution Path
                </span>
                {relevanceScore !== undefined && (
                  <span className="text-emerald-400 font-mono text-[10px]">
                    Score: {(relevanceScore * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              <p className="font-semibold text-slate-200 text-xs">
                {isWebFallback
                  ? '🌐 Tavily Live Web Search Fallback'
                  : sourcesCount > 0
                  ? '📁 ChromaDB Vector Knowledge Store'
                  : '🧠 Groq LLM General Technical Knowledge'}
              </p>
              <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                {retries && retries > 0
                  ? `Self-corrected with ${retries} query rewrite loop(s) before routing.`
                  : relevanceScore !== undefined && relevanceScore > 0
                  ? `Document relevance passed validation threshold with ${(relevanceScore * 100).toFixed(0)}% confidence.`
                  : 'Direct generation completed.'}
              </p>
            </div>
          </div>

          {/* Search Query Used */}
          {rewrittenQuery && (
            <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center gap-1.5">
                <Search className="w-3.5 h-3.5 text-indigo-400" /> Optimized Vector Search Query
              </div>
              <p className="font-mono text-indigo-300 text-[11px] bg-slate-950 p-2.5 rounded-md border border-slate-800 break-words leading-relaxed">
                {rewrittenQuery}
              </p>
              <p className="text-[10px] text-slate-400 mt-1.5">
                Expanded keywords and technical synonyms generated by Groq to maximize vector recall across indexed documents.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function App(): React.JSX.Element {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [sessionId] = useState<string>(() => Math.random().toString(36.25));
  const [feedbackStatus, setFeedbackStatus] = useState<string>('');
  const [ingesting, setIngesting] = useState<boolean>(false);
  const [ingestStatus, setIngestStatus] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadDocuments = (): void => {
    fetchDocuments()
      .then((data) => setDocuments(data.documents))
      .catch((error) => console.error('Failed to fetch documents:', error));
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleIngestSamples = async (): Promise<void> => {
    setIngesting(true);
    setIngestStatus('Indexing documents in sample_docs...');
    try {
      const res = await ingestSamples();
      setIngestStatus(`Success! Indexed ${res.chunks_indexed} chunks.`);
      loadDocuments();
      setTimeout(() => setIngestStatus(''), 4000);
    } catch {
      setIngestStatus('Ingestion failed. Ensure backend is running.');
      setTimeout(() => setIngestStatus(''), 4000);
    } finally {
      setIngesting(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIngesting(true);
    setIngestStatus(`Uploading and parsing ${file.name}...`);
    try {
      const res = await uploadDocument(file);
      setIngestStatus(`Success! Indexed ${res.chunks_indexed} chunks from ${file.name}.`);
      loadDocuments();
      setTimeout(() => setIngestStatus(''), 5000);
    } catch {
      setIngestStatus('Upload failed. Please check file format.');
      setTimeout(() => setIngestStatus(''), 4000);
    } finally {
      setIngesting(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const executeQuestion = async (userQuestion: string): Promise<void> => {
    if (!userQuestion.trim() || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userQuestion }]);
    setLoading(true);

    try {
      const res = await submitQuery(userQuestion, sessionId);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          retries: res.retries,
          relevance_score: res.relevance_score,
          query_intent: res.query_intent,
          rewritten_query: res.rewritten_query
        }
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: err?.message || 'The service encountered an issue processing your request. Please try again shortly.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (e: React.FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault();
    executeQuestion(input);
  };

  const handleFeedback = async (rating: 'thumbs_up' | 'thumbs_down'): Promise<void> => {
    try {
      await submitFeedback({ session_id: sessionId, rating });
      setFeedbackStatus('Thank you for your feedback!');
      setTimeout(() => setFeedbackStatus(''), 3000);
    } catch {
      setFeedbackStatus('Failed to submit feedback.');
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-80 border-r border-slate-800 bg-slate-900/95 flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h1 className="font-bold text-sm text-slate-100 leading-tight">TechDoc Assistant</h1>
              <p className="text-[11px] text-slate-400">Explainable Self-Corrective RAG</p>
            </div>
          </div>
        </div>

        <div className="p-4 flex-1 overflow-y-auto">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5" /> Indexed Documents ({documents.length})
            </h2>
            <button
              onClick={loadDocuments}
              title="Refresh document list"
              className="p-1 hover:text-indigo-400 text-slate-500 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 mb-3">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.md,.txt"
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={ingesting}
              className="text-xs font-medium bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-indigo-300 border border-slate-700 py-2 px-2.5 rounded-lg flex items-center justify-center gap-1.5 transition-colors shadow-sm"
              title="Upload PDF, Markdown or Text file"
            >
              <Upload className="w-3.5 h-3.5" />
              Upload PDF/Doc
            </button>
            <button
              onClick={handleIngestSamples}
              disabled={ingesting}
              className="text-xs font-medium bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white py-2 px-2.5 rounded-lg flex items-center justify-center gap-1.5 transition-colors shadow-sm"
              title="Re-index all documents in sample_docs"
            >
              {ingesting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Layers className="w-3.5 h-3.5" />}
              Re-index All
            </button>
          </div>

          {ingestStatus && (
            <div className="p-2 mb-3 bg-indigo-950/60 border border-indigo-800/50 rounded-lg text-[11px] text-indigo-300 text-center animate-pulse">
              {ingestStatus}
            </div>
          )}

          {documents.length === 0 && (
            <div className="p-4 bg-slate-800/60 rounded-xl border border-dashed border-slate-700 text-center my-2">
              <p className="text-xs text-slate-400">No technical documents indexed yet. Upload a PDF or click Re-index All.</p>
            </div>
          )}

          <div className="space-y-2">
            {documents.map((doc) => (
              <div key={doc.id} className="p-2.5 bg-slate-800/70 hover:bg-slate-800 rounded-lg border border-slate-700/80 transition-colors">
                <div className="flex items-center gap-2 font-medium text-xs text-indigo-300 mb-1">
                  <FileText className="w-3.5 h-3.5 flex-shrink-0 text-indigo-400" />
                  <span className="truncate font-mono" title={doc.title}>{doc.title}</span>
                </div>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">{doc.content_preview}</p>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
        {/* Header */}
        <header className="h-14 border-b border-slate-800/80 flex items-center px-6 bg-slate-900/60 justify-between backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-slate-400">
              Session: <span className="text-indigo-400 font-semibold">{sessionId}</span>
            </span>
            <span className="text-[11px] bg-indigo-950/80 text-indigo-300 border border-indigo-800/60 px-2 py-0.5 rounded-full font-mono">
              LLM: Groq
            </span>
            <span className="text-[11px] bg-cyan-950/80 text-cyan-300 border border-cyan-800/60 px-2 py-0.5 rounded-full font-mono flex items-center gap-1">
              <Globe className="w-3 h-3" /> Web Fallback: Tavily
            </span>
          </div>
          {feedbackStatus && <div className="text-xs text-emerald-400 font-medium animate-pulse">{feedbackStatus}</div>}
        </header>

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 max-w-lg mx-auto">
              <div className="w-14 h-14 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-4 shadow-inner">
                <Sparkles className="w-7 h-7" />
              </div>
              <h3 className="text-base font-semibold text-slate-200 mb-1">Explainable Technical Documentation Assistant</h3>
              <p className="text-xs text-slate-400 leading-relaxed mb-5">
                Ask questions about your uploaded PDFs, Markdown, and technical specs. Grounded with self-corrective RAG, full explainability traces, and Tavily live search.
              </p>

              <div className="w-full text-left space-y-2">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider text-center">
                  Try asking one of these:
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {[
                    { label: 'Explain OOP concepts in Java with code', tag: 'Code & Concept' },
                    { label: 'Compare overloading vs overriding in a table', tag: 'Comparison Matrix' },
                    { label: 'How does FastAPI routing work?', tag: 'Architecture' },
                    { label: 'What is Docker Compose architecture?', tag: 'Web Search Fallback' }
                  ].map((item, pIdx) => (
                    <button
                      key={pIdx}
                      onClick={() => executeQuestion(item.label)}
                      className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800/90 border border-slate-800 hover:border-indigo-500/50 text-left transition-all group shadow-sm flex flex-col justify-between"
                    >
                      <span className="text-xs text-slate-300 group-hover:text-indigo-300 transition-colors font-medium">
                        {item.label}
                      </span>
                      <span className="text-[10px] text-indigo-400/80 font-mono mt-1">
                        Intent: {item.tag} ➔
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((msg, idx) => {
            const isWebFallback = !!(msg.sources && msg.sources.some((s) => s.document_id.startsWith('[Web]')));

            return (
              <div
                key={idx}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {/* Assistant Avatar */}
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 flex-shrink-0 mt-0.5">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                {/* Message Bubble */}
                <div
                  className={`${
                    msg.role === 'user'
                      ? 'max-w-xl bg-indigo-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm shadow-md'
                      : 'w-full max-w-3xl lg:max-w-4xl bg-slate-900/90 border border-slate-800 text-slate-200 rounded-2xl rounded-tl-sm p-5 shadow-lg'
                  }`}
                >
                  {/* Content */}
                  {msg.role === 'user' ? (
                    <p className="whitespace-pre-wrap font-medium leading-relaxed">{msg.content}</p>
                  ) : (
                    <div>
                      {/* Markdown Formatted Answer */}
                      <MarkdownView content={msg.content} />

                      {/* Explainability & Pipeline Trace Drawer */}
                      <ExplainabilityDrawer
                        intent={msg.query_intent}
                        rewrittenQuery={msg.rewritten_query}
                        relevanceScore={msg.relevance_score}
                        retries={msg.retries}
                        sourcesCount={msg.sources ? msg.sources.length : 0}
                        isWebFallback={isWebFallback}
                      />

                      {/* Sources Section */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-slate-800">
                          <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center gap-1.5">
                            <BookOpen className="w-3.5 h-3.5 text-indigo-400" /> Cited Sources ({msg.sources.length}):
                          </p>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                            {msg.sources.map((src, sIdx) => {
                              const matchPct = Math.round((src.score ?? 1.0) * 100);
                              const isWeb = src.document_id.startsWith('[Web]');
                              const urlMatch = src.chunk_text.match(/https?:\/\/[^\s—]+/);
                              const webUrl = isWeb && urlMatch ? urlMatch[0] : null;

                              return (
                                <div
                                  key={sIdx}
                                  className="text-xs bg-slate-950/80 p-3 rounded-lg border border-slate-800 text-slate-300 flex flex-col justify-between"
                                >
                                  <div className="flex items-center justify-between mb-1.5 gap-2">
                                    <span
                                      className="font-semibold text-indigo-300 truncate max-w-[220px] flex items-center gap-1.5 text-xs font-mono"
                                      title={src.document_id}
                                    >
                                      {isWeb ? (
                                        <Globe className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                                      ) : (
                                        <FileText className="w-3.5 h-3.5 flex-shrink-0 text-indigo-400" />
                                      )}
                                      {src.document_id}
                                    </span>
                                    <div className="flex items-center gap-1.5 flex-shrink-0">
                                      {webUrl && (
                                        <a
                                          href={webUrl}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-0.5 bg-cyan-950/60 border border-cyan-800/60 px-1.5 py-0.5 rounded transition-colors"
                                          title="Open in new tab"
                                        >
                                          Visit <ExternalLink className="w-2.5 h-2.5" />
                                        </a>
                                      )}
                                      <span
                                        className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-medium ${
                                          matchPct >= 70
                                            ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800/80'
                                            : matchPct >= 40
                                            ? 'bg-amber-950/80 text-amber-300 border border-amber-800/80'
                                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                                        }`}
                                      >
                                        Match: {matchPct}%
                                      </span>
                                    </div>
                                  </div>
                                  <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                                    {src.chunk_text.replace(/https?:\/\/[^\s—]+\s*—?\s*/, '') || src.chunk_text}...
                                  </p>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Action Bar */}
                      <div className="mt-4 flex items-center justify-between pt-3 border-t border-slate-800/60 text-xs">
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => handleFeedback('thumbs_up')}
                            className="p-1.5 hover:text-indigo-400 text-slate-400 hover:bg-slate-800 rounded-md transition-colors"
                            title="Helpful response"
                          >
                            <ThumbsUp className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleFeedback('thumbs_down')}
                            className="p-1.5 hover:text-indigo-400 text-slate-400 hover:bg-slate-800 rounded-md transition-colors"
                            title="Not helpful"
                          >
                            <ThumbsDown className="w-3.5 h-3.5" />
                          </button>
                          <div className="w-px h-3 bg-slate-800 mx-1" />
                          <CopyResponseButton text={msg.content} />
                        </div>

                        <div className="flex items-center gap-2">
                          {msg.relevance_score !== undefined && (
                            <span
                              className={`text-xs px-2.5 py-0.5 rounded-full font-mono font-medium flex items-center gap-1 ${
                                msg.relevance_score >= 0.70
                                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                  : msg.relevance_score > 0
                                  ? 'bg-amber-950 text-amber-300 border border-amber-800'
                                  : 'bg-slate-800 text-slate-400 border border-slate-700'
                              }`}
                              title="Overall Relevance of Retrieved Documentation"
                            >
                              <Target className="w-3 h-3" />
                              Relevance: {Math.round(msg.relevance_score * 100)}%
                            </span>
                          )}
                          {msg.retries !== undefined && msg.retries > 0 && (
                            <span className="text-xs text-amber-400 flex items-center gap-1 font-mono">
                              <RefreshCw className="w-3 h-3" /> Retries: {msg.retries}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* User Avatar */}
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 flex-shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 flex-shrink-0 animate-pulse">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl rounded-tl-sm p-4 text-xs text-slate-400 flex items-center gap-2.5 shadow-md">
                <RefreshCw className="w-4 h-4 animate-spin text-indigo-400" />
                <span>Analyzing intent, retrieving chunks, and grading relevance...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Footer */}
        <footer className="p-4 border-t border-slate-800/80 bg-slate-900/60 backdrop-blur-sm">
          <form onSubmit={handleSend} className="flex gap-3 max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a technical question (e.g. 'Explain encapsulation in Java', 'What is Docker?')..."
              className="flex-1 bg-slate-900 border border-slate-700/80 rounded-xl px-4 py-3 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors shadow-inner"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white px-5 py-3 rounded-xl font-medium text-xs flex items-center gap-2 transition-colors shadow-md"
            >
              <Send className="w-3.5 h-3.5" /> Send
            </button>
          </form>
        </footer>
      </main>
    </div>
  );
}
