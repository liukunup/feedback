/**
 * API 服务层
 */
import axios from 'axios';
import type {
  Channel, ChannelCreate, ChannelUpdate,
  Message, MessageListResponse, MessageDetailResponse,
  SearchQuery, SearchResponse, StatisticsResponse
} from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============ 渠道 API ============
export const channelApi = {
  list: async (params?: {
    platform?: string;
    enabled?: boolean;
    page?: number;
    pageSize?: number;
  }): Promise<Channel[]> => {
    const { data } = await api.get('/channels/', { params });
    return data.items;
  },

  get: async (id: string): Promise<Channel> => {
    const { data } = await api.get(`/channels/${id}`);
    return data;
  },

  create: async (channel: ChannelCreate): Promise<Channel> => {
    const { data } = await api.post('/channels/', channel);
    return data;
  },

  update: async (id: string, updates: ChannelUpdate): Promise<Channel> => {
    const { data } = await api.patch(`/channels/${id}`, updates);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/channels/${id}`);
  },

  enable: async (id: string): Promise<Channel> => {
    const { data } = await api.post(`/channels/${id}/enable`);
    return data;
  },

  disable: async (id: string): Promise<Channel> => {
    const { data } = await api.post(`/channels/${id}/disable`);
    return data;
  },

  triggerFetch: async (id: string): Promise<{ taskId: string }> => {
    const { data } = await api.post(`/channels/${id}/fetch`);
    return data;
  },
};

// ============ 消息 API ============
export const messageApi = {
  list: async (params?: {
    channelId?: string;
    platform?: string;
    sentiment?: string;
    category?: string;
    since?: string;
    until?: string;
    author?: string;
    analyzed?: boolean;
    page?: number;
    pageSize?: number;
  }): Promise<MessageListResponse> => {
    const { data } = await api.get('/messages/', { params });
    return data;
  },

  get: async (id: string): Promise<MessageDetailResponse> => {
    const { data } = await api.get(`/messages/${id}`);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/messages/${id}`);
  },
};

// ============ 搜索 API ============
export const searchApi = {
  search: async (query: SearchQuery): Promise<SearchResponse> => {
    const { data } = await api.post('/search/', query);
    return data;
  },

  stats: async (params?: {
    channelId?: string;
    since?: string;
    until?: string;
  }): Promise<StatisticsResponse> => {
    const { data } = await api.get('/search/stats', { params });
    return data;
  },

  categories: async (limit?: number): Promise<{ categories: Array<{ name: string; count: number }> }> => {
    const { data } = await api.get('/search/categories', { params: { limit } });
    return data;
  },
};

export default api;
