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

/**
 * A full-featured whiteboard using Excalidraw.
 * Replaces the limited 'react-sketch-canvas' implementation.
 */
const Scratchpad = () => {
  const [excalidrawAPI, setExcalidrawAPI] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Excalidraw loads asynchronously
  useEffect(() => {
    // Small timeout to prevent flicker if it loads instantly
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer); // Cleanup on unmount
  }, []);


  const handleClearAll = () => {
    if (excalidrawAPI) {
      excalidrawAPI.resetScene();
    }
  };

  return (
    <div className="relative h-full w-full overflow-hidden rounded-md border border-border bg-card/60 shadow-sm">
      {/* Custom absolute toolbar for external actions if needed, 
          but Excalidraw has its own internal UI which is superior */}
      <div className="absolute right-4 top-4 z-50 flex gap-2">
        {/* Clear All with Confirmation - We keep this external for easy access 
             although Excalidraw has a reset, this is safer/explicit */}
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
            setExcalidrawAPI(api);
            setIsLoading(false);
          }}
          theme="light"
          UIOptions={{
            canvasActions: {
              changeViewBackgroundColor: true,
              clearCanvas: false, // We use our own clear button or key shortcut
              loadScene: false,
              saveToActiveFile: false,
              toggleTheme: false, // Force light mode or controlled by app
              saveAsImage: true,
            },
          }}
        >
          <WelcomeScreen>
            <WelcomeScreen.Center>
              <WelcomeScreen.Center.Heading>
                Whiteboard
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
