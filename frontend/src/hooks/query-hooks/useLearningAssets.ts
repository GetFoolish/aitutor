import { useQuery } from "@tanstack/react-query";
import { apiUtils } from "../../lib/api-utils";

const DASH_API_URL = import.meta.env.VITE_DASH_API_URL || 'http://localhost:8000';

export interface LearningAsset {
    id?: string;
    title: string;
    thumbnail?: string;
    videoId?: string;
    path?: string; // Kept for backward compat if needed, but videoId is primary now
    duration?: string;
    category?: string;
}

export function useLearningAssets() {
    return useQuery<LearningAsset[]>({
        queryKey: ["learning-assets"],
        queryFn: async () => {
            const res = await apiUtils.get(`${DASH_API_URL}/api/learning-assets`);
            if (!res.ok) {
                throw new Error(`Failed to fetch learning assets (${res.status})`);
            }
            const data = await res.json();

            // Normalize data (backend uses _id, frontend component expects id)
            return data.map((item: any) => ({
                ...item,
                id: item._id || item.id,
                category: item.category || "General"
            }));
        },
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}
