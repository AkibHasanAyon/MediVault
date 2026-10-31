import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  return (
    <div className={`prose-sm max-w-none text-xs leading-relaxed space-y-2 ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed text-slate-800">{children}</p>,
          h1: ({ children }) => (
            <h1 className="text-sm font-bold text-slate-900 mt-3 mb-1.5 first:mt-0 flex items-center space-x-1">
              <span>{children}</span>
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-xs font-bold text-slate-900 mt-2.5 mb-1 first:mt-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-bold text-teal-800 mt-2 mb-1 first:mt-0">
              {children}
            </h3>
          ),
          ul: ({ children }) => (
            <ul className="list-disc pl-4 space-y-1 my-1.5 text-slate-800">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal pl-4 space-y-1 my-1.5 text-slate-800">
              {children}
            </ol>
          ),
          li: ({ children }) => <li className="leading-relaxed pl-0.5">{children}</li>,
          strong: ({ children }) => <strong className="font-bold text-slate-900">{children}</strong>,
          em: ({ children }) => <em className="italic text-slate-700">{children}</em>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-teal-500 pl-3 py-1 my-2 bg-teal-50/50 rounded-r-lg text-slate-700 italic">
              {children}
            </blockquote>
          ),
          code: ({ children, className }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code className="bg-teal-50 text-teal-800 border border-teal-100 font-mono text-[11px] px-1 py-0.5 rounded">
                  {children}
                </code>
              );
            }
            return (
              <code className="block bg-slate-900 text-slate-100 p-2.5 rounded-xl font-mono text-[11px] overflow-x-auto my-2">
                {children}
              </code>
            );
          },
          table: ({ children }) => (
            <div className="overflow-x-auto my-2 rounded-lg border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 text-[11px]">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-slate-50 font-bold text-slate-700">{children}</thead>,
          tbody: ({ children }) => <tbody className="divide-y divide-slate-100 bg-white">{children}</tbody>,
          tr: ({ children }) => <tr className="hover:bg-slate-50/50 transition">{children}</tr>,
          th: ({ children }) => <th className="px-2.5 py-1.5 text-left font-bold">{children}</th>,
          td: ({ children }) => <td className="px-2.5 py-1.5 text-slate-800">{children}</td>,
          hr: () => <hr className="border-slate-200 my-2.5" />,
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noreferrer"
              className="text-medivault-primary font-bold hover:underline"
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

