import { ChangeEvent, useCallback, useEffect, useMemo, useState } from "react";
import "./settings-dialog.scss";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import VoiceSelector from "./VoiceSelector";
import ResponseModalitySelector from "./ResponseModalitySelector";
import {
  FunctionDeclaration,
  LiveConnectConfig,
  Modality,
  Tool,
} from "@google/genai";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

type FunctionDeclarationsTool = Tool & {
  functionDeclarations: FunctionDeclaration[];
};

export default function SettingsDialog({
  trigger,
  className,
}: {
  trigger?: React.ReactNode;
  className?: string;
}) {
  const { config, setConfig, connected } = useLiveAPIContext();
  const [userPrompt, setUserPrompt] = useState("");

  const functionDeclarations: FunctionDeclaration[] = useMemo(() => {
    if (!Array.isArray(config.tools)) {
      return [];
    }
    return (config.tools as Tool[])
      .filter((t: Tool): t is FunctionDeclarationsTool =>
        Array.isArray((t as any).functionDeclarations),
      )
      .map((t) => t.functionDeclarations)
      .filter((fc) => !!fc)
      .flat();
  }, [config]);

  useEffect(() => {
    // Set initial config with audio requirements for gemini-2.5-flash-native-audio-preview
    // System prompt is now loaded by the backend
    setConfig({
      ...config,
      responseModalities: [Modality.AUDIO],
      speechConfig: {
        voiceConfig: {
          prebuiltVoiceConfig: {
            voiceName: "Puck",
          },
        },
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUserPromptChange = useCallback(
    (event: ChangeEvent<HTMLTextAreaElement>) => {
      const newUserPrompt = event.target.value;
      setUserPrompt(newUserPrompt);
      // Backend handles base prompt, we just send additional instructions
      const newConfig: LiveConnectConfig = {
        ...config,
        systemInstruction: newUserPrompt.trim(),
      };
      setConfig(newConfig);
    },
    [config, setConfig],
  );

  const updateFunctionDescription = useCallback(
    (editedFdName: string, newDescription: string) => {
      const newConfig: LiveConnectConfig = {
        ...config,
        tools:
          config.tools?.map((tool) => {
            const fdTool = tool as FunctionDeclarationsTool;
            if (!Array.isArray(fdTool.functionDeclarations)) {
              return tool;
            }
            return {
              ...tool,
              functionDeclarations: fdTool.functionDeclarations.map((fd) =>
                fd.name === editedFdName
                  ? { ...fd, description: newDescription }
                  : fd,
              ),
            };
          }) || [],
      };
      setConfig(newConfig);
    },
    [config, setConfig],
  );

  return (
    <div className={`settings-dialog z-1002 ${className || ""}`}>
      <Dialog>
        <DialogTrigger asChild>
          {trigger || (
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="action-button material-symbols-outlined"
            >
              settings
            </Button>
          )}
        </DialogTrigger>
        <DialogContent className="dialog">
          <DialogHeader>
            <DialogTitle>Settings</DialogTitle>
            <DialogDescription>
              Configure response modality, voice, and system instructions before
              connecting.
            </DialogDescription>
          </DialogHeader>
          <div className={`dialog-container ${connected ? "disabled" : ""}`}>
            {connected && (
              <div className="connected-indicator">
                <p>
                  These settings can only be applied before connecting and will
                  override other settings.
                </p>
              </div>
            )}
            <div className="mode-selectors">
              <ResponseModalitySelector />
              <VoiceSelector />
            </div>

            <div className="space-y-2">
              <Label htmlFor="system-instructions">System Instructions</Label>
              <Textarea
                id="system-instructions"
                className="system"
                onChange={handleUserPromptChange}
                value={userPrompt}
                placeholder="Add additional instructions for the model..."
              />
            </div>

            <h4>Function declarations</h4>
            <div className="function-declarations">
              <div className="fd-rows">
                {functionDeclarations.map((fd, fdKey) => (
                  <div className="fd-row" key={`function-${fdKey}`}>
                    <span className="fd-row-name">{fd.name}</span>
                    <span className="fd-row-args">
                      {Object.keys(fd.parameters?.properties || {}).map(
                        (item, k) => (
                          <span key={k}>{item}</span>
                        ),
                      )}
                    </span>
                    <input
                      key={`fd-${fd.description}`}
                      className="fd-row-description"
                      type="text"
                      defaultValue={fd.description}
                      onBlur={(e) =>
                        updateFunctionDescription(fd.name!, e.target.value)
                      }
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
