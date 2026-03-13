import { useContext } from "react";
import { Compass } from "lucide-react";
import { PresetContext } from "./PresetCameraContext";

export type PresetId = "front" | "back" | "left" | "right" | "top";

const PRESETS: { id: PresetId; label: string }[] = [
  { id: "front", label: "正面" },
  { id: "back", label: "背面" },
  { id: "left", label: "左侧" },
  { id: "right", label: "右侧" },
  { id: "top", label: "俯视" },
];

interface PresetViewsProps {
  disabled?: boolean;
}

export default function PresetViews({ disabled }: PresetViewsProps) {
  const context = useContext(PresetContext);
  const setPreset = context?.setPreset;

  return (
    <div className="absolute bottom-4 right-4 z-10 flex flex-col gap-1 rounded-lg bg-gray-900/80 px-2 py-1.5 backdrop-blur-sm">
      <span className="flex items-center gap-1 px-1 text-[10px] text-gray-500">
        <Compass className="h-2.5 w-2.5" />
        视角
      </span>
      <div className="flex gap-0.5">
        {PRESETS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => !disabled && setPreset?.(id)}
            disabled={disabled}
            className="rounded px-1.5 py-0.5 text-[10px] text-gray-400 hover:bg-gray-700 hover:text-gray-200 disabled:opacity-50"
            title={label}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}
