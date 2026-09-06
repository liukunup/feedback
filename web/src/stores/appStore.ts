/**
 * 全局状态管理
 */
import { create } from 'zustand';

interface AppState {
  // 当前选中的平台
  selectedPlatform: string | null;
  setSelectedPlatform: (platform: string | null) => void;
  
  // 搜索关键词
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  
  // 选中的情感
  selectedSentiment: string | null;
  setSelectedSentiment: (sentiment: string | null) => void;
  
  // 选中的标签
  selectedCategories: string[];
  setSelectedCategories: (categories: string[]) => void;
  toggleCategory: (category: string) => void;
  
  // 时间范围
  dateRange: {
    since: Date | null;
    until: Date | null;
  };
  setDateRange: (since: Date | null, until: Date | null) => void;
  
  // 侧边栏展开
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  
  // 刷新状态
  isRefreshing: boolean;
  setRefreshing: (refreshing: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // 平台选择
  selectedPlatform: null,
  setSelectedPlatform: (platform) => set({ selectedPlatform: platform }),
  
  // 搜索
  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),
  
  // 情感
  selectedSentiment: null,
  setSelectedSentiment: (sentiment) => set({ selectedSentiment: sentiment }),
  
  // 标签
  selectedCategories: [],
  setSelectedCategories: (categories) => set({ selectedCategories: categories }),
  toggleCategory: (category) => 
    set((state) => ({
      selectedCategories: state.selectedCategories.includes(category)
        ? state.selectedCategories.filter((c) => c !== category)
        : [...state.selectedCategories, category],
    })),
  
  // 时间范围
  dateRange: {
    since: null,
    until: null,
  },
  setDateRange: (since, until) => set({ dateRange: { since, until } }),
  
  // 侧边栏
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  
  // 刷新
  isRefreshing: false,
  setRefreshing: (refreshing) => set({ isRefreshing: refreshing }),
}));
