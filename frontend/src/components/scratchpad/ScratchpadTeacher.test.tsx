// @vitest-environment jsdom
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { ScratchpadTeacher } from './ScratchpadTeacher';
import type { InstructionSet } from './types';

// Mock fetch
global.fetch = vi.fn();

// Mock tldraw
vi.mock('tldraw', () => ({
  Tldraw: ({ onMount }: { onMount: (editor: any) => void }) => {
    // Simulate mounting with a mock editor
    setTimeout(() => {
      onMount({
        createShape: vi.fn((shape) => shape.id),
        deleteShape: vi.fn(),
        getCurrentPageShapes: vi.fn(() => []),
        updateInstanceState: vi.fn(),
      });
    }, 0);
    return <div data-testid="tldraw-canvas">Tldraw Canvas</div>;
  },
  createShapeId: (id: string) => `shape:${id}`,
  toRichText: (text: string) => ({ text }),
}));

// Mock lucide-react icons
vi.mock('lucide-react', () => ({
  Play: () => <span>Play Icon</span>,
  Pause: () => <span>Pause Icon</span>,
  RotateCcw: () => <span>RotateCcw Icon</span>,
  FastForward: () => <span>FastForward Icon</span>,
  SkipBack: () => <span>SkipBack Icon</span>,
  Loader2: () => <span>Loader Icon</span>,
}));

describe('ScratchpadTeacher', () => {
  const mockInstructionSet: InstructionSet = {
    explanation_id: 'test-123',
    concept: '7x6',
    grade_level: '3-5',
    total_duration_ms: 5000,
    steps: [
      {
        action: 'write',
        step_id: 1,
        position: { x: 100, y: 100 },
        text: 'Let\'s solve 7 × 6',
        delay_ms: 0,
        duration_ms: 1000,
        style: { color: 'black', size: 'medium' },
      },
      {
        action: 'draw_groups',
        step_id: 2,
        position: { x: 100, y: 200 },
        object: '🍎',
        rows: 7,
        cols: 6,
        delay_ms: 1000,
        duration_ms: 2000,
        style: { color: 'red', size: 'large' },
      },
      {
        action: 'write',
        step_id: 3,
        position: { x: 100, y: 400 },
        text: '7 × 6 = 42',
        delay_ms: 3000,
        duration_ms: 1000,
        style: { color: 'green', size: 'large' },
      },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    
    // Mock successful API response
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockInstructionSet,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows loading state initially', () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    expect(screen.getByText(/loading teaching instructions/i)).toBeInTheDocument();
  });

  it('fetches instructions from API on mount', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:5001/api/scratchpad/generate',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            concept: '7x6',
            grade_level: '3-5',
            context: undefined,
          }),
        })
      );
    });
  });

  it('renders component after loading', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByText(/Teaching: 7x6 \(3-5\)/i)).toBeInTheDocument();
    });
  });

  it('displays tldraw canvas after loading', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByTestId('tldraw-canvas')).toBeInTheDocument();
    });
  });

  it('shows error state on API failure', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('API Error'));
    
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByText(/failed to load instructions/i)).toBeInTheDocument();
    });
  });

  it('displays play button initially', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByTitle('Play')).toBeInTheDocument();
    });
  });

  it('shows all speed options', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByText('0.5x')).toBeInTheDocument();
      expect(screen.getByText('1x')).toBeInTheDocument();
      expect(screen.getByText('1.5x')).toBeInTheDocument();
      expect(screen.getByText('2x')).toBeInTheDocument();
    });
  });

  it('displays progress indicator', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByText(/Step 0\/3/i)).toBeInTheDocument();
      expect(screen.getByText('Paused')).toBeInTheDocument();
    });
  });

  it('can toggle play/pause', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByTitle('Play')).toBeInTheDocument();
    });

    const playButton = screen.getByTitle('Play');
    fireEvent.click(playButton);

    await waitFor(() => {
      expect(screen.getByTitle('Pause')).toBeInTheDocument();
    });

    const pauseButton = screen.getByTitle('Pause');
    fireEvent.click(pauseButton);

    await waitFor(() => {
      expect(screen.getByTitle('Play')).toBeInTheDocument();
    });
  });

  it('shows restart and reset buttons', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByTitle('Restart')).toBeInTheDocument();
      expect(screen.getByTitle('Reset')).toBeInTheDocument();
    });
  });

  it('can change playback speed', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" initialSpeed={1} />);
    
    await waitFor(() => {
      expect(screen.getByText('2x')).toBeInTheDocument();
    });

    const speedButton = screen.getByText('2x');
    fireEvent.click(speedButton);

    // Speed button should now be highlighted
    expect(speedButton).toHaveClass('bg-primary');
  });

  it('calls onPlay callback when play is clicked', async () => {
    const onPlay = vi.fn();
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" onPlay={onPlay} />);
    
    await waitFor(() => {
      expect(screen.getByTitle('Play')).toBeInTheDocument();
    });

    const playButton = screen.getByTitle('Play');
    fireEvent.click(playButton);

    expect(onPlay).toHaveBeenCalledTimes(1);
  });

  it('calls onPause callback when pause is clicked', async () => {
    const onPause = vi.fn();
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" onPause={onPause} />);
    
    await waitFor(() => {
      expect(screen.getByTitle('Play')).toBeInTheDocument();
    });

    // Start playing
    const playButton = screen.getByTitle('Play');
    fireEvent.click(playButton);

    await waitFor(() => {
      expect(screen.getByTitle('Pause')).toBeInTheDocument();
    });

    // Then pause
    const pauseButton = screen.getByTitle('Pause');
    fireEvent.click(pauseButton);

    expect(onPause).toHaveBeenCalledTimes(1);
  });

  it('auto-plays when autoPlay prop is true', async () => {
    const onPlay = vi.fn();
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" autoPlay={true} onPlay={onPlay} />);
    
    await waitFor(() => {
      expect(onPlay).toHaveBeenCalled();
    });
  });

  it('hides controls when showControls is false', async () => {
    render(<ScratchpadTeacher concept="7x6" gradeLevel="3-5" showControls={false} />);
    
    await waitFor(() => {
      expect(screen.getByTestId('tldraw-canvas')).toBeInTheDocument();
    });

    // Control buttons should not be present
    expect(screen.queryByTitle('Play')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Pause')).not.toBeInTheDocument();
  });

  it('passes context to API', async () => {
    render(
      <ScratchpadTeacher 
        concept="fractions" 
        gradeLevel="3-5" 
        context="use pizza slices"
      />
    );
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:5001/api/scratchpad/generate',
        expect.objectContaining({
          body: JSON.stringify({
            concept: 'fractions',
            grade_level: '3-5',
            context: 'use pizza slices',
          }),
        })
      );
    });
  });

  it('applies custom className', async () => {
    const { container } = render(
      <ScratchpadTeacher concept="7x6" gradeLevel="3-5" className="custom-class" />
    );
    
    await waitFor(() => {
      expect(container.querySelector('.custom-class')).toBeInTheDocument();
    });
  });

  it('uses custom apiBaseUrl when provided', async () => {
    render(
      <ScratchpadTeacher 
        concept="7x6" 
        gradeLevel="3-5" 
        apiBaseUrl="https://custom-api.com"
      />
    );
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        'https://custom-api.com/api/scratchpad/generate',
        expect.any(Object)
      );
    });
  });

  it('displays help text', async () => {
    render(<ScratchpadTeacher concept="fractions" gradeLevel="3-5" />);
    
    await waitFor(() => {
      expect(screen.getByText(/Watch as fractions is explained step-by-step/i)).toBeInTheDocument();
    });
  });
});
