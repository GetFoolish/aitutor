import { useCallback } from 'react';

interface UseMediaMixerProps {
  socket: WebSocket | null;
}

interface MediaMixerCommand {
  type: string;
  data?: any;
}

export function useMediaMixer({ socket }: UseMediaMixerProps) {
  const sendCommand = useCallback(
    (command: MediaMixerCommand) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        const commandString = JSON.stringify(command);
        console.log(`Sending command to MediaMixer:`, command);
        socket.send(commandString);
      } else {
        console.error('MediaMixer socket not connected or not available.');
      }
    },
    [socket]
  );

  const toggleCamera = useCallback(
    (enabled: boolean) => {
      sendCommand({ type: 'toggle_camera', data: { enabled } });
    },
    [sendCommand]
  );

  const toggleScreen = useCallback(
    (enabled: boolean) => {
      sendCommand({ type: 'toggle_screen', data: { enabled } });
    },
    [sendCommand]
  );

  return { sendCommand, toggleCamera, toggleScreen };
}
