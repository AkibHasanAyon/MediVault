import React, { useState, useRef, useEffect } from 'react';
import { Bot, Send, Sparkles, BookOpen, AlertCircle, X, Heart, ShieldCheck } from 'lucide-react';
import { aiApi, ChatMessage } from '../../api/ai';
import { MarkdownRenderer } from '../common/MarkdownRenderer';

interface AskAiDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

const QUICK_STARTERS = [
  { label: '📊 Explain my latest lab report', query: 'Can you explain the key findings of my latest lab test report in simple words?' },
  { label: '🥗 Tips to maintain healthy blood sugar', query: 'What are healthy everyday dietary and lifestyle habits to manage blood sugar in Bangladesh?' },
  { label: '💊 What medications am I taking?', query: 'Can you summarize what active medications I am currently prescribed and their schedules?' },
  { label: '💧 Daily wellness & hydration tips', query: 'What are good daily hydration and exercise tips for maintaining energy and health?' },
];

export const AskAiDrawer: React.FC<AskAiDrawerProps> = ({ isOpen, onClose }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'AI',
      content:
        'হ্যালো! 😊 আমি আপনার মেডিভল্ট ব্যক্তিগত স্বাস্থ্য সহকারী ও বন্ধু।\n\nআপনার স্বাস্থ্য, দৈনন্দিন সুস্থতা, ডায়েট বা লাইফস্টাইল টিপস, কিংবা আপনার প্রেসক্রিপশন ও ল্যাব টেস্টের রিপোর্ট বুঝতে কোনো সাহায্য লাগলে আমাকে নির্দ্বিধায় বলুন। আমি সবসময় আপনার পাশে আছি!\n\n(Hello! 😊 I am your MediVault personal health companion. Feel free to ask me anything about your wellness, lifestyle habits, or to help understand your medical records and lab tests!)',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeConvId, setActiveConvId] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const sendMessage = async (textToSend: string) => {
    const trimmed = textToSend.trim();
    if (!trimmed || isLoading) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'USER',
      content: trimmed,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await aiApi.ask(trimmed, activeConvId);
      setActiveConvId(res.conversation_id);

      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'AI',
        content: res.answer,
        citations: res.citations,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: 'AI',
          content: 'দুঃখিত, সংযোগ ত্রুটির কারণে উত্তর দেওয়া সম্ভব হয়নি। কিছুক্ষণ পর আবার চেষ্টা করুন। (Sorry, there was a connection issue. Please try again shortly.)',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[500px] bg-white shadow-2xl z-50 flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-gradient-to-r from-teal-50 via-white to-teal-50/40">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-medivault-primary to-teal-700 text-white flex items-center justify-center shadow-md">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-medivault-navy flex items-center space-x-1.5">
              <span>MediVault Health Companion</span>
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            </h3>
            <p className="text-[11px] text-teal-700 font-medium flex items-center space-x-1">
              <Heart className="w-3 h-3 text-rose-500 fill-rose-500" />
              <span>Your friendly personal health assistant</span>
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 text-slate-400 hover:text-slate-600 rounded-xl hover:bg-slate-100 transition"
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
              className={`max-w-[88%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                m.sender === 'USER'
                  ? 'bg-medivault-primary text-white rounded-br-none shadow-sm'
                  : 'bg-white text-slate-800 border border-slate-200/90 rounded-bl-none shadow-sm'
              }`}
            >
              {m.sender === 'USER' ? (
                <p className="whitespace-pre-wrap">{m.content}</p>
              ) : (
                <MarkdownRenderer content={m.content} />
              )}

              {/* Citations pills if document was referenced */}
              {m.citations && m.citations.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-slate-100 space-y-1.5">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Referenced Records:
                  </span>
                  {m.citations.map((cite, idx) => (
                    <div
                      key={idx}
                      className="flex items-center space-x-1.5 bg-teal-50/80 border border-teal-100 px-2.5 py-1 rounded-lg text-[11px] text-teal-900"
                    >
                      <BookOpen className="w-3 h-3 text-medivault-primary shrink-0" />
                      <span className="font-semibold">{cite.document_title}</span>
                      {cite.document_date && <span className="text-slate-400">({cite.document_date})</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <span className="text-[10px] text-slate-400 mt-1 px-1">{m.timestamp}</span>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center space-x-2.5 text-xs text-slate-500 p-3 bg-white border border-slate-200 rounded-2xl rounded-bl-none max-w-[80%] shadow-sm">
            <div className="flex space-x-1">
              <div className="w-2 h-2 rounded-full bg-teal-600 animate-bounce" />
              <div className="w-2 h-2 rounded-full bg-teal-600 animate-bounce [animation-delay:0.2s]" />
              <div className="w-2 h-2 rounded-full bg-teal-600 animate-bounce [animation-delay:0.4s]" />
            </div>
            <span className="text-[11px] font-medium text-slate-600">Reviewing your health context & preparing friendly advice...</span>
          </div>
        )}

        {/* Quick Starters if conversation is just beginning */}
        {messages.length === 1 && !isLoading && (
          <div className="pt-2 space-y-2">
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider px-1">
              Suggested Questions to Ask:
            </p>
            <div className="space-y-1.5">
              {QUICK_STARTERS.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => sendMessage(item.query)}
                  className="w-full text-left p-2.5 bg-white hover:bg-teal-50/70 border border-slate-200 hover:border-teal-300 rounded-xl text-xs text-slate-700 font-medium transition shadow-2xs flex items-center justify-between group"
                >
                  <span>{item.label}</span>
                  <span className="text-slate-300 group-hover:text-medivault-primary font-bold text-sm">→</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Safety Disclaimer Banner */}
      <div className="px-4 py-2 bg-teal-50/60 border-t border-teal-100/70 text-[10px] text-slate-600 flex items-center space-x-2">
        <ShieldCheck className="w-4 h-4 shrink-0 text-teal-600" />
        <span>Personal health companion & assistant. MediVault AI shares educational advice and does not prescribe new prescription drugs.</span>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="p-3 border-t border-slate-200 bg-white flex space-x-2">
        <input
          type="text"
          placeholder="Ask a question about your health, records, or wellness..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 px-4 py-2.5 border border-slate-300 rounded-xl text-xs focus:ring-2 focus:ring-teal-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={!input.trim() || isLoading}
          className="px-4 py-2.5 bg-medivault-primary text-white rounded-xl hover:bg-teal-700 transition disabled:opacity-50 shadow-sm"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
};
