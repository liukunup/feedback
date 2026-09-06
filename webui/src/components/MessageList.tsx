/**
 * 消息列表组件
 */
import React from 'react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { clsx } from 'clsx';
import { 
  MessageSquare, 
  ThumbsUp, 
  ThumbsDown, 
  Minus,
  Paperclip,
} from 'lucide-react';
import type { Message, Sentiment, Platform } from '../types';

// 平台图标映射
const platformIcons: Record<Platform, string> = {
  discord: '📱',
  reddit: '📘',
  qq: '💬',
  wecom: '💼',
};

// 情感图标
const sentimentIcons: Record<Sentiment, React.ReactNode> = {
  positive: <ThumbsUp className="w-4 h-4 text-green-500" />,
  neutral: <Minus className="w-4 h-4 text-gray-400" />,
  negative: <ThumbsDown className="w-4 h-4 text-red-500" />,
};

interface MessageListProps {
  messages: Message[];
  onMessageClick?: (message: Message) => void;
  isLoading?: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  onMessageClick,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="h-32 bg-gray-200 rounded-lg" />
          </div>
        ))}
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="text-center py-12">
        <MessageSquare className="w-12 h-12 mx-auto text-gray-400 mb-4" />
        <p className="text-gray-500">暂无消息</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageCard
          key={message.id}
          message={message}
          onClick={() => onMessageClick?.(message)}
        />
      ))}
    </div>
  );
};

interface MessageCardProps {
  message: Message;
  onClick?: () => void;
}

const MessageCard: React.FC<MessageCardProps> = ({ message, onClick }) => {
  const platform = message.platform || 'discord';
  
  return (
    <div
      className={clsx(
        'bg-white rounded-lg shadow-sm border border-gray-200 p-4',
        'hover:shadow-md transition-shadow cursor-pointer'
      )}
      onClick={onClick}
    >
      {/* 头部 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">{platformIcons[platform]}</span>
          <span className="font-medium text-gray-900">
            {message.channelName || message.authorName}
          </span>
          <span className="text-sm text-gray-500">
            @{message.authorName}
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          {sentimentIcons[message.sentiment as Sentiment]}
          <span>
            {message.createdAt ? formatDistanceToNow(new Date(message.createdAt), {
              addSuffix: true,
              locale: zhCN,
            }) : '未知时间'}
          </span>
        </div>
      </div>

      {/* 内容 */}
      <div className="mb-3">
        <p className="text-gray-800 whitespace-pre-wrap">{message.content}</p>
      </div>

      {/* 附件 */}
      {message.attachments && message.attachments.length > 0 && (
        <div className="flex items-center gap-2 mb-3 text-sm text-gray-500">
          <Paperclip className="w-4 h-4" />
          <span>{message.attachments.length} 个附件</span>
        </div>
      )}

      {/* 标签 */}
      <div className="flex items-center gap-2 flex-wrap">
        {message.categories?.map((category) => (
          <span
            key={category}
            className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs"
          >
            {category}
          </span>
        ))}
        {(!message.categories || message.categories.length === 0) && (
          <span className="px-2 py-1 bg-gray-100 text-gray-500 rounded-full text-xs">
            未分类
          </span>
        )}
      </div>

      {/* AI 分析摘要 */}
      {message.summary && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <p className="text-sm text-gray-600 italic">
            💡 {message.summary}
          </p>
        </div>
      )}
    </div>
  );
};

export default MessageList;
