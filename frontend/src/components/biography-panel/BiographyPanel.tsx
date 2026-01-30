import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Book, RefreshCw, X, User, ChevronDown, ChevronUp } from "lucide-react";
import { jwtUtils } from "../../lib/jwt-utils";
import cn from "classnames";

const TEACHING_ASSISTANT_API_URL = import.meta.env.VITE_TEACHING_ASSISTANT_API_URL || 'http://localhost:8002';

interface BiographyData {
  biography: string;
  biography_version: number;
  academic_journey?: {
    current_topic?: string;
    mastered_topics?: string[];
    struggling_topics?: string[];
    milestones?: string[];
  };
  statistics?: {
    total_sessions?: number;
    total_questions_answered?: number;
    total_questions_correct?: number;
    average_session_duration_minutes?: number;
    last_session_date?: string;
  };
}

interface BiographyPanelProps {
  isOpen: boolean;
  onClose: () => void;
  position?: "left" | "right";
}

export function BiographyPanel({ isOpen, onClose, position = "right" }: BiographyPanelProps) {
  const [biography, setBiography] = useState<BiographyData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState({
    biography: true,
    journey: false,
    stats: false,
  });

  const fetchBiography = useCallback(async () => {
    const token = jwtUtils.getToken();
    if (!token) {
      setError("Not authenticated");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${TEACHING_ASSISTANT_API_URL}/student/biography`, {
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch biography: ${response.status}`);
      }

      const data = await response.json();

      // Handle nested biography structure
      if (data.biography && typeof data.biography === 'object') {
        setBiography({
          biography: data.biography.biography || "",
          biography_version: data.biography.biography_version || 0,
          academic_journey: data.biography.academic_journey || {},
          statistics: data.biography.statistics || {},
        });
      } else {
        setBiography({
          biography: data.biography || "",
          biography_version: data.biography_version || 0,
          academic_journey: data.academic_journey || {},
          statistics: data.statistics || {},
        });
      }
    } catch (err: any) {
      console.error("[BiographyPanel] Error:", err);
      setError(err.message || "Failed to load biography");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchBiography();
    }
  }, [isOpen, fetchBiography]);

  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "Never";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, x: position === "right" ? 100 : -100 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: position === "right" ? 100 : -100 }}
          transition={{ type: "spring", damping: 25, stiffness: 300 }}
          className={cn(
            "fixed top-20 z-[999] w-[380px] max-h-[calc(100vh-120px)] bg-[#FFFDF5] dark:bg-[#1a1a1a] border-[3px] border-black dark:border-white rounded-xl shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)] overflow-hidden flex flex-col",
            position === "right" ? "right-4" : "left-4"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-3 border-b-[3px] border-black dark:border-white bg-[#C4B5FD]">
            <div className="flex items-center gap-2">
              <div className="p-1.5 border-[2px] border-black dark:border-white bg-white dark:bg-black">
                <Book className="w-4 h-4 text-black dark:text-white" />
              </div>
              <h3 className="font-black text-black uppercase text-sm tracking-wide">
                Living Biography
              </h3>
              {biography?.biography_version && (
                <span className="px-2 py-0.5 text-[9px] font-black uppercase bg-white dark:bg-black text-black dark:text-white border-[2px] border-black dark:border-white">
                  v{biography.biography_version}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={fetchBiography}
                disabled={loading}
                className="w-8 h-8 flex items-center justify-center border-[2px] border-black dark:border-white bg-white dark:bg-black hover:bg-[#FFD93D] text-black dark:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 disabled:opacity-50"
              >
                <RefreshCw className={cn("w-3.5 h-3.5", loading && "animate-spin")} />
              </button>
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center border-[2px] border-black dark:border-white bg-white dark:bg-black hover:bg-[#FF6B6B] text-black dark:text-white hover:text-white transition-all shadow-[1px_1px_0_0_rgba(0,0,0,1)] hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {loading && !biography && (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="w-6 h-6 animate-spin text-black dark:text-white" />
              </div>
            )}

            {error && (
              <div className="p-3 bg-[#FF6B6B] border-[2px] border-black text-white text-sm font-bold">
                {error}
              </div>
            )}

            {biography && (
              <>
                {/* Biography Section */}
                <div className="border-[2px] border-black dark:border-white">
                  <button
                    onClick={() => toggleSection("biography")}
                    className="w-full flex items-center justify-between p-2 bg-[#4ADE80] hover:bg-[#3ECF6E] transition-colors"
                  >
                    <div className="flex items-center gap-2">
                      <User className="w-4 h-4 text-black" />
                      <span className="font-black text-black uppercase text-xs">Student Profile</span>
                    </div>
                    {expandedSections.biography ? (
                      <ChevronUp className="w-4 h-4 text-black" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-black" />
                    )}
                  </button>
                  <AnimatePresence>
                    {expandedSections.biography && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="p-3 bg-white dark:bg-black text-black dark:text-white text-sm leading-relaxed whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                          {biography.biography || "No biography generated yet. Start a conversation to build the Living Biography!"}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Academic Journey Section */}
                <div className="border-[2px] border-black dark:border-white">
                  <button
                    onClick={() => toggleSection("journey")}
                    className="w-full flex items-center justify-between p-2 bg-[#FFD93D] hover:bg-[#F0CA2D] transition-colors"
                  >
                    <span className="font-black text-black uppercase text-xs">Academic Journey</span>
                    {expandedSections.journey ? (
                      <ChevronUp className="w-4 h-4 text-black" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-black" />
                    )}
                  </button>
                  <AnimatePresence>
                    {expandedSections.journey && biography.academic_journey && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="p-3 bg-white dark:bg-black space-y-2">
                          {biography.academic_journey.current_topic && (
                            <div>
                              <span className="text-xs font-black text-black dark:text-white uppercase">Current Topic:</span>
                              <p className="text-sm text-black dark:text-white">{biography.academic_journey.current_topic}</p>
                            </div>
                          )}
                          {biography.academic_journey.mastered_topics && biography.academic_journey.mastered_topics.length > 0 && (
                            <div>
                              <span className="text-xs font-black text-black dark:text-white uppercase">Mastered:</span>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {biography.academic_journey.mastered_topics.map((topic, i) => (
                                  <span key={i} className="px-2 py-0.5 text-xs bg-[#4ADE80] text-black border border-black">
                                    {topic}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {(!biography.academic_journey.current_topic &&
                            (!biography.academic_journey.mastered_topics || biography.academic_journey.mastered_topics.length === 0)) && (
                            <p className="text-sm text-gray-500 dark:text-gray-400 italic">No academic journey data yet</p>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Statistics Section */}
                <div className="border-[2px] border-black dark:border-white">
                  <button
                    onClick={() => toggleSection("stats")}
                    className="w-full flex items-center justify-between p-2 bg-[#C4B5FD] hover:bg-[#B4A5ED] transition-colors"
                  >
                    <span className="font-black text-black uppercase text-xs">Session Stats</span>
                    {expandedSections.stats ? (
                      <ChevronUp className="w-4 h-4 text-black" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-black" />
                    )}
                  </button>
                  <AnimatePresence>
                    {expandedSections.stats && biography.statistics && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="p-3 bg-white dark:bg-black grid grid-cols-2 gap-2">
                          <div className="p-2 border border-black dark:border-white text-center">
                            <div className="text-2xl font-black text-black dark:text-white">
                              {biography.statistics.total_sessions || 0}
                            </div>
                            <div className="text-[9px] font-bold text-gray-600 dark:text-gray-400 uppercase">Sessions</div>
                          </div>
                          <div className="p-2 border border-black dark:border-white text-center">
                            <div className="text-2xl font-black text-black dark:text-white">
                              {biography.statistics.total_questions_correct || 0}/{biography.statistics.total_questions_answered || 0}
                            </div>
                            <div className="text-[9px] font-bold text-gray-600 dark:text-gray-400 uppercase">Questions</div>
                          </div>
                          <div className="col-span-2 p-2 border border-black dark:border-white">
                            <div className="text-xs text-gray-600 dark:text-gray-400">
                              <span className="font-bold">Last Session:</span> {formatDate(biography.statistics.last_session_date)}
                            </div>
                            {biography.statistics.average_session_duration_minutes && (
                              <div className="text-xs text-gray-600 dark:text-gray-400">
                                <span className="font-bold">Avg Duration:</span> {biography.statistics.average_session_duration_minutes.toFixed(1)} min
                              </div>
                            )}
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="p-2 border-t-[2px] border-black dark:border-white bg-[#f5f5f0] dark:bg-[#111]">
            <p className="text-[9px] text-gray-500 dark:text-gray-400 text-center font-bold uppercase">
              Biography updates automatically as you learn
            </p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default BiographyPanel;
