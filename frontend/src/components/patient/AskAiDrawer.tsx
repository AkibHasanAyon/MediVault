import React, { useState } from 'react';
import { Bot, Send, Sparkles, BookOpen, AlertCircle, X } from 'lucide-react';
import { aiApi, ChatMessage, AICitation } from '../../api/ai';

interface AskAiDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AskAiDrawer: React.FC<AskAiDrawerProps> = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'AI',
      content: 'হ্যালো! আমি আপনার মেডিভল্ট ব্যক্তিগত স্বাস্থ্য সহকারী। আপনার আপলোড করা প্রেসক্রিপশন ও টেস্ট রিপোর্ট সম্পর্কে কোনো প্রশ্ন থাকলে জিজ্ঞাসা করতে পারেন।\n\n(Hello! I am your MediVault health assistant. Ask me questions about your uploaded prescriptions and lab reports.)',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeConvId, setActiveConvId] = useState<string | undefined>(undefined);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'USER',
      content: input,
      timestamp: new Date().toLocaleTimeString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await aiApi.ask(input, activeConvId);
      setActiveConvId(res.conversation_id);

      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'AI',
        content: res.answer,
        citations: res.citations,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'AI',
          content: 'দুঃখিত, সংযোগ ত্রুটির কারণে উত্তর দেওয়া সম্ভব হয়নি। কিছুক্ষণ পর আবার চেষ্টা করুন।',
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-white shadow-2xl z-50 flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-gradient-to-r from-teal-50 to-white">
        <div className="flex items-center space-x-2.5">
          <div className="w-9 h-9 rounded-xl bg-medivault-primary text-white flex items-center justify-center shadow-sm">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-medivault-navy flex items-center space-x-1">
              <span>Ask AI Clinical Assistant</span>
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            </h3>
            <p className="text-[11px] text-slate-500">Grounded strictly in your uploaded records</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'USER' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                m.sender === 'USER'
                  ? 'bg-medivault-primary text-white rounded-br-none shadow-sm'
                  : 'bg-white text-slate-800 border border-slate-200 rounded-bl-none shadow-sm whitespace-pre-wrap'
              }`}
            >
              <p>{m.content}</p>

              {/* Citations pills */}
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 pt-2 border-t border-slate-100 space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Cited Sources:
                  </span>
                  {m.citations.map((cite, idx) => (
                    <div
                      key={idx}
                      className="flex items-center space-x-1.5 bg-teal-50/70 border border-teal-100 px-2.5 py-1 rounded-md text-[11px] text-teal-900"
                    >
                      <BookOpen className="w-3 h-3 text-medivault-primary shrink-0" />
                      <span className="font-semibold">{cite.document_title}</span>
                      <span className="text-slate-400">({cite.document_date})</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <span className="text-[10px] text-slate-400 mt-1 px-1">{m.timestamp}</span>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center space-x-2 text-xs text-slate-400 p-2">
            <div className="w-2 h-2 rounded-full bg-teal-600 animate-bounce" />
            <div className="w-2 h-2 rounded-full bg-teal-600 animate-bounce [animation-delay:0.2s]" />
            <div className="w-2 h-2 rounded-full bg-teal-600 animate-bounce [animation-delay:0.4s]" />
            <span className="text-[11px]">Searching your medical documents...</span>
          </div>
        )}
      </div>

      {/* Disclaimer */}
      <div className="px-4 py-2 bg-amber-50/70 border-t border-amber-100 text-[10px] text-amber-800 flex items-center space-x-1.5">
        <AlertCircle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
        <span>For informational clarity only. MediVault AI does not diagnose diseases or prescribe medications.</span>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="p-3 border-t border-slate-200 bg-white flex space-x-2">
        <input
          type="text"
          placeholder="Ask a question about your health records..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 px-4 py-2.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="px-4 py-2.5 bg-medivault-primary text-white rounded-xl hover:bg-teal-700 transition disabled:opacity-50"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};

