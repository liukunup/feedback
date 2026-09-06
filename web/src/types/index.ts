/**
 * 类型定义
 */
export interface Channel {
  id: string;
  platform: Platform;
  name: string;
  description?: string;
  webhookId?: string;
  webhookUrl?: string;
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
  messagesCount?: number;
}

export interface ChannelCreate {
  platform: Platform;
  name: string;
  description?: string;
  config: Record<string, any>;
  enabled?: boolean;
}

export interface ChannelUpdate {
  name?: string;
  description?: string;
  config?: Record<string, any>;
  enabled?: boolean;
}

export interface Message {
  id: string;
  channelId: string;
  platformMessageId: string;
  content: string;
  authorId: string;
  authorName: string;
  authorAvatar?: string;
  createdAt: string;
  channelName?: string;
  metadata?: Record<string, any>;
  attachments?: Attachment[];
  sentiment?: Sentiment;
  categories?: string[];
  entities?: {
    users?: string[];
    organizations?: string[];
    topics?: string[];
  };
  summary?: string;
  analyzed: boolean;
  platform?: Platform;
}

export interface MessageDetailResponse extends Message {
  previousMessage?: Message;
  nextMessage?: Message;
}

export interface MessageListResponse {
  total: number;
  page: number;
  pageSize: number;
  items: Message[];
}

export interface SearchQuery {
  query: string;
  channelIds?: string[];
  platforms?: Platform[];
  categories?: string[];
  sentiment?: Sentiment;
  author?: string;
  since?: string;
  until?: string;
  page?: number;
  pageSize?: number;
  sortBy?: 'createdAt' | 'relevance';
  sortOrder?: 'asc' | 'desc';
}

export interface SearchResponse {
  query: string;
  total: number;
  page: number;
  pageSize: number;
  items: Message[];
  facets?: {
    platforms?: Record<string, number>;
    sentiments?: Record<string, number>;
    categories?: Record<string, number>;
  };
}

export interface StatisticsResponse {
  totalMessages: number;
  totalChannels: number;
  messagesByPlatform: Record<string, number>;
  messagesBySentiment: Record<string, number>;
  topCategories: Array<{ category: string; count: number }>;
  messagesToday: number;
  messagesThisWeek: number;
}

export interface Attachment {
  type: string;
  url?: string;
  filename?: string;
  contentType?: string;
}

export type Platform = 'discord' | 'reddit' | 'qq' | 'wecom';

export type Sentiment = 'positive' | 'neutral' | 'negative';
