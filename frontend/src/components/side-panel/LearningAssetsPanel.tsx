import { useState } from "react";
import cn from "classnames";
import { BookOpen, Play, X, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Mock data for learning assets
// In a real app, this would come from an API based on the student's current subject/level
const INITIAL_ASSETS = [
    {
        id: "1",
        title: "Introduction to Algebra",
        thumbnail: "https://img.youtube.com/vi/NybHckSEQBI/mqdefault.jpg",
        videoId: "NybHckSEQBI",
        duration: "12:30",
        category: "Math"
    },
    {
        id: "2",
        title: "The Cell Cycle (Mitosis)",
        thumbnail: "https://img.youtube.com/vi/Q6ucKWIIFmg/mqdefault.jpg",
        videoId: "Q6ucKWIIFmg",
        duration: "8:45",
        category: "Biology"
    },
    {
        id: "3",
        title: "Newton's Laws of Motion",
        thumbnail: "https://img.youtube.com/vi/kKKM8Y-u7ds/mqdefault.jpg",
        videoId: "kKKM8Y-u7ds",
        duration: "15:20",
        category: "Physics"
    },
    {
        id: "4",
        title: "Photosynthesis Explained",
        thumbnail: "https://img.youtube.com/vi/sQK3Yr4Sc_k/mqdefault.jpg",
        videoId: "sQK3Yr4Sc_k",
        duration: "6:10",
        category: "Biology"
    },
    {
        id: "5",
        title: "Pythagorean Theorem",
        thumbnail: "https://img.youtube.com/vi/AA6RfgP-AHU/mqdefault.jpg",
        videoId: "AA6RfgP-AHU",
        duration: "9:15",
        category: "Math"
    }
];

interface LearningAssetsPanelProps {
    open: boolean;
    onToggle: () => void;
}

export default function LearningAssetsPanel({ open, onToggle }: LearningAssetsPanelProps) {
    const [activeVideo, setActiveVideo] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState("");

    const filteredAssets = INITIAL_ASSETS.filter(asset =>
        asset.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.category.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return (
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

                {/* Video Player Modal/Overlay */}
                {activeVideo && (
                    <div className="shrink-0 w-full aspect-video bg-black border-b-[3px] border-black dark:border-white relative group">
                        <iframe
                            width="100%"
                            height="100%"
                            src={`https://www.youtube-nocookie.com/embed/${activeVideo}?autoplay=1&rel=0&modestbranding=1`}
                            title="YouTube video player"
                            frameBorder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                            allowFullScreen
                        ></iframe>
                        <Button
                            variant="destructive"
                            size="sm"
                            className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity border-2 border-white"
                            onClick={() => setActiveVideo(null)}
                        >
                            Close
                        </Button>
                    </div>
                )}

                {/* Assets List */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                    {filteredAssets.map((asset) => (
                        <div
                            key={asset.id}
                            className={cn(
                                "group relative border-[3px] border-black dark:border-white bg-white dark:bg-zinc-900 cursor-pointer transition-all hover:translate-x-1 hover:translate-y-1 hover:shadow-none shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]",
                                activeVideo === asset.videoId ? "ring-4 ring-[#C4B5FD] border-transparent" : ""
                            )}
                            onClick={() => setActiveVideo(asset.videoId)}
                        >
                            {/* Thumbnail */}
                            <div className="aspect-video relative overflow-hidden bg-gray-100 border-b-[3px] border-black dark:border-white">
                                <img
                                    src={asset.thumbnail}
                                    alt={asset.title}
                                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                                />
                                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors flex items-center justify-center">
                                    <div className="bg-white/90 text-black p-2 rounded-full opacity-0 group-hover:opacity-100 transition-opacity scale-75 group-hover:scale-100 duration-200 border-2 border-black">
                                        <Play className="w-4 h-4 fill-black" />
                                    </div>
                                </div>
                                <span className="absolute bottom-1 right-1 bg-black text-white text-[10px] font-bold px-1.5 py-0.5 rounded border border-white">
                                    {asset.duration}
                                </span>
                            </div>

                            {/* Info */}
                            <div className="p-3">
                                <div className="flex items-start justify-between gap-2">
                                    <h3 className="font-bold text-sm leading-tight text-black dark:text-white line-clamp-2">
                                        {asset.title}
                                    </h3>
                                </div>
                                <div className="mt-2 flex items-center justify-between">
                                    <span className="text-[10px] uppercase font-black tracking-wider text-gray-500 bg-gray-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full">
                                        {asset.category}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}

                    {filteredAssets.length === 0 && (
                        <div className="text-center py-8 text-gray-500 font-medium text-sm">
                            No videos found.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
