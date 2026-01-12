import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import cn from "classnames";
import { BookOpen, Play, X, Search, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { type LearningAsset } from "../../hooks/query-hooks/useLearningAssets";

// Interface for Learning Asset
interface LearningAssetsPanelProps {
    open: boolean;
    onToggle: () => void;
    currentAsset?: LearningAsset | null;
    questionText?: string;
}

export default function LearningAssetsPanel({ open, onToggle, currentAsset, questionText }: LearningAssetsPanelProps) {
    const [activeVideo, setActiveVideo] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [videoOpacity, setVideoOpacity] = useState(0.95);
    const [portalTarget, setPortalTarget] = useState<HTMLElement | null>(null);

    const [selectedExternalAsset, setSelectedExternalAsset] = useState<any | null>(null);

    // Find the portal target (Practice Session card)
    useEffect(() => {
        const target = document.getElementById("practice-session-card");
        setPortalTarget(target);
    }, [activeVideo]); // Re-check when video opens

    // Map currentAsset to array if exists
    const assets = currentAsset ? [currentAsset] : [];

    const filteredAssets = assets.filter(asset =>
        asset.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (asset.category && asset.category.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    // Clean question text for search query
    const getSearchQuery = (text: string) => {
        if (!text) return "";

        // 1. Basic Cleaning
        const cleanText = text
            .replace(/\\text\{([^}]+)\}/g, '$1') // Extract content from \text{} first
            .replace(/\\[a-zA-Z]+/g, ' ')       // Remove other latex commands (\frac, \sqrt etc)
            .replace(/(\$|\\|\{|\})/g, ' ')     // Remove latex delimiters
            .replace(/[#*`_]/g, ' ')            // Remove markdown
            .replace(/[.,/#!$%^&*;:{}=\-_`~()\[\]]/g, "") // Remove punctuation
            .replace(/\s+/g, ' ')               // Collapse whitespace
            .trim()
            .toLowerCase();

        // 2. Stop words list (common English words + question phrasing)
        const stopWords = new Set([
            "pick", "the", "expression", "that", "matches", "this", "description",
            "choose", "answer", "one", "following", "which", "of", "a", "an", "and",
            "or", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "but", "at", "by", "for", "with", "about", "against",
            "between", "into", "through", "during", "before", "after", "above", "below",
            "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where", "why", "how",
            "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
            "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
            "can", "will", "just", "don", "should", "now", "text"
        ]);

        // 3. Filter and prioritized selection
        const words = cleanText.split(' ')
            .filter(w => w.length > 2)          // Filter out tiny words
            .filter(w => !stopWords.has(w));    // Remove stop words

        // Take up to 6 key words
        const query = words.slice(0, 6).join(' ');

        return encodeURIComponent(query);
    };

    const searchQuery = questionText ? getSearchQuery(questionText) : "";
    const searchEmbedUrl = searchQuery
        ? `https://www.youtube.com/embed?listType=search&list=${searchQuery}`
        : "";

    const renderVideoOverlay = () => {
        if (!activeVideo || !portalTarget) return null;

        // Check both database assets AND the selected external asset
        const activeAsset = assets.find(a => (a.videoId === activeVideo) || (a.path === activeVideo)) ||
            (selectedExternalAsset?.videoId === activeVideo ? selectedExternalAsset : null);

        // Use custom youtube-nocookie embed for ad-free experience if videoId exists
        let embedUrl = "";
        if (activeAsset?.videoId) {
            // Using standard youtube.com with origin to prevent redirects
            embedUrl = `https://www.youtube.com/embed/${activeAsset.videoId}?autoplay=1&rel=0&origin=${window.location.origin}`;
            console.log("[VideoOverlay] Loading:", embedUrl);
        } else if (activeAsset?.path) {
            embedUrl = activeAsset.path.startsWith('http')
                ? activeAsset.path
                : `https://www.khanacademy.org/${activeAsset.path.startsWith('/') ? activeAsset.path.substring(1) : activeAsset.path}`;
        }

        return createPortal(
            <div className="absolute inset-0 z-50 flex flex-col overflow-hidden rounded-[inherit]">
                {/* Close Button - Top Right */}
                <Button
                    variant="ghost"
                    size="icon"
                    className="absolute top-4 right-4 z-[60] bg-black/20 hover:bg-black/40 text-white rounded-full h-8 w-8 backdrop-blur-sm transition-all"
                    onClick={() => setActiveVideo(null)}
                >
                    <X className="h-5 w-5" />
                </Button>

                <div
                    className="w-full h-full bg-black transition-opacity duration-300"
                    style={{ opacity: videoOpacity }}
                >
                    <iframe
                        width="100%"
                        height="100%"
                        src={embedUrl}
                        title="Video player"
                        frameBorder="0"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                        allowFullScreen
                        className="w-full h-full"
                    ></iframe>
                </div>

                {/* Opacity Control - Floating Bar */}
                <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-[60] flex items-center gap-4 bg-white/90 dark:bg-black/90 backdrop-blur-md px-6 py-3 rounded-full border-2 border-black dark:border-white shadow-lg transition-all">
                    <div className="flex items-center gap-3 w-48 md:w-64">
                        <Eye className="w-4 h-4 text-gray-500" style={{ opacity: 0.3 }} />
                        <Slider
                            value={[videoOpacity * 100]}
                            onValueChange={(val) => setVideoOpacity(val[0] / 100)}
                            max={100}
                            min={10} // Don't allow total invisibility
                            step={1}
                            className="flex-1"
                        />
                        <Eye className="w-4 h-4 text-black dark:text-white" />
                    </div>
                    <div className="h-4 w-[2px] bg-gray-300 dark:bg-gray-700" />
                    <span className="text-xs font-black min-w-10 text-center">
                        {Math.round(videoOpacity * 100)}%
                    </span>
                </div>
            </div>,
            portalTarget
        );
    };

    return (
        <>
            {renderVideoOverlay()}
            <div
                className={cn(
                    "fixed top-[44px] lg:top-[48px] right-0 flex flex-col border-l-[3px] lg:border-l-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000] transition-all duration-500 cubic-bezier(0.16, 1, 0.3, 1) z-50 will-change-transform shadow-[-2px_0_0_0_rgba(0,0,0,1)] lg:shadow-[-2px_0_0_0_rgba(0,0,0,1)] dark:shadow-[-2px_0_0_0_rgba(255,255,255,0.3)]",
                    "h-[calc(100vh-44px)] lg:h-[calc(100vh-48px)] w-[300px] lg:w-[320px]", // Slightly wider for video thumbs
                    open ? "translate-x-0" : "translate-x-full",
                    "max-md:hidden" // Hide on mobile for now
                )}
            >
                {/* Header */}
                <header className="flex items-center justify-between h-[44px] lg:h-[48px] px-3 lg:px-4 border-b-[3px] border-black dark:border-white shrink-0 overflow-hidden transition-all duration-300 bg-[#C4B5FD]">
                    <div className="flex items-center gap-2 lg:gap-2.5">
                        <div className="p-1.5 lg:p-2 border-[2px] lg:border-[3px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]">
                            <BookOpen className="w-4 h-4 lg:w-4 lg:h-4 text-black dark:text-white font-bold" />
                        </div>
                        <h2 className="text-sm lg:text-base font-black text-black uppercase tracking-tight whitespace-nowrap">
                            Learning Assets
                        </h2>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 hover:bg-black/10 text-black"
                        onClick={onToggle}
                    >
                        <X className="h-5 w-5" />
                    </Button>
                </header>

                {/* Content */}
                <div className="flex flex-col flex-grow overflow-hidden bg-[#FFFDF5] dark:bg-[#000000]">

                    {/* Search Bar */}
                    <div className="p-4 border-b-[3px] border-black dark:border-white">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                            <Input
                                placeholder="Search topics..."
                                className="pl-9 border-[2px] border-black dark:border-white focus-visible:ring-0 focus-visible:shadow-[2px_2px_0_0_rgba(0,0,0,1)] transition-all font-medium"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                            />
                        </div>
                    </div>

                    {/* Assets List */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {filteredAssets.map((asset, index) => (
                            <div
                                key={asset.id || index}
                                className={cn(
                                    "group relative border-[3px] border-black dark:border-white bg-white dark:bg-zinc-900 cursor-pointer transition-all hover:translate-x-1 hover:translate-y-1 hover:shadow-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]",
                                    activeVideo === (asset.videoId || asset.path) ? "ring-4 ring-[#C4B5FD] border-transparent" : ""
                                )}
                                onClick={() => setActiveVideo(asset.videoId || asset.path || null)}
                            >
                                <div className="flex flex-col">
                                    <div className="relative w-full aspect-video bg-gray-200 shrink-0 overflow-hidden border-b-2 border-black dark:border-white group-hover:scale-[1.02] transition-transform origin-top z-10">
                                        {asset.thumbnail ? (
                                            <img
                                                src={asset.thumbnail}
                                                alt={asset.title}
                                                className="w-full h-full object-cover"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center bg-[#FFD93D]">
                                                <Play className="w-10 h-10 text-black fill-black" />
                                            </div>
                                        )}
                                        {asset.duration && (
                                            <span className="absolute bottom-1 right-1 bg-black/80 text-white text-[10px] px-1.5 py-0.5 font-bold">
                                                {asset.duration}
                                            </span>
                                        )}
                                    </div>
                                    <div className="min-w-0 flex-1 p-3">
                                        <h3 className="font-bold text-sm leading-tight text-black dark:text-white line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                                            {asset.title}
                                        </h3>
                                        {asset.category && (
                                            <div className="mt-2 text-[10px] font-black uppercase tracking-tight text-black/40 dark:text-white/40 line-clamp-1 border-2 border-black/10 dark:border-white/10 self-start px-2 py-0.5 inline-block">
                                                {asset.category}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}

                        {filteredAssets.length === 0 && (
                            <div className="text-center py-4 text-gray-500 font-medium text-xs">
                                {currentAsset ? "No matches found." : "No explicit database videos."}
                            </div>
                        )}

                        {/* Automatic YouTube Search Link */}
                        {searchQuery && (
                            <div className="mt-4">
                                <YouTubeSearchResults
                                    query={searchQuery}
                                    onSelect={(video) => {
                                        setSelectedExternalAsset(video);
                                        setActiveVideo(video.videoId);
                                    }}
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div >
        </>
    );
}

const API_BASE_URL = import.meta.env.VITE_DASH_API_URL || "http://localhost:8000";

function YouTubeSearchResults({ query, onSelect }: { query: string, onSelect: (video: any) => void }) {
    const [videos, setVideos] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (!query) return;

        const fetchVideos = async () => {
            setLoading(true);
            try {
                // Decode query for display/API usage
                const decodedQuery = decodeURIComponent(query);
                const url = `${API_BASE_URL}/api/learning-assets/search?query=${encodeURIComponent(decodedQuery)}`;
                console.log("[YT Search] Fetching:", url);

                const response = await fetch(url);
                console.log("[YT Search] Response status:", response.status);

                if (response.ok) {
                    const data = await response.json();
                    console.log("[YT Search] Data received:", data);
                    setVideos(data);
                } else {
                    const text = await response.text();
                    console.error("[YT Search] Fetch failed:", text);
                }
            } catch (error) {
                console.error("Failed to fetch YouTube videos:", error);
            } finally {
                setLoading(false);
            }
        };

        const timer = setTimeout(fetchVideos, 500); // Debounce
        return () => clearTimeout(timer);
    }, [query]);

    if (loading) {
        return <div className="text-center py-4 text-xs font-medium text-gray-400">Loading videos...</div>;
    }

    if (videos.length === 0) {
        return (
            <div className="text-center py-4 text-xs font-medium text-gray-400">
                No videos found.
                <a
                    href={`https://www.youtube.com/results?search_query=${query}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block mt-2 underline text-blue-500"
                >
                    Try searching directly
                </a>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {videos.slice(0, 10).map((video) => (
                <div
                    key={video.id}
                    onClick={() => onSelect(video)}
                    className="group relative border-[2px] border-black dark:border-white bg-white dark:bg-zinc-900 cursor-pointer transition-all hover:translate-x-1 hover:translate-y-1 hover:shadow-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]"
                >
                    <div className="flex flex-col">
                        <div className="relative w-full aspect-video bg-gray-200 shrink-0 overflow-hidden border-b-2 border-black dark:border-white group-hover:scale-[1.02] transition-transform origin-top z-10">
                            <img
                                src={video.thumbnail}
                                alt={video.title}
                                className="w-full h-full object-cover"
                            />
                            <div className="absolute inset-0 flex items-center justify-center bg-black/10 group-hover:bg-black/0 transition-colors">
                                <Play className="w-10 h-10 fill-white text-white drop-shadow-md opacity-80 group-hover:opacity-100" />
                            </div>
                            <span className="absolute bottom-1 right-1 bg-black/80 text-white text-[10px] px-1.5 py-0.5 font-bold">
                                {video.duration}
                            </span>
                        </div>

                        <div className="min-w-0 flex-1 p-3">
                            <h3 className="font-bold text-sm leading-tight text-black dark:text-white line-clamp-2 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                                {video.title}
                            </h3>
                            <div className="mt-2 text-[10px] font-black uppercase tracking-tight text-black/40 dark:text-white/40 line-clamp-1 border-2 border-black/10 dark:border-white/10 self-start px-2 py-0.5 inline-block">
                                {video.channel}
                            </div>
                        </div>
                    </div>
                </div>
            ))}
            <div className="flex flex-col gap-2 mt-2">
                <a
                    href={`https://www.youtube.com/results?search_query=${query}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-center text-[10px] font-bold uppercase tracking-widest text-gray-400 hover:text-black dark:hover:text-white transition-colors py-1"
                >
                    View More on YouTube &rarr;
                </a>
                <a
                    href="https://www.youtube.com/premium"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-center text-[11px] font-bold uppercase tracking-wide text-gray-500 hover:text-[#FF0000] hover:border-[#FF0000] transition-all py-2 border-2 border-dashed border-gray-300 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                    Remove Ads with YouTube Premium
                </a>
            </div>
        </div>
    );
}
