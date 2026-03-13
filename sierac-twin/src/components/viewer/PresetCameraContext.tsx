import { createContext, useState, type ReactNode } from "react";
import type { PresetId } from "./PresetViews";

export interface PresetContextValue {
  preset: PresetId | null;
  setPreset: (p: PresetId | null) => void;
}

export const PresetContext = createContext<PresetContextValue | null>(null);

export function PresetCameraProvider({ children }: { children: ReactNode }) {
  const [preset, setPreset] = useState<PresetId | null>(null);
  return (
    <PresetContext.Provider value={{ preset, setPreset }}>
      {children}
    </PresetContext.Provider>
  );
}
