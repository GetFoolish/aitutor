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
}

export default function LearningAssetsPanel({ open, onToggle, currentAsset }: LearningAssetsPanelProps) {
    const [activeVideo, setActiveVideo] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState("");
    const [videoOpacity, setVideoOpacity] = useState(0.95);
    const [portalTarget, setPortalTarget] = useState<HTMLElement | null>(null);

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

    const renderVideoOverlay = () => {
        if (!activeVideo || !portalTarget) return null;

        const activeAsset = assets.find(a => (a.videoId === activeVideo) || (a.path === activeVideo));

        // Use custom youtube-nocookie embed for ad-free experience if videoId exists
        let embedUrl = "";
        if (activeAsset?.videoId) {
            embedUrl = `https://www.youtube-nocookie.com/embed/${activeAsset.videoId}?autoplay=1&rel=0`;
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
                                    "group relative border-[3px] border-black dark:border-white bg-white dark:bg-zinc-900 cursor-pointer transition-all hover:translate-x-1 hover:translate-y-1 hover:shadow-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] p-3",
                                    activeVideo === (asset.videoId || asset.path) ? "ring-4 ring-[#C4B5FD] border-transparent" : ""
                                )}
                                onClick={() => setActiveVideo(asset.videoId || asset.path || null)}
                            >
                                <div className="flex items-start gap-3">
                                    <div className="relative w-24 h-16 border-2 border-black dark:border-white bg-gray-200 shrink-0 overflow-hidden group-hover:scale-105 transition-transform">
                                        {asset.thumbnail ? (
                                            <img
                                                src={asset.thumbnail}
                                                alt={asset.title}
                                                className="w-full h-full object-cover"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center bg-[#FFD93D]">
                                                <Play className="w-6 h-6 text-black fill-black" />
                                            </div>
                                        )}
                                    </div>
                                    <div className="min-w-0 flex-1">
                                        <h3 className="font-bold text-sm leading-tight text-black dark:text-white line-clamp-2">
                                            {asset.title}
                                        </h3>
                                        {asset.duration && (
                                            <p className="text-[10px] font-bold text-gray-500 mt-1 uppercase tracking-wider line-clamp-1">
                                                {asset.duration}
                                            </p>
                                        )}
                                        {asset.category && (
                                            <div className="mt-2 text-[9px] font-black uppercase tracking-tight text-black/40 dark:text-white/40 line-clamp-1">
                                                {asset.category}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}

                        {filteredAssets.length === 0 && (
                            <div className="text-center py-8 text-gray-500 font-medium text-sm">
                                {currentAsset ? "No matches found." : "No related videos for this question."}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </>
    );
}
