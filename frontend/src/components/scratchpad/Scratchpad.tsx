import { useRef, useState, useEffect } from 'react';
import { FaEraser, FaUndo, FaPen } from 'react-icons/fa';

interface ScratchpadProps {
  height?: number;
}

export function Scratchpad({ height = 300 }: ScratchpadProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [context, setContext] = useState<CanvasRenderingContext2D | null>(null);
  const [history, setHistory] = useState<ImageData[]>([]);
  const [penColor] = useState('#ffffff');
  const [penSize, setPenSize] = useState(3);
  const commandSocketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = height;

    // Configure drawing context
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = penColor;
    ctx.lineWidth = penSize;

    setContext(ctx);

    // Save initial blank state
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    setHistory([imageData]);
  }, [height, penColor, penSize]);

  useEffect(() => {
    if (context) {
      context.strokeStyle = penColor;
      context.lineWidth = penSize;
    }
  }, [penColor, penSize, context]);

  // Connect to MediaMixer command WebSocket
  useEffect(() => {
    console.log('[Scratchpad] Connecting to MediaMixer...');
    const commandWs = new WebSocket('ws://localhost:8765');

    commandWs.onopen = () => {
      console.log('[Scratchpad] Connected to MediaMixer command server');
    };

    commandWs.onerror = (err) => {
      console.error('[Scratchpad] MediaMixer command WebSocket error:', err);
    };

    commandWs.onclose = () => {
      console.log('[Scratchpad] MediaMixer command WebSocket disconnected');
    };

    commandSocketRef.current = commandWs;

    return () => {
      console.log('[Scratchpad] Closing MediaMixer command WebSocket');
      commandWs.close();
    };
  }, []);

  // Send canvas frames to MediaMixer periodically
  useEffect(() => {
    if (!canvasRef.current || !commandSocketRef.current) return;

    const sendFrameToMediaMixer = () => {
      const canvas = canvasRef.current;
      const ws = commandSocketRef.current;

      if (!canvas || !ws || ws.readyState !== WebSocket.OPEN) return;

      try {
        // Convert canvas to base64 image
        const dataUrl = canvas.toDataURL('image/png');

        // Send to MediaMixer
        ws.send(JSON.stringify({
          type: 'scratchpad_frame',
          data: dataUrl
        }));
      } catch (error) {
        console.error('[Scratchpad] Error sending frame to MediaMixer:', error);
      }
    };

    // Send frames at 2 FPS (every 500ms) - balance between responsiveness and performance
    const interval = setInterval(sendFrameToMediaMixer, 500);

    return () => clearInterval(interval);
  }, [context]);

  const saveState = (ctx: CanvasRenderingContext2D) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    setHistory((prev) => [...prev, imageData]);
  };

  const startDrawing = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!context) return;

    setIsDrawing(true);
    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    context.beginPath();
    context.moveTo(x, y);
  };

  const draw = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!isDrawing || !context) return;

    const rect = canvasRef.current!.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    context.lineTo(x, y);
    context.stroke();
  };

  const stopDrawing = () => {
    if (!isDrawing || !context) return;

    setIsDrawing(false);
    context.closePath();
    saveState(context);
  };

  const clearCanvas = () => {
    if (!context || !canvasRef.current) return;

    context.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    setHistory([]);
  };

  const undo = () => {
    if (!context || !canvasRef.current || history.length <= 1) return;

    const newHistory = [...history];
    newHistory.pop();
    const previousState = newHistory[newHistory.length - 1];

    if (previousState) {
      context.putImageData(previousState, 0, 0);
      setHistory(newHistory);
    }
  };

  return (
    <div className="scratchpad-container" style={{
      background: 'var(--surface-light)',
      border: '2px dashed var(--border)',
      borderRadius: 'var(--radius)',
      padding: 'var(--space-2)',
      marginBottom: 'var(--space-3)',
      scrollMarginTop: '80px', // Space for fixed headers when scrolling
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 'var(--space-2)',
        paddingBottom: 'var(--space-1)',
        borderBottom: '1px solid var(--border)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          <span style={{ fontSize: '14px', color: 'var(--text-secondary)', fontWeight: 600 }}>
            <FaPen size={12} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
            Scratchpad
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
          <select
            value={penSize}
            onChange={(e) => setPenSize(Number(e.target.value))}
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              padding: '4px 8px',
              color: 'var(--text-primary)',
              fontSize: '12px',
              cursor: 'pointer',
            }}
          >
            <option value="2">Thin</option>
            <option value="3">Normal</option>
            <option value="5">Thick</option>
          </select>

          <button
            onClick={undo}
            disabled={history.length <= 1}
            className="btn"
            style={{
              padding: '6px 10px',
              fontSize: '12px',
              minHeight: 'unset',
              opacity: history.length <= 1 ? 0.5 : 1,
            }}
            title="Undo"
          >
            <FaUndo size={12} />
          </button>

          <button
            onClick={clearCanvas}
            className="btn"
            style={{
              padding: '6px 10px',
              fontSize: '12px',
              minHeight: 'unset',
            }}
            title="Clear"
          >
            <FaEraser size={12} />
          </button>
        </div>
      </div>

      <canvas
        ref={canvasRef}
        onMouseDown={startDrawing}
        onMouseMove={draw}
        onMouseUp={stopDrawing}
        onMouseLeave={stopDrawing}
        style={{
          width: '100%',
          height: `${height}px`,
          background: '#0a0e14',
          borderRadius: 'var(--radius-sm)',
          cursor: 'crosshair',
          display: 'block',
        }}
      />

      <p style={{
        fontSize: '11px',
        color: 'var(--text-tertiary)',
        margin: 'var(--space-1) 0 0',
        fontStyle: 'italic',
      }}>
        Use this space to work out your answer
      </p>
    </div>
  );
}
