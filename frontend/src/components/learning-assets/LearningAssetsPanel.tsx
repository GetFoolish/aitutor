import React, { useEffect, useState } from 'react';
import cn from 'classnames';
import { Skeleton } from '../ui/skeleton';
import { useAuth } from '../../contexts/AuthContext';
import { Play, Video as VideoIcon } from 'lucide-react';

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

interface LearningVideo {
  video_id: string;
  title: string;
  language: string;
  score?: number;
  approved_at?: string;
}

interface LearningAssetsPanelProps {
  questionId: string | null;
  open: boolean;
  onToggle: () => void;
  onVideosWatched?: (videoIds: string[]) => void;
}

const LearningAssetsPanel: React.FC<LearningAssetsPanelProps> = ({
  questionId,
  open,
  onToggle,
  onVideosWatched
}) => {
  const { user } = useAuth();
  const [videos, setVideos] = useState<LearningVideo[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [watchedVideoIds, setWatchedVideoIds] = useState<string[]>([]);

  useEffect(() => {
    if (!questionId || !open) {
      setVideos([]);
      setSelectedVideoId(null);
      setWatchedVideoIds([]);
      return;
    }

    const fetchVideos = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const preferredLanguage = user?.preferred_language || 'English';
        const token = localStorage.getItem('jwt_token');
        
        const response = await fetch(
          `${DASH_API_URL}/api/learning-assets/videos/${questionId}?preferred_language=${encodeURIComponent(preferredLanguage)}`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch learning videos');
        }

        const data = await response.json();
        setVideos(data);
        
        // Auto-select first video
        if (data.length > 0 && data[0].video_id) {
          setSelectedVideoId(data[0].video_id);
        }
      } catch (err: any) {
        console.error('Error fetching learning videos:', err);
        setError(err?.message || 'Failed to load videos');
        setVideos([]);
      } finally {
        setLoading(false);
      }
    };

    fetchVideos();
  }, [questionId, open, user?.preferred_language]);

  const handleVideoSelect = (videoId: string) => {
    setSelectedVideoId(videoId);
    // Track that this video was watched
    if (!watchedVideoIds.includes(videoId)) {
      const updatedWatchedIds = [...watchedVideoIds, videoId];
      setWatchedVideoIds(updatedWatchedIds);
      // Notify parent component
      if (onVideosWatched) {
        onVideosWatched(updatedWatchedIds);
      }
    }
  };

  return (
    <div
      className={cn(
        "fixed top-[44px] lg:top-[48px] right-0 flex flex-col border-l-[3px] lg:border-l-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform shadow-[-2px_0_0_0_rgba(0,0,0,1)] lg:shadow-[-2px_0_0_0_rgba(0,0,0,1)] dark:shadow-[-2px_0_0_0_rgba(255,255,255,0.3)]",
        "h-[calc(100vh-44px)] lg:h-[calc(100vh-48px)] w-[240px] lg:w-[260px]",
        open ? "translate-x-0" : "translate-x-full",
        "max-md:hidden" // Hide on mobile
      )}
    >
      <header className="flex items-center justify-between h-[44px] lg:h-[48px] px-3 lg:px-4 border-b-[3px] border-black dark:border-white shrink-0 overflow-hidden transition-all duration-300 bg-[#C4B5FD]">
        <div className="flex items-center gap-2 lg:gap-2.5 animate-in fade-in slide-in-from-right-4 duration-300">
          <div className="p-1.5 lg:p-2 border-[2px] lg:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
            <VideoIcon className="w-4 h-4 lg:w-4 lg:h-4 text-black dark:text-white font-bold" />
          </div>
          <h2 className="text-sm lg:text-base font-black text-black uppercase tracking-tight whitespace-nowrap">
            Learning Assets
          </h2>
        </div>
      </header>

      <div className="flex flex-col flex-grow overflow-hidden bg-[#FFFDF5] dark:bg-[#000000]">
        {loading ? (
          <div className="p-4 space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : error ? (
          <div className="p-4">
            <p className={cn(
              "text-sm font-bold text-red-600 dark:text-red-400"
            )}>
              {error}
            </p>
          </div>
        ) : videos.length === 0 ? (
          <div className="p-4">
            <p className={cn(
              "text-sm font-bold text-black dark:text-white"
            )}>
              No learning videos available for this question.
            </p>
          </div>
        ) : (
          <>
            {/* Video Player */}
            {selectedVideoId && (
              <div className="p-4 border-b-[3px] border-black dark:border-white">
                <div className={cn(
                  "relative w-full bg-black",
                  "border-[2px] border-black dark:border-white"
                )} style={{ paddingBottom: '56.25%' }}>
                  <iframe
                    className="absolute top-0 left-0 w-full h-full"
                    src={`https://www.youtube.com/embed/${selectedVideoId}`}
                    title="Learning Video"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                </div>
              </div>
            )}

            {/* Video List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {videos.map((video, index) => (
                <button
                  key={video.video_id || index}
                  onClick={() => handleVideoSelect(video.video_id)}
                  className={cn(
                    "w-full p-3 text-left border-[2px] border-black dark:border-white",
                    "bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFD93D] dark:hover:bg-[#FFD93D]",
                    "transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] dark:shadow-[1px_1px_0_0_rgba(255,255,255,0.3)]",
                    "hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none",
                    selectedVideoId === video.video_id && "bg-[#C4B5FD] dark:bg-[#C4B5FD]"
                  )}
                >
                  <div className="flex items-start gap-2">
                    <Play className={cn(
                      "w-4 h-4 flex-shrink-0 mt-0.5 text-black dark:text-white"
                    )} />
                    <div className="flex-1 min-w-0">
                      <p className={cn(
                        "text-xs font-bold text-black dark:text-white line-clamp-2"
                      )}>
                        {video.title || 'Untitled Video'}
                      </p>
                      {video.language && (
                        <p className={cn(
                          "text-[10px] font-bold text-black dark:text-white opacity-70 mt-1"
                        )}>
                          {video.language}
                        </p>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default LearningAssetsPanel;

