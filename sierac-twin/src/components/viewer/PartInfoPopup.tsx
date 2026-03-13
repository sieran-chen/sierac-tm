import type { PartMapping, TelemetryValue } from "@/types/equipment";

interface PartInfoPopupProps {
  selectedPart: { name: string; pos: { x: number; y: number } };
  mapping: PartMapping;
  telemetry: TelemetryValue[];
  onClose: () => void;
}

export default function PartInfoPopup({
  selectedPart,
  mapping,
  telemetry,
  onClose,
}: PartInfoPopupProps) {
  const points = telemetry.filter((t) => mapping.pointIds.includes(t.point_id));

  return (
    <div
      className="absolute z-10 w-64 rounded-lg border border-gray-600 bg-gray-800/95 p-3 text-sm text-white shadow-xl"
      style={{
        left: selectedPart.pos.x + 12,
        top: selectedPart.pos.y - 20,
      }}
    >
      <div className="mb-2 flex items-center justify-between">
        <span className="font-medium">{mapping.label}</span>
        <button
          type="button"
          className="text-gray-400 hover:text-white"
          onClick={onClose}
          aria-label="关闭"
        >
          ✕
        </button>
      </div>
      <div className="space-y-1 text-xs">
        {points.length > 0 ? (
          points.map((t) => (
            <div
              key={t.point_id}
              className="flex justify-between gap-2"
            >
              <span className="text-gray-400">{t.name}</span>
              <span className="tabular-nums text-gray-200">
                {typeof t.value === "number"
                  ? t.value.toFixed(2)
                  : String(t.value)}
                {t.unit ? ` ${t.unit}` : ""}
              </span>
            </div>
          ))
        ) : (
          <span className="text-gray-500">
            关联测点：{mapping.pointIds.join(", ")}
          </span>
        )}
      </div>
    </div>
  );
}
