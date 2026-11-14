import React, { useState } from 'react';
import { Copy, Check, Info, Code2, Sigma } from 'lucide-react';

interface MarkdownViewProps {
  content: string;
}

/**
 * Converts common LaTeX math expressions into clean, legible mathematical notation with Unicode symbols.
 */
export function formatLatexMath(raw: string): string {
  if (!raw) return '';
  let s = raw.trim();

  // Strip wrapping \boxed{...} or \text{...}
  s = s.replace(/\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}/g, '$1');
  s = s.replace(/\\text\{([^{}]+)\}/g, '$1');

  // LaTeX spacing
  s = s.replace(/\\[;,!]|\\quad|\\qquad/g, ' ');

  // Brackets
  s = s.replace(/\\bigl\(|\\left\(/g, '(').replace(/\\bigr\)|\\right\)/g, ')');
  s = s.replace(/\\bigl\[|\\left\[/g, '[').replace(/\\bigr\]|\\right\]/g, ']');

  // Vector / bold fonts: \mathbf{X} -> X, \boldsymbol{\beta} -> β
  s = s.replace(/\\(?:mathbf|boldsymbol|mathbfit|bm|mathit)\{([^{}]+)\}/g, '$1');

  // Fractions: \frac{a}{b} -> (a / b)
  s = s.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, '($1 / $2)');

  // Greek letters
  s = s.replace(/\\beta/g, 'β');
  s = s.replace(/\\alpha/g, 'α');
  s = s.replace(/\\theta/g, 'θ');
  s = s.replace(/\\lambda/g, 'λ');
  s = s.replace(/\\sigma/g, 'σ');
  s = s.replace(/\\mu/g, 'μ');
  s = s.replace(/\\gamma/g, 'γ');
  s = s.replace(/\\epsilon/g, 'ε');
  s = s.replace(/\\delta/g, 'δ');
  s = s.replace(/\\nabla/g, '∇');

  // Common mathematical symbols
  s = s.replace(/\\hat\{y\}/g, 'ŷ');
  s = s.replace(/\\hat\{([a-zA-Z])\}/g, '$1̂');
  s = s.replace(/\\leftarrow/g, '←');
  s = s.replace(/\\rightarrow/g, '→');
  s = s.replace(/\\le/g, '≤').replace(/\\ge/g, '≥');
  s = s.replace(/\\ne/g, '≠').replace(/\\approx/g, '≈');
  s = s.replace(/\\times/g, '×').replace(/\\cdot/g, '·');
  s = s.replace(/\\dots|\\cdots|\\ldots/g, '...');

  // Superscripts & Subscripts
  s = s.replace(/\\top|\^\\top|\^T/g, 'ᵀ');
  s = s.replace(/\^\{\*\}|\^\{!\*\}|\^\*/g, '*');
  s = s.replace(/\^\{-1\}|\^-1/g, '⁻¹');
  s = s.replace(/\^2/g, '²').replace(/\^3/g, '³').replace(/\^k/g, 'ᵏ');
  s = s.replace(/_0/g, '₀').replace(/_1/g, '₁').replace(/_2/g, '₂').replace(/_3/g, '₃');
  s = s.replace(/_i/g, 'ᵢ').replace(/_j/g, 'ⱼ').replace(/_k/g, 'ₖ').replace(/_m/g, 'ₘ').replace(/_n/g, 'ₙ');

  // Summations: \sum_{i=1}^{m} -> ∑(i=1 to m)
  s = s.replace(/\\sum_\{([^{}]+)\}\^\{([^{}]+)\}/g, '∑($1 to $2) ');
  s = s.replace(/\\sum/g, '∑ ');

  // Clean remaining backslashes and redundant spaces
  s = s.replace(/\\([a-zA-Z]+)/g, '$1');
  s = s.replace(/\s+/g, ' ').trim();

  return s;
}

function CodeBlock({ code, language }: { code: string; language: string }): React.JSX.Element {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(code).catch(() => {});
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-slate-800 bg-slate-950/90 shadow-md">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900 border-b border-slate-800 text-xs text-slate-400">
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
      <pre className="p-3.5 overflow-x-auto text-xs font-mono text-slate-200 leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function MathDisplayBlock({ math }: { math: string }): React.JSX.Element {
  const [copied, setCopied] = useState(false);
  const formatted = formatLatexMath(math);

  const handleCopy = () => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(formatted).catch(() => {});
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-3.5 rounded-xl border border-indigo-900/40 bg-gradient-to-r from-slate-950 via-indigo-950/20 to-slate-950 p-3 shadow-inner group relative">
      <div className="flex items-center justify-between text-[10px] text-indigo-400/80 uppercase font-mono tracking-wider mb-1.5 px-1">
        <span className="flex items-center gap-1">
          <Sigma className="w-3 h-3 text-indigo-400" /> Mathematical Formula
        </span>
        <button
          onClick={handleCopy}
          className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 text-[10px] text-slate-400 hover:text-slate-200"
        >
          {copied ? <Check className="w-2.5 h-2.5 text-emerald-400" /> : <Copy className="w-2.5 h-2.5" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <div className="flex justify-center items-center py-2 overflow-x-auto">
        <div className="font-serif text-sm md:text-base text-indigo-200 tracking-wide px-4 py-1.5 rounded-lg bg-slate-900/80 border border-indigo-900/30 shadow-sm font-medium">
          {formatted}
        </div>
      </div>
    </div>
  );
}

function renderInlineText(text: string): React.ReactNode[] {
  const tokens: React.ReactNode[] = [];
  // Matches inline code (`...`), inline LaTeX math (\(...\) or $...$), bold (**...**), italic (*...*), or links
  const regex = /(`[^`]+`|\\\(.+?\\\)|\$[^$\n]+\$|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;
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
    } else if (token.startsWith('\\(') && token.endsWith('\\)')) {
      const mathInner = token.slice(2, -2);
      tokens.push(
        <span key={key} className="font-serif italic text-indigo-300 font-medium px-1.5 py-0.5 bg-indigo-950/40 rounded border border-indigo-900/40 text-[11px] tracking-wide inline-block mx-0.5">
          {formatLatexMath(mathInner)}
        </span>
      );
    } else if (token.startsWith('$') && token.endsWith('$') && token.length > 2) {
      const mathInner = token.slice(1, -1);
      tokens.push(
        <span key={key} className="font-serif italic text-indigo-300 font-medium px-1.5 py-0.5 bg-indigo-950/40 rounded border border-indigo-900/40 text-[11px] tracking-wide inline-block mx-0.5">
          {formatLatexMath(mathInner)}
        </span>
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

    // 2. Display Math Block: \[ ... \] or $$ ... $$
    const trimmedLine = line.trim();
    if (trimmedLine === '\\[' || trimmedLine.startsWith('\\[') || trimmedLine === '$$' || trimmedLine.startsWith('$$')) {
      const isBracket = trimmedLine.startsWith('\\[');
      let mathContent = '';

      if (isBracket && trimmedLine.endsWith('\\]') && trimmedLine.length > 4) {
        // Single-line \[ math \]
        mathContent = trimmedLine.slice(2, -2).trim();
        i++;
      } else if (!isBracket && trimmedLine.endsWith('$$') && trimmedLine.length > 4) {
        // Single-line $$ math $$
        mathContent = trimmedLine.slice(2, -2).trim();
        i++;
      } else {
        // Multi-line block
        const mathLines: string[] = [];
        if (isBracket && trimmedLine.length > 2) {
          mathLines.push(trimmedLine.slice(2));
        } else if (!isBracket && trimmedLine.length > 2) {
          mathLines.push(trimmedLine.slice(2));
        }
        i++;
        while (i < lines.length) {
          const cur = lines[i].trim();
          if (isBracket && (cur === '\\]' || cur.endsWith('\\]'))) {
            if (cur.length > 2) mathLines.push(cur.slice(0, -2));
            i++;
            break;
          }
          if (!isBracket && (cur === '$$' || cur.endsWith('$$'))) {
            if (cur.length > 2) mathLines.push(cur.slice(0, -2));
            i++;
            break;
          }
          mathLines.push(lines[i]);
          i++;
        }
        mathContent = mathLines.join(' ').trim();
      }

      if (mathContent) {
        elements.push(<MathDisplayBlock key={`math-${i}`} math={mathContent} />);
      }
      continue;
    }

    // 3. Table Block: Markdown Pipe Table (| col 1 | col 2 |)
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
          <div key={`table-${i}`} className="my-3 overflow-x-auto rounded-xl border border-slate-800 shadow-sm">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-800/80 border-b border-slate-700 text-slate-200 font-semibold">
                  {headerCells.map((h, hIdx) => (
                    <th key={hIdx} className="px-3.5 py-2.5">
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
                        <td key={cIdx} className="px-3.5 py-2.5 text-slate-300">
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

    // 4. Tab-Separated Table Fallback (e.g. Symbol\tMeaning)
    if (line.includes('\t') && line.split('\t').length >= 2) {
      const tabTableLines: string[] = [];
      while (i < lines.length && lines[i].includes('\t') && lines[i].split('\t').length >= 2) {
        tabTableLines.push(lines[i]);
        i++;
      }
      if (tabTableLines.length >= 2) {
        const headerCells = tabTableLines[0].split('\t').map((c) => c.trim());
        const bodyLines = tabTableLines.slice(1);

        elements.push(
          <div key={`tab-table-${i}`} className="my-3 overflow-x-auto rounded-xl border border-slate-800 shadow-sm">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-800/80 border-b border-slate-700 text-slate-200 font-semibold">
                  {headerCells.map((h, hIdx) => (
                    <th key={hIdx} className="px-3.5 py-2.5">
                      {renderInlineText(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 bg-slate-900/60">
                {bodyLines.map((row, rIdx) => {
                  const cells = row.split('\t').map((c) => c.trim());
                  return (
                    <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                      {cells.map((c, cIdx) => (
                        <td key={cIdx} className="px-3.5 py-2.5 text-slate-300">
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

    // 5. Blockquote / Callout Note
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
          className={`my-3 p-3.5 rounded-xl border flex gap-2.5 text-xs leading-relaxed ${
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

    // 6. Headings
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

    // 7. Horizontal Rule
    if (line.trim() === '---' || line.trim() === '***') {
      elements.push(<hr key={`hr-${i}`} className="my-4 border-slate-800" />);
      i++;
      continue;
    }

    // 8. List Items
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

    // 9. Regular paragraph
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
