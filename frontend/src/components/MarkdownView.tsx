import React, { useState } from 'react';
import { Copy, Check, Info, Code2 } from 'lucide-react';

interface MarkdownViewProps {
  content: string;
}

function CodeBlock({ code, language }: { code: string; language: string }): React.JSX.Element {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-lg overflow-hidden border border-slate-800 bg-slate-950/90 shadow-md">
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900 border-b border-slate-800 text-xs text-slate-400">
        <span className="font-mono flex items-center gap-1.5 text-indigo-300 font-semibold lowercase">
          <Code2 className="w-3.5 h-3.5" />
          {language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-slate-200 transition-colors text-[11px] px-2 py-0.5 rounded bg-slate-800/80 hover:bg-slate-700"
          title="Copy code"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <pre className="p-3 overflow-x-auto text-xs font-mono text-slate-200 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function renderInlineText(text: string): React.ReactNode[] {
  // Regex to match code, bold, link, and plain text
  const tokens: React.ReactNode[] = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      tokens.push(text.substring(lastIndex, match.index));
    }
    const token = match[0];
    const key = `${match.index}-${token.length}`;

    if (token.startsWith('`') && token.endsWith('`')) {
      tokens.push(
        <code key={key} className="bg-slate-800/90 text-indigo-300 border border-slate-700/60 px-1.5 py-0.5 rounded font-mono text-xs">
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith('**') && token.endsWith('**')) {
      tokens.push(
        <strong key={key} className="font-semibold text-slate-100">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith('*') && token.endsWith('*')) {
      tokens.push(
        <em key={key} className="italic text-slate-300">
          {token.slice(1, -1)}
        </em>
      );
    } else if (token.startsWith('[') && token.includes('](')) {
      const parts = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (parts) {
        tokens.push(
          <a
            key={key}
            href={parts[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
          >
            {parts[1]}
          </a>
        );
      }
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    tokens.push(text.substring(lastIndex));
  }

  return tokens;
}

export function MarkdownView({ content }: MarkdownViewProps): React.JSX.Element {
  if (!content) return <span />;

  const elements: React.JSX.Element[] = [];
  const lines = content.split('\n');
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // 1. Fenced Code Block
    if (line.trim().startsWith('```')) {
      const lang = line.trim().slice(3).trim();
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // Skip closing ```
      elements.push(
        <CodeBlock key={`code-${i}`} code={codeLines.join('\n')} language={lang} />
      );
      continue;
    }

    // 2. Table Block
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        const headerCells = tableLines[0]
          .split('|')
          .slice(1, -1)
          .map((c) => c.trim());
        const bodyLines = tableLines.slice(2); // Skip separator line

        elements.push(
          <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-lg border border-slate-800 shadow-sm">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-800/80 border-b border-slate-700 text-slate-200">
                  {headerCells.map((h, hIdx) => (
                    <th key={hIdx} className="px-3 py-2 font-semibold">
                      {renderInlineText(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900/60">
                {bodyLines.map((row, rIdx) => {
                  const cells = row
                    .split('|')
                    .slice(1, -1)
                    .map((c) => c.trim());
                  return (
                    <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                      {cells.map((c, cIdx) => (
                        <td key={cIdx} className="px-3 py-2 text-slate-300">
                          {renderInlineText(c)}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // 3. Blockquote / Callout Note
    if (line.trim().startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].replace(/^>\s?/, ''));
        i++;
      }
      const quoteText = quoteLines.join(' ');
      const isNote = quoteText.toLowerCase().includes('note:');

      elements.push(
        <div
          key={`quote-${i}`}
          className={`my-3 p-3 rounded-lg border flex gap-2.5 text-xs leading-relaxed ${
            isNote
              ? 'bg-amber-950/30 border-amber-800/60 text-amber-200/90'
              : 'bg-slate-800/50 border-slate-700 text-slate-300'
          }`}
        >
          <Info className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-400" />
          <div className="flex-1">{renderInlineText(quoteText)}</div>
        </div>
      );
      continue;
    }

    // 4. Headings
    if (line.startsWith('### ')) {
      elements.push(
        <h3 key={`h3-${i}`} className="text-sm font-bold text-indigo-300 mt-4 mb-2 flex items-center gap-1.5">
          {renderInlineText(line.slice(4))}
        </h3>
      );
      i++;
      continue;
    }

    if (line.startsWith('## ')) {
      elements.push(
        <h2 key={`h2-${i}`} className="text-base font-bold text-slate-100 mt-5 mb-2 pb-1 border-b border-slate-800">
          {renderInlineText(line.slice(3))}
        </h2>
      );
      i++;
      continue;
    }

    if (line.startsWith('# ')) {
      elements.push(
        <h1 key={`h1-${i}`} className="text-lg font-bold text-white mt-6 mb-3">
          {renderInlineText(line.slice(2))}
        </h1>
      );
      i++;
      continue;
    }

    // 5. Horizontal Rule
    if (line.trim() === '---' || line.trim() === '***') {
      elements.push(<hr key={`hr-${i}`} className="my-4 border-slate-800" />);
      i++;
      continue;
    }

    // 6. List Items
    const listMatch = line.match(/^(\s*)([-*]|\d+\.)\s+(.+)$/);
    if (listMatch) {
      const isNumbered = /^\d+\./.test(listMatch[2]);
      const indent = listMatch[1].length > 0 ? 'ml-4' : '';
      elements.push(
        <div key={`li-${i}`} className={`flex items-start gap-2 my-1 text-xs text-slate-300 ${indent}`}>
          <span className="font-mono text-indigo-400 mt-0.5 select-none font-semibold">
            {isNumbered ? listMatch[2] : '•'}
          </span>
          <span className="flex-1 leading-relaxed">{renderInlineText(listMatch[3])}</span>
        </div>
      );
      i++;
      continue;
    }

    // 7. Regular paragraph / empty line
    if (line.trim()) {
      elements.push(
        <p key={`p-${i}`} className="my-2 text-xs leading-relaxed text-slate-300">
          {renderInlineText(line)}
        </p>
      );
    }
    i++;
  }

  return <div className="space-y-1">{elements}</div>;
}

