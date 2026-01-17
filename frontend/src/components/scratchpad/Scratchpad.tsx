import React, { useCallback, useState } from "react";
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
import { Trash2 } from "lucide-react";
import { useLiveKit } from "../../features/livekit";
import { useAIDrawing } from "../../hooks/useAIDrawing";

/**
 * A full-featured whiteboard using tldraw.
 * Modern, reliable canvas for math work and drawing.
 * AI tutor can draw on this canvas to explain concepts.
 */
const Scratchpad = () => {
  const [editor, setEditor] = useState<Editor | null>(null);
  const { room } = useLiveKit();

  // Hook for AI drawing commands
  const { clearAIDrawings } = useAIDrawing(editor, room);

  const handleMount = useCallback((editor: Editor) => {
    setEditor(editor);
  }, []);

  const handleClearAll = useCallback(() => {
    if (editor) {
      editor.selectAll();
      editor.deleteShapes(editor.getSelectedShapeIds());
    }
  }, [editor]);

  return (
    <div className="relative h-full w-full overflow-hidden rounded-md border border-border bg-white shadow-sm">
      {/* Clear Button */}
      <div className="absolute right-4 top-4 z-50">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              type="button"
              size="sm"
              variant="destructive"
              className="h-8 text-xs shadow-md flex items-center gap-1"
            >
              <Trash2 className="w-3 h-3" />
              Clear Board
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear entire whiteboard?</AlertDialogTitle>
              <AlertDialogDescription>
                This will delete all your drawings. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleClearAll}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                Clear All
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Tldraw Canvas */}
      <div className="h-full w-full" style={{ position: "absolute", inset: 0 }}>
        <Tldraw
          onMount={handleMount}
          hideUi={false}
          inferDarkMode={false}
        />
      </div>
    </div>
  );
};

export default Scratchpad;
