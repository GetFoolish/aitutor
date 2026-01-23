/**
 * 404 Not Found Page
 * Displays when user navigates to a non-existent route
 */
import React from 'react';
import { useHistory } from 'react-router-dom';
import { Button } from '../ui/button';
import cn from 'classnames';
import { Home, ArrowLeft } from 'lucide-react';

const NotFoundPage: React.FC = () => {
  const history = useHistory();

  const handleGoHome = () => {
    history.push('/');
  };

  const handleGoBack = () => {
    history.goBack();
  };

  return (
    <div className="min-h-screen bg-[#FFFDF5] dark:bg-[#000000] flex items-center justify-center p-4 page-transition">
      <div className="max-w-2xl w-full">
        {/* 404 Card */}
        <div className={cn(
          "border-[4px] border-black dark:border-white bg-[#FFFDF5] dark:bg-[#000000]",
          "shadow-[8px_8px_0_0_rgba(0,0,0,1)] dark:shadow-[8px_8px_0_0_rgba(255,255,255,0.3)]",
          "p-8 md:p-12 text-center"
        )}>
          {/* 404 Number */}
          <div className={cn(
            "text-[120px] md:text-[180px] font-black leading-none mb-4",
            "text-black dark:text-white",
            "relative inline-block"
          )}>
            404
            {/* Neo-brutalist decoration boxes */}
            <div className="absolute -top-4 -right-4 w-16 h-16 bg-[#FFD93D] border-[3px] border-black dark:border-white -z-10" />
            <div className="absolute -bottom-4 -left-4 w-20 h-20 bg-[#FF6B6B] border-[3px] border-black dark:border-white -z-10" />
          </div>

          {/* Title */}
          <h1 className={cn(
            "text-3xl md:text-4xl font-black mb-4 text-black dark:text-white uppercase tracking-wide"
          )}>
            Page Not Found
          </h1>

          {/* Description */}
          <p className={cn(
            "text-base md:text-lg font-bold text-black dark:text-white mb-8 max-w-md mx-auto"
          )}>
            Oops! The page you're looking for doesn't exist. It might have been moved or deleted.
          </p>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Button
              onClick={handleGoHome}
              className={cn(
                "w-full sm:w-auto px-6 py-3 font-black text-black transition-all transform",
                "border-[3px] border-black shadow-[4px_4px_0_0_rgba(0,0,0,1)]",
                "active:translate-x-1 active:translate-y-1 active:shadow-none",
                "bg-[#FFD93D] hover:bg-[#FFD93D] uppercase text-base"
              )}
            >
              <Home className="w-5 h-5 mr-2" />
              Go Home
            </Button>

            <Button
              onClick={handleGoBack}
              className={cn(
                "w-full sm:w-auto px-6 py-3 font-black text-black dark:text-white transition-all transform",
                "border-[3px] border-black dark:border-white shadow-[4px_4px_0_0_rgba(0,0,0,1)] dark:shadow-[4px_4px_0_0_rgba(255,255,255,0.3)]",
                "active:translate-x-1 active:translate-y-1 active:shadow-none",
                "bg-[#FFFDF5] dark:bg-[#000000] hover:bg-[#FFFDF5] dark:hover:bg-[#000000] uppercase text-base"
              )}
            >
              <ArrowLeft className="w-5 h-5 mr-2" />
              Go Back
            </Button>
          </div>

          {/* Decorative Elements */}
          <div className="mt-12 flex justify-center gap-4">
            <div className="w-12 h-12 bg-[#C4B5FD] border-[2px] border-black dark:border-white transform rotate-12" />
            <div className="w-12 h-12 bg-[#FF6B6B] border-[2px] border-black dark:border-white transform -rotate-12" />
            <div className="w-12 h-12 bg-[#FFD93D] border-[2px] border-black dark:border-white transform rotate-45" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
