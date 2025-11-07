import React, { useEffect, useState, RefObject } from 'react';
import cn from 'classnames';
import { RiSidebarFoldLine, RiSidebarUnfoldLine } from "react-icons/ri";
import { useMediaMixer } from '../../hooks/use-media-mixer';
import './media-mixer-display.scss';

interface MediaMixerDisplayProps {
  socket: WebSocket | null;
  renderCanvasRef: RefObject<HTMLCanvasElement>;
}

const MediaMixerDisplay: React.FC<MediaMixerDisplayProps> = ({ socket, renderCanvasRef }) => {
  const [imageData, setImageData] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Get MediaMixer command socket to enable screen sharing
  const [commandSocket, setCommandSocket] = useState<WebSocket | null>(null);
  const { toggleScreen } = useMediaMixer({ socket: commandSocket });

  // Setup command socket connection for sending toggle commands
  useEffect(() => {
    console.log('MediaMixerDisplay: Connecting to command WebSocket on ws://localhost:8765');
    const ws = new WebSocket('ws://localhost:8765');

    ws.onopen = () => {
      console.log('MediaMixerDisplay: Command socket connected');
      setCommandSocket(ws);
    };

    ws.onerror = (err) => {
      console.error('MediaMixerDisplay: Command socket error:', err);
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, []);

  // Disable automatic screen sharing - user video only
  useEffect(() => {
    if (commandSocket && commandSocket.readyState === WebSocket.OPEN) {
      console.log('MediaMixerDisplay: Screen sharing disabled (showing user video only)');
      // toggleScreen(true); // Commented out to show only user camera, not screen
    }
  }, [commandSocket, toggleScreen]);

  useEffect(() => {
    if (!socket) {
      console.log('MediaMixerDisplay: No socket provided yet');
      return;
    }

    console.log('MediaMixerDisplay: Setting up video WebSocket connection');
    console.log('MediaMixerDisplay: Socket readyState:', socket.readyState);

    const image = new Image();
    image.onload = () => {
      const canvas = renderCanvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          canvas.width = image.width;
          canvas.height = image.height;
          ctx.drawImage(image, 0, 0);
        }
      }
    };

    // Check if already connected (readyState === 1 means OPEN)
    if (socket.readyState === WebSocket.OPEN) {
      console.log('MediaMixerDisplay: Socket already connected');
      setIsConnected(true);
      setError(null);
    }

    const handleOpen = () => {
      console.log('MediaMixerDisplay: Connected to video WebSocket');
      setIsConnected(true);
      setError(null);
    };

    const handleMessage = (event: MessageEvent) => {
      const frame = event.data;
      const imageUrl = `data:image/jpeg;base64,${frame}`;
      setImageData(imageUrl);
      image.src = imageUrl;
    };

    const handleError = (err: Event) => {
      console.error('MediaMixerDisplay: WebSocket error:', err);
      setError('Failed to connect to MediaMixer video stream. Is it running?');
      setIsConnected(false);
    };

    const handleClose = () => {
      console.log('MediaMixerDisplay: Disconnected from video WebSocket');
      setIsConnected(false);
    };

    socket.addEventListener('open', handleOpen);
    socket.addEventListener('message', handleMessage);
    socket.addEventListener('error', handleError);
    socket.addEventListener('close', handleClose);

    return () => {
      console.log('MediaMixerDisplay: Cleaning up video WebSocket');
      socket.removeEventListener('open', handleOpen);
      socket.removeEventListener('message', handleMessage);
      socket.removeEventListener('error', handleError);
      socket.removeEventListener('close', handleClose);
    };
  }, [socket, renderCanvasRef]);

  return (
    <div className={cn("media-mixer-display", { "collapsed": isCollapsed })} style={{ border: '2px solid var(--border)', borderRadius: 'var(--radius)' }}>
      <header className="top" style={{ background: 'var(--surface-light)', padding: 'var(--space-2)', borderBottom: '1px solid var(--border)' }}>
        <button onClick={() => setIsCollapsed(!isCollapsed)} className="collapse-button">
          {isCollapsed ? (
            <RiSidebarUnfoldLine color="#b4b8bb" />
          ) : (
            <RiSidebarFoldLine color="#b4b8bb" />
          )}
        </button>
        <h2 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
          Your Workspace {isConnected && <span style={{ color: 'var(--success)', fontSize: '12px' }}>● Live</span>}
        </h2>
      </header>
      <div className="media-mixer-content" style={{ padding: 'var(--space-2)', minHeight: '200px', background: 'var(--bg)' }}>
        {error && <div className="error-message" style={{ color: 'var(--error)', padding: 'var(--space-2)', background: 'rgba(255, 112, 112, 0.1)', borderRadius: 'var(--radius-sm)' }}>{error}</div>}
        {!socket && <div style={{ color: 'var(--text-secondary)', padding: 'var(--space-2)' }}>Waiting for workspace connection...</div>}
        {socket && !isConnected && !error && <div style={{ color: 'var(--warning)', padding: 'var(--space-2)' }}>Connecting to your workspace...</div>}
        {isConnected && !imageData && <div style={{ color: 'var(--accent)', padding: 'var(--space-2)' }}>Workspace connected! Waiting for video...</div>}
        {isConnected && imageData && (
          <div>
            <img
              src={imageData}
              alt="Your workspace - Use paper/whiteboard to work out problems"
              style={{
                width: '100%',
                height: 'auto',
                borderRadius: 'var(--radius-sm)',
                border: '2px solid var(--success)'
              }}
            />
            <p style={{
              fontSize: '12px',
              color: 'var(--text-tertiary)',
              marginTop: 'var(--space-1)',
              fontStyle: 'italic',
              textAlign: 'center'
            }}>
              Use your paper or whiteboard to work out the problem
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default MediaMixerDisplay;
