import { apiClient } from './client';

export interface AICitation {
  document_id: string;
  document_title: string;
  document_date: string;
  excerpt: string;
}

export interface AskAIResponse {
  answer: string;
  citations: AICitation[];
  conversation_id: string;
  disclaimer: string;
}

export interface ChatMessage {
  id: string;
  sender: 'USER' | 'AI';
  content: string;
  citations?: AICitation[];
  timestamp: string;
}

export const aiApi = {
  ask: async (question: string, conversationId?: string): Promise<AskAIResponse> => {
    const { data } = await apiClient.post('/ai/ask/', {
      question,
      conversation_id: conversationId,
    });
    return data.data || data;
  },

  getHistory: async (): Promise<ChatMessage[]> => {
    const { data } = await apiClient.get('/ai/conversations/current/');
    return data.messages || [];
  },
};

