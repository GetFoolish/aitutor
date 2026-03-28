import React from 'react';
import type { ClassroomMessage } from './types';

interface ClassroomChatMessageProps {
  message: ClassroomMessage;
}

export function ClassroomChatMessage({ message }: ClassroomChatMessageProps) {
  const isUser = message.isUser;

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-3`}>
      {/* Avatar */}
      {!isUser && (
        <div
          className="w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center overflow-hidden border border-border"
          style={{ backgroundColor: message.agentColor ?? '#6b7280' }}
        >
          {message.agentAvatar ? (
            <img
              src={message.agentAvatar}
              alt={message.agentName}
              className="w-full h-full object-cover"
              onError={(e) => {
                const t = e.currentTarget as HTMLImageElement;
                t.style.display = 'none';
              }}
            />
          ) : (
            <span className="text-white text-xs font-semibold">{message.agentName[0]}</span>
          )}
        </div>
      )}

      {/* Bubble */}
      <div className={`flex flex-col max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
        {!isUser && (
          <span className="text-[11px] text-muted-foreground mb-1 ml-1 font-medium">
            {message.agentName}
          </span>
        )}
        <div
          className={`px-3 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
            isUser
              ? 'bg-primary text-primary-foreground rounded-br-sm'
              : 'bg-muted text-foreground rounded-bl-sm'
          }`}
        >
          {message.content}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 ml-0.5 bg-current align-middle animate-pulse rounded-sm opacity-70" />
          )}
        </div>
      </div>
    </div>
  );
}
