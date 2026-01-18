/**
 * Global listener for scratchpad commands from LiveKit data channel.
 *
 * This hook MUST be used at the App level (always mounted) to receive
 * the `open_scratchpad` command even when the scratchpad is closed.
 */

import { useEffect } from 'react';
import { Room, DataPacket_Kind } from 'livekit-client';

interface ScratchpadMessage {
  type: 'scratchpad_command';
  command: {
    action: string;
    [key: string]: any;
  };
}

export function useGlobalScratchpadListener(room: Room | null) {
  useEffect(() => {
    if (!room) {
      console.log('[GlobalScratchpad] No room yet, waiting...');
      return;
    }

    const handleDataReceived = (
      payload: Uint8Array,
      participant: any,
      kind: DataPacket_Kind,
      topic?: string
    ) => {
      // Only process scratchpad messages
      if (topic !== 'scratchpad') {
        return;
      }

      try {
        const text = new TextDecoder().decode(payload);
        const message: ScratchpadMessage = JSON.parse(text);

        if (message.type === 'scratchpad_command' && message.command) {
          console.log('[GlobalScratchpad] Received command:', message.command.action);

          // Handle open_scratchpad globally (even when scratchpad is closed)
          if (message.command.action === 'open_scratchpad') {
            console.log('[GlobalScratchpad] Opening scratchpad panel');
            window.dispatchEvent(new CustomEvent('ai-open-scratchpad'));
          }
        }
      } catch (error) {
        console.error('[GlobalScratchpad] Error parsing message:', error);
      }
    };

    room.on('dataReceived', handleDataReceived);
    console.log('[GlobalScratchpad] Listening for commands on room:', room.name);

    return () => {
      room.off('dataReceived', handleDataReceived);
    };
  }, [room]);
}
