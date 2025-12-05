import { useCallback, useState } from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useLiveAPIContext } from "../../contexts/LiveAPIContext";
import { Modality } from "@google/genai";

const responseOptions = [
  { value: "audio", label: "audio" },
  { value: "text", label: "text" },
];

export default function ResponseModalitySelector() {
  const { config, setConfig } = useLiveAPIContext();

  const [value, setValue] = useState<"audio" | "text">("audio");

  const updateConfig = useCallback(
    (modality: "audio" | "text") => {
      setConfig({
        ...config,
        responseModalities: [
          modality === "audio" ? Modality.AUDIO : Modality.TEXT,
        ],
      });
    },
    [config, setConfig]
  );

  return (
    <div className="select-group space-y-1">
      <Label htmlFor="response-modality-selector">Response modality</Label>
      <Select
        value={value}
        onValueChange={(nextValue) => {
          if (nextValue === "audio" || nextValue === "text") {
            setValue(nextValue);
            updateConfig(nextValue);
          }
        }}
      >
        <SelectTrigger id="response-modality-selector">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {responseOptions.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
