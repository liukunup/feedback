/**
 * 首页 / 仪表盘
 */
import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';

import { FilterBar } from '../components/FilterBar';
import { MessageList } from '../components/MessageList';
import { Statistics } from '../components/Statistics';
import { messageApi, searchApi } from '../services/api';
import { useAppStore } from '../stores/appStore';

export const Dashboard: React.FC = () => {
  const {
    selectedPlatform,
    searchQuery,
    selectedSentiment,
    selectedCategories,
    dateRange,
    isRefreshing,
    setRefreshing,
  } = useAppStore();

  // 获取统计数据
  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: () => searchApi.stats(),
    refetchInterval: 60000, // 每分钟刷新
  });

  // 获取标签列表
  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => searchApi.categories(50),
  });

  // 获取消息列表
  const [page, setPage] = useState(1);
  const { data: messagesData, isLoading, refetch } = useQuery({
    queryKey: ['messages', selectedPlatform, searchQuery, selectedSentiment, selectedCategories, dateRange, page],
    queryFn: () =>
      messageApi.list({
        platform: selectedPlatform || undefined,
        sentiment: selectedSentiment || undefined,
        category: selectedCategories[0] || undefined,
        since: dateRange.since?.toISOString(),
        until: dateRange.until?.toISOString(),
        page,
        pageSize: 20,
      }),
    enabled: !searchQuery, // 有搜索关键词时用搜索 API
  });

  // 搜索结果
  const { data: searchData, refetch: searchRefetch } = useQuery({
    queryKey: ['search', searchQuery, selectedPlatform, selectedSentiment, selectedCategories],
    queryFn: () =>
      searchApi.search({
        query: searchQuery,
        platforms: selectedPlatform ? [selectedPlatform as any] : undefined,
        sentiment: selectedSentiment as any || undefined,
        categories: selectedCategories,
        page,
        pageSize: 20,
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

  // 处理搜索
  const handleSearch = () => {
    setPage(1);
  };

  const messages = searchQuery
    ? searchData?.items || []
    : messagesData?.items || [];

  const total = searchQuery
    ? searchData?.total || 0
    : messagesData?.total || 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 头部 */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-900">
            📊 Social Feed Aggregator
          </h1>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? '刷新中...' : '刷新'}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* 统计信息 */}
        {stats && <Statistics stats={stats} />}

        <div className="flex gap-6">
          {/* 侧边栏 */}
          <aside className="w-80 flex-shrink-0 hidden lg:block">
            <FilterBar
              categories={categoriesData?.categories || []}
              onSearch={handleSearch}
            />
          </aside>

          {/* 主内容 */}
          <div className="flex-1">
            {/* 移动端筛选 */}
            <div className="lg:hidden mb-4">
              <FilterBar
                categories={categoriesData?.categories || []}
                onSearch={handleSearch}
              />
            </div>

            {/* 消息列表 */}
            <MessageList
              messages={messages}
              isLoading={isLoading}
            />

            {/* 分页 */}
            {total > 20 && (
              <div className="flex items-center justify-center gap-2 mt-6">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50"
                >
                  上一页
                </button>
                <span className="text-gray-600">
                  第 {page} / {Math.ceil(total / 20)} 页
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * 20 >= total}
                  className="px-4 py-2 bg-white border border-gray-300 rounded-lg disabled:opacity-50"
                >
                  下一页
                </button>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
