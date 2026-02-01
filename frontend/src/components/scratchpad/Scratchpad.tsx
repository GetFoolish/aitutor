// @ts-nocheck
import React, { useState, useEffect, useRef } from "react";
import { Tldraw, Editor } from "tldraw";
import "tldraw/tldraw.css";
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
 * A full-featured whiteboard using tldraw.
 * Replaced Excalidraw due to stability issues.
 * 
 * Features:
 * - Full drawing tools (pencil, shapes, text, arrows)
 * - Undo/redo support
 * - Pan and zoom
 * - Clear all with confirmation
 */
const Scratchpad = () => {
  const [editor, setEditor] = useState<Editor | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // tldraw loads asynchronously
  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  const handleClearAll = () => {
    if (editor) {
      editor.selectAll();
      editor.deleteShapes(editor.getSelectedShapeIds());
    }
  };

  return (
    <div className="relative h-full w-full overflow-hidden rounded-md border border-border bg-card/60 shadow-sm">
      {/* Clear All with Confirmation */}
      <div className="absolute right-4 top-4 z-50 flex gap-2">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" size="sm" disabled={isLoading}>
              Clear All
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear scratchpad?</AlertDialogTitle>
              <AlertDialogDescription>
                This will remove everything you've drawn. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleClearAll}>
                Clear All
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/80">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      )}

      <div style={{ width: "100%", height: "100%", minHeight: "400px" }}>
        <Tldraw
          onMount={(editorInstance) => {
            setEditor(editorInstance);
          }}
        />
      </div>
    </div>
  );
};

export default Scratchpad;
