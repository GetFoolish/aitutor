import React from 'react';
import type { TutoringAgent } from './types';

interface AgentAvatarBarProps {
  agents: TutoringAgent[];
  speakingAgentId: string | null;
  thinkingStage: string | null;
}

export function AgentAvatarBar({ agents, speakingAgentId, thinkingStage }: AgentAvatarBarProps) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-border bg-card/50">
      <span className="text-xs text-muted-foreground font-medium uppercase tracking-wide mr-1">
        Agents
      </span>
      {agents.map((agent) => {
        const isSpeaking = speakingAgentId === agent.id;
        const isThinking = thinkingStage != null && speakingAgentId === agent.id;
        return (
          <div key={agent.id} className="flex flex-col items-center gap-0.5">
            <div
              className="relative"
              title={`${agent.name} (${agent.role})`}
            >
              <div
                className={`w-9 h-9 rounded-full overflow-hidden border-2 transition-all duration-200 ${
                  isSpeaking
                    ? 'border-[var(--agent-color)] shadow-[0_0_0_2px_var(--agent-color,#3b82f6)]'
                    : 'border-border'
                }`}
                style={{ '--agent-color': agent.color } as React.CSSProperties}
              >
                <img
                  src={agent.avatar}
                  alt={agent.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to initials if avatar fails to load
                    const target = e.currentTarget as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement!;
                    parent.style.backgroundColor = agent.color;
                    parent.style.display = 'flex';
                    parent.style.alignItems = 'center';
                    parent.style.justifyContent = 'center';
                    parent.innerHTML = `<span style="color:white;font-size:14px;font-weight:600">${agent.name[0]}</span>`;
                  }}
                />
              </div>
              {isSpeaking && (
                <span className="absolute -bottom-0.5 -right-0.5 flex h-3 w-3">
                  <span
                    className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
                    style={{ backgroundColor: agent.color }}
                  />
                  <span
                    className="relative inline-flex rounded-full h-3 w-3"
                    style={{ backgroundColor: agent.color }}
                  />
                </span>
              )}
            </div>
            <span className="text-[10px] text-muted-foreground max-w-[44px] truncate text-center">
              {agent.name}
            </span>
          </div>
        );
      })}
      {thinkingStage === 'director' && (
        <span className="ml-2 text-xs text-muted-foreground italic animate-pulse">
          thinking…
        </span>
      )}
    </div>
  );
}
