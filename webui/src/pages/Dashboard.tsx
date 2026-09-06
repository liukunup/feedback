/**
 * 首页 / 仪表盘
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, MessageSquare, TrendingUp, Calendar, Hash, Search, X } from 'lucide-react';
import { clsx } from 'clsx';

import { MessageList } from '../components/MessageList';
import { messageApi, searchApi } from '../services/api';
import { useAppStore } from '../stores/appStore';

const PAGE_SIZE_OPTIONS = [10, 20, 50, 100];

const platforms = [
  { id: null, name: '全部', icon: '🌐' },
  { id: 'discord', name: 'Discord', icon: '📱' },
  { id: 'reddit', name: 'Reddit', icon: '📘' },
  { id: 'qq', name: 'QQ', icon: '💬' },
  { id: 'wecom', name: '企业微信', icon: '💼' },
];

const sentiments = [
  { id: null, name: '全部', icon: null },
  { id: 'positive', name: '正面', icon: '😊' },
  { id: 'neutral', name: '中性', icon: '😐' },
  { id: 'negative', name: '负面', icon: '😞' },
];

export const Dashboard: React.FC = () => {
  const {
    selectedPlatform,
    setSelectedPlatform,
    searchQuery,
    setSearchQuery,
    selectedSentiment,
    setSelectedSentiment,
    selectedCategories,
    toggleCategory,
    dateRange,
    setDateRange,
    isRefreshing,
    setRefreshing,
  } = useAppStore();

  // 分页状态
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  // 获取统计数据
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => searchApi.stats(),
    refetchInterval: 60000,
  });

  // 获取标签列表
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => searchApi.categories(50),
  });

  // 获取消息列表
  const { data: messagesData, isLoading, refetch } = useQuery({
    queryKey: ['messages', selectedPlatform, searchQuery, selectedSentiment, selectedCategories, dateRange, page, pageSize],
    queryFn: () =>
      messageApi.list({
        platform: selectedPlatform || undefined,
        sentiment: selectedSentiment || undefined,
        category: selectedCategories[0] || undefined,
        since: dateRange.since?.toISOString(),
        until: dateRange.until?.toISOString(),
        page,
        pageSize,
      }),
    enabled: !searchQuery,
  });

  // 搜索结果
  const { data: searchData, refetch: searchRefetch } = useQuery({
    queryKey: ['search', searchQuery, selectedPlatform, selectedSentiment, selectedCategories, page, pageSize],
    queryFn: () =>
      searchApi.search({
        query: searchQuery,
        platforms: selectedPlatform ? [selectedPlatform as any] : undefined,
        sentiment: selectedSentiment as any || undefined,
        categories: selectedCategories,
        page,
        pageSize,
      }),
    enabled: !!searchQuery,
  });

  // 刷新
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await refetch();
      if (searchQuery) await searchRefetch();
    } finally {
      setRefreshing(false);
    }
  };

  // 清除筛选
  const clearFilters = () => {
    setSelectedPlatform(null);
    setSelectedSentiment(null);
    setSearchQuery('');
    setDateRange(null, null);
  };

  const hasFilters = selectedPlatform || selectedSentiment || searchQuery || selectedCategories.length > 0;

  const messages = searchQuery ? searchData?.items || [] : messagesData?.items || [];
  const total = searchQuery ? searchData?.total || 0 : messagesData?.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* 顶部导航 */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <h1 className="text-lg font-semibold text-gray-800">
          📊 Social Feed Aggregator
        </h1>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-500 text-white text-sm rounded-md hover:bg-blue-600 disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? '刷新中...' : '刷新'}
        </button>
      </header>

      {/* 主内容 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧 - 消息列表 */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          {/* 消息列表 */}
          <div className="flex-1 overflow-y-auto p-4">
            <MessageList messages={messages} isLoading={isLoading} />
          </div>

          {/* 分页 */}
          {total > 0 && (
            <div className="p-3 border-t border-gray-100 bg-gray-50 shrink-0">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-gray-500">每页</span>
                  <select
                    value={pageSize}
                    onChange={(e) => {
                      setPageSize(Number(e.target.value));
                      setPage(1);
                    }}
                    className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    {PAGE_SIZE_OPTIONS.map((s) => (
                      <option key={s} value={s}>{s}条</option>
                    ))}
                  </select>
                </div>

                <div className="text-gray-600">
                  共 {total} 条，第 {page}/{totalPages} 页
                </div>

                <div className="flex items-center gap-1">
                  <button onClick={() => setPage(1)} disabled={page === 1}
                    className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50">
                    首页
                  </button>
                  <button onClick={() => setPage(page - 1)} disabled={page === 1}
                    className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50">
                    上一页
                  </button>
                  <button onClick={() => setPage(page + 1)} disabled={page >= totalPages}
                    className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50">
                    下一页
                  </button>
                  <button onClick={() => setPage(totalPages)} disabled={page >= totalPages}
                    className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50">
                    末页
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 右侧 - 筛选和统计 */}
        <div className="w-80 bg-gray-50 overflow-y-auto p-4 shrink-0 space-y-4">
          {/* 筛选栏 */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-gray-700">🔍 筛选</h2>
              {hasFilters && (
                <button onClick={clearFilters} className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1">
                  <X className="w-3 h-3" /> 清除
                </button>
              )}
            </div>

            {/* 搜索框 */}
            <div className="relative mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索消息..."
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* 平台选择 */}
            <div className="mb-4">
              <h3 className="text-xs font-medium text-gray-500 mb-2">渠道</h3>
              <div className="flex flex-wrap gap-1">
                {platforms.map((p) => (
                  <button
                    key={p.id || 'all'}
                    onClick={() => setSelectedPlatform(p.id)}
                    className={clsx(
                      'px-2 py-1 rounded text-xs transition-colors',
                      selectedPlatform === p.id
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {p.icon} {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* 情感选择 */}
            <div className="mb-4">
              <h3 className="text-xs font-medium text-gray-500 mb-2">情感</h3>
              <div className="flex flex-wrap gap-1">
                {sentiments.map((s) => (
                  <button
                    key={s.id || 'all'}
                    onClick={() => setSelectedSentiment(s.id)}
                    className={clsx(
                      'px-2 py-1 rounded text-xs transition-colors',
                      selectedSentiment === s.id
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    )}
                  >
                    {s.icon} {s.name}
                  </button>
                ))}
              </div>
            </div>

            {/* 时间范围 */}
            <div className="mb-4">
              <h3 className="text-xs font-medium text-gray-500 mb-2">时间</h3>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={dateRange.since?.toISOString().split('T')[0] || ''}
                  onChange={(e) => setDateRange(e.target.value ? new Date(e.target.value) : null, dateRange.until)}
                  className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs"
                />
                <span className="text-gray-400">-</span>
                <input
                  type="date"
                  value={dateRange.until?.toISOString().split('T')[0] || ''}
                  onChange={(e) => setDateRange(dateRange.since, e.target.value ? new Date(e.target.value) : null)}
                  className="flex-1 px-2 py-1 border border-gray-300 rounded text-xs"
                />
              </div>
            </div>

            {/* 标签筛选 */}
            {categoriesData?.categories && categoriesData.categories.length > 0 && (
              <div>
                <h3 className="text-xs font-medium text-gray-500 mb-2">标签</h3>
                <div className="flex flex-wrap gap-1 max-h-32 overflow-y-auto">
                  {categoriesData.categories.map((cat) => (
                    <button
                      key={cat.name}
                      onClick={() => toggleCategory(cat.name)}
                      className={clsx(
                        'px-2 py-0.5 rounded text-xs transition-colors',
                        selectedCategories.includes(cat.name)
                          ? 'bg-blue-500 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      )}
                    >
                      {cat.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 统计信息 */}
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <h2 className="text-sm font-medium text-gray-700 mb-4">📈 统计</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-blue-100 flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-blue-600" />
                </div>
                <div>
                  <div className="text-lg font-bold text-gray-900">{stats?.totalMessages || 0}</div>
                  <div className="text-xs text-gray-500">总消息</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-green-100 flex items-center justify-center">
                  <Calendar className="w-4 h-4 text-green-600" />
                </div>
                <div>
                  <div className="text-lg font-bold text-gray-900">{stats?.messagesToday || 0}</div>
                  <div className="text-xs text-gray-500">今日</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-purple-100 flex items-center justify-center">
                  <TrendingUp className="w-4 h-4 text-purple-600" />
                </div>
                <div>
                  <div className="text-lg font-bold text-gray-900">{stats?.messagesThisWeek || 0}</div>
                  <div className="text-xs text-gray-500">本周</div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-orange-100 flex items-center justify-center">
                  <Hash className="w-4 h-4 text-orange-600" />
                </div>
                <div>
                  <div className="text-lg font-bold text-gray-900">{stats?.totalChannels || 0}</div>
                  <div className="text-xs text-gray-500">渠道</div>
                </div>
              </div>
            </div>

            {/* 平台分布 */}
            {stats?.messagesByPlatform && Object.keys(stats.messagesByPlatform).length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <h3 className="text-xs font-medium text-gray-500 mb-2">平台</h3>
                <div className="space-y-1">
                  {Object.entries(stats.messagesByPlatform).map(([platform, count]) => (
                    <div key={platform} className="flex items-center justify-between text-sm">
                      <span className="text-gray-600 capitalize">{platform}</span>
                      <span className="font-medium text-gray-900">{count as number}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
