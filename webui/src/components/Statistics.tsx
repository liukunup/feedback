/**
 * 统计信息组件
 */
import React from 'react';
import { 
  MessageSquare, 
  Hash, 
  TrendingUp, 
  Calendar,
  Smile,
  Meh,
  Frown
} from 'lucide-react';
import type { StatisticsResponse } from '../types';

interface StatisticsProps {
  stats: StatisticsResponse;
}

export const Statistics: React.FC<StatisticsProps> = ({ stats }) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {/* 总消息数 */}
      <StatCard
        icon={<MessageSquare className="w-5 h-5" />}
        label="总消息数"
        value={stats.totalMessages.toLocaleString()}
        color="blue"
      />

      {/* 今日消息 */}
      <StatCard
        icon={<Calendar className="w-5 h-5" />}
        label="今日消息"
        value={stats.messagesToday.toLocaleString()}
        color="green"
      />

      {/* 本周消息 */}
      <StatCard
        icon={<TrendingUp className="w-5 h-5" />}
        label="本周消息"
        value={stats.messagesThisWeek.toLocaleString()}
        color="purple"
      />

      {/* 渠道数 */}
      <StatCard
        icon={<Hash className="w-5 h-5" />}
        label="渠道数"
        value={stats.totalChannels.toString()}
        color="orange"
      />

      {/* 情感分布 */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 md:col-span-4">
        <h3 className="text-sm font-medium text-gray-700 mb-3">情感分布</h3>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Smile className="w-5 h-5 text-green-500" />
            <span className="text-2xl font-bold text-green-600">
              {stats.messagesBySentiment.positive || 0}
            </span>
            <span className="text-sm text-gray-500">正面</span>
          </div>
          <div className="flex items-center gap-2">
            <Meh className="w-5 h-5 text-gray-400" />
            <span className="text-2xl font-bold text-gray-600">
              {stats.messagesBySentiment.neutral || 0}
            </span>
            <span className="text-sm text-gray-500">中性</span>
          </div>
          <div className="flex items-center gap-2">
            <Frown className="w-5 h-5 text-red-500" />
            <span className="text-2xl font-bold text-red-600">
              {stats.messagesBySentiment.negative || 0}
            </span>
            <span className="text-sm text-gray-500">负面</span>
          </div>
        </div>
      </div>

      {/* Top 标签 */}
      {stats.topCategories.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 md:col-span-4">
          <h3 className="text-sm font-medium text-gray-700 mb-3">热门标签</h3>
          <div className="flex flex-wrap gap-2">
            {stats.topCategories.slice(0, 10).map((cat) => (
              <span
                key={cat.category}
                className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
              >
                {cat.category} ({cat.count})
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: 'blue' | 'green' | 'purple' | 'orange';
}

const StatCard: React.FC<StatCardProps> = ({ icon, label, value, color }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    purple: 'bg-purple-50 text-purple-600',
    orange: 'bg-orange-50 text-orange-600',
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${colorClasses[color]} mb-3`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );
};

export default Statistics;
