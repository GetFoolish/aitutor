// @ts-nocheck
import React, { useState, useEffect } from "react";
import { Excalidraw, MainMenu, WelcomeScreen } from "@excalidraw/excalidraw";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Loader2 } from "lucide-react";
import { useOptionalScratchpad } from "../../contexts/ScratchpadContext";

/**
 * A full-featured whiteboard using Excalidraw.
 * Now connected to ScratchpadContext so AI tutor can draw on it.
 */
const Scratchpad = () => {
  const [localExcalidrawAPI, setLocalExcalidrawAPI] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const scratchpadContext = useOptionalScratchpad();

  // Excalidraw loads asynchronously
  useEffect(() => {
    // Small timeout to prevent flicker if it loads instantly
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer); // Cleanup on unmount
  }, []);

  // Share the API with context when available
  useEffect(() => {
    if (localExcalidrawAPI && scratchpadContext?.setExcalidrawAPI) {
      scratchpadContext.setExcalidrawAPI(localExcalidrawAPI);
      console.log('🎨 Scratchpad API shared with context - AI teacher can now draw!');
    }
  }, [localExcalidrawAPI, scratchpadContext]);

  const handleClearAll = () => {
    if (localExcalidrawAPI) {
      localExcalidrawAPI.resetScene();
    }
  };

  return (
    <div className="relative h-full w-full overflow-hidden rounded-md border border-border bg-card/60 shadow-sm">
      {/* AI Teacher indicator when connected */}
      {scratchpadContext?.excalidrawAPI && (
        <div className="absolute left-4 top-4 z-50 flex items-center gap-2 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800 shadow-sm">
          <span className="h-2 w-2 animate-pulse rounded-full bg-green-500"></span>
          AI Teacher Ready
        </div>
      )}

      {/* Custom absolute toolbar for external actions */}
      <div className="absolute right-4 top-4 z-50 flex gap-2">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              type="button"
              size="sm"
              variant="destructive"
              className="h-8 text-xs shadow-md backdrop-blur-sm"
            >
              <span className="material-symbols-outlined mr-1 text-sm">delete_forever</span>
              Clear Board
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear entire whiteboard?</AlertDialogTitle>
              <AlertDialogDescription>
                This will delete all your drawings. This action cannot be undone easily via this button
                (though Excalidraw internal undo might still work).
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleClearAll} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                Clear All
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-40 backdrop-blur-sm">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}

      {/* Excalidraw Container */}
      <div className="h-full w-full" style={{ height: "100%", width: "100%" }}>
        {/* @ts-ignore - Excalidraw types mismatch with current version */}
        <Excalidraw
          onMount={(api: any) => {
            setLocalExcalidrawAPI(api);
            setIsLoading(false);
          }}
          theme="light"
          UIOptions={{
            canvasActions: {
              changeViewBackgroundColor: true,
              clearCanvas: false,
              loadScene: false,
              saveToActiveFile: false,
              toggleTheme: false,
              saveAsImage: true,
            },
          }}
        >
          <WelcomeScreen>
            <WelcomeScreen.Center>
              <WelcomeScreen.Center.Heading>
                AI Whiteboard
              </WelcomeScreen.Center.Heading>
              <WelcomeScreen.Center.Menu>
                <WelcomeScreen.Center.MenuItemHelp />
              </WelcomeScreen.Center.Menu>
            </WelcomeScreen.Center>
          </WelcomeScreen>
          <MainMenu>
            <MainMenu.DefaultItems.SaveAsImage />
            <MainMenu.DefaultItems.Export />
            <MainMenu.Separator />
            <MainMenu.DefaultItems.ClearCanvas />
            <MainMenu.Separator />
            <MainMenu.DefaultItems.Help />
          </MainMenu>
        </Excalidraw>
      </div>
    </div>
  );
};

export default Scratchpad;
