/**
 * 渠道切换和筛选组件
 */
import { clsx } from 'clsx';
import { Search, X } from 'lucide-react';
import { useAppStore } from '../stores/appStore';

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

interface FilterBarProps {
  categories: Array<{ name: string; count: number }>;
  onSearch: () => void;
}

export const FilterBar: React.FC<FilterBarProps> = ({ categories, onSearch }) => {
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
  } = useAppStore();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch();
  };

  const clearFilters = () => {
    setSelectedPlatform(null);
    setSelectedSentiment(null);
    setSearchQuery('');
    setDateRange(null, null);
  };

  const hasFilters = selectedPlatform || selectedSentiment || searchQuery || selectedCategories.length > 0;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-4">
      {/* 搜索框 */}
      <form onSubmit={handleSearch} className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索消息内容、作者..."
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </form>

      {/* 平台选择 */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">渠道</h3>
        <div className="flex flex-wrap gap-2">
          {platforms.map((p) => (
            <button
              key={p.id || 'all'}
              onClick={() => setSelectedPlatform(p.id)}
              className={clsx(
                'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                selectedPlatform === p.id
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {p.icon} {p.name}
            </button>
          ))}
        </div>
      </div>

      {/* 情感选择 */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">情感</h3>
        <div className="flex flex-wrap gap-2">
          {sentiments.map((s) => (
            <button
              key={s.id || 'all'}
              onClick={() => setSelectedSentiment(s.id)}
              className={clsx(
                'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                selectedSentiment === s.id
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              )}
            >
              {s.icon} {s.name}
            </button>
          ))}
        </div>
      </div>

      {/* 标签筛选 */}
      {categories.length > 0 && (
        <div className="mb-4">
          <h3 className="text-sm font-medium text-gray-700 mb-2">标签</h3>
          <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto">
            {categories.map((cat) => (
              <button
                key={cat.name}
                onClick={() => toggleCategory(cat.name)}
                className={clsx(
                  'px-3 py-1 rounded-full text-sm transition-colors',
                  selectedCategories.includes(cat.name)
                    ? 'bg-blue-500 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                )}
              >
                {cat.name} ({cat.count})
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 时间范围 */}
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-700 mb-2">时间范围</h3>
        <div className="flex gap-2">
          <input
            type="date"
            value={dateRange.since?.toISOString().split('T')[0] || ''}
            onChange={(e) => setDateRange(e.target.value ? new Date(e.target.value) : null, dateRange.until)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
          />
          <span className="self-center text-gray-400">至</span>
          <input
            type="date"
            value={dateRange.until?.toISOString().split('T')[0] || ''}
            onChange={(e) => setDateRange(dateRange.since, e.target.value ? new Date(e.target.value) : null)}
            className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
          />
        </div>
      </div>

      {/* 清除筛选 */}
      {hasFilters && (
        <button
          onClick={clearFilters}
          className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
        >
          <X className="w-4 h-4" />
          清除筛选
        </button>
      )}
    </div>
  );
};

export default FilterBar;
