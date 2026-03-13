import { Suspense, useState, useCallback, useRef, useEffect } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Preload, Html } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import ImageSphere from "./ImageSphere";
import ModelViewer from "./ModelViewer";
import ModelPlaceholder from "./ModelPlaceholder";
import ViewAngleIndicator from "./ViewAngleIndicator";
import ViewerErrorBoundary from "./ViewerErrorBoundary";
import PresetViews from "./PresetViews";
import PresetCameraController from "./PresetCameraController";
import PartInfoPopup from "./PartInfoPopup";
import { PresetCameraProvider } from "./PresetCameraContext";
import { useViewAngle } from "@/hooks/useViewAngle";
import { PART_MAPPING } from "@/config/partMapping";
import { MODEL_CONFIG } from "@/config/modelConfig";
import { sceneToWorld } from "@/config/coordinateSystem";
import type {
  Alarm,
  CalibrationPoint,
  TelemetryValue,
  ViewerPathConfig,
} from "@/types/equipment";
import { fetchViewerPathConfig, saveViewerPathConfig } from "@/services/api";
import EquipmentAxes from "./EquipmentAxes";

const USE_MODEL = import.meta.env.VITE_USE_MODEL !== "false";
type CalibrationTarget = "start" | "waypoint" | "end";

const MODEL_EULER = new THREE.Euler(...MODEL_CONFIG.rotation);
const MODEL_POSITION = new THREE.Vector3(...MODEL_CONFIG.position);
const MODEL_QUATERNION = new THREE.Quaternion().setFromEuler(MODEL_EULER);

function sceneCoordToWorldPoint(front: number, up: number, right: number, alignWithModel: boolean) {
  const [x, y, z] = sceneToWorld(front, up, right);
  const world = new THREE.Vector3(x, y, z);
  if (alignWithModel) {
    world.applyQuaternion(MODEL_QUATERNION);
  }
  world.add(MODEL_POSITION);

  return {
    x: world.x,
    z: world.z,
    front,
    up,
    right,
  };
}

function formatCoord(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function createDefaultPathPoints(): ViewerPathConfig {
  return {
    start: sceneCoordToWorldPoint(-8, 0, 8.5, false),
    waypoint: null,
    end: sceneCoordToWorldPoint(0, 0, -8.5, true),
  };
}

function ViewerLoadingFallback() {
  return (
    <>
      <mesh>
        <planeGeometry args={[10, 10]} />
        <meshBasicMaterial color="#374151" />
      </mesh>
      <Html center style={{ color: "#9ca3af", fontSize: 14, pointerEvents: "none" }}>
        正在加载 3D 模型，请稍候…
      </Html>
    </>
  );
}

interface EquipmentViewerProps {
  equipmentId: string;
  alarms?: Alarm[];
  telemetry?: TelemetryValue[];
}

const ZOOM_STEP = 1.2;

export default function EquipmentViewer({
  equipmentId,
  alarms = [],
  telemetry = [],
}: EquipmentViewerProps) {
  const { angle, handleCameraChange } = useViewAngle();
  const orbitRef = useRef<OrbitControlsImpl>(null);
  const [modelLoadFailed, setModelLoadFailed] = useState(false);
  const [hoveredPart, setHoveredPart] = useState<string | null>(null);
  const [selectedPart, setSelectedPart] = useState<{
    name: string;
    pos: { x: number; y: number };
  } | null>(null);
  const [calibrationTarget, setCalibrationTarget] = useState<CalibrationTarget>("end");
  const [pickedPoint, setPickedPoint] = useState<CalibrationPoint | null>(null);
  const [pathPoints, setPathPoints] = useState<ViewerPathConfig>(() => createDefaultPathPoints());
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [loadError, setLoadError] = useState<string | null>(null);

  const handlePartHover = useCallback((name: string | null) => {
    setHoveredPart(name);
  }, []);

  const handlePartClick = useCallback(
    (name: string, screenPos: { x: number; y: number }) => {
      setSelectedPart((prev) =>
        prev?.name === name ? null : { name, pos: screenPos }
      );
    },
    []
  );

  const showImageSphere = !USE_MODEL || modelLoadFailed;
  const partLabel = hoveredPart
    ? PART_MAPPING.find((p) => p.partName === hoveredPart)?.label
    : null;
  const selectedMapping = selectedPart
    ? PART_MAPPING.find((p) => p.partName === selectedPart.name)
    : null;

  useEffect(() => {
    let cancelled = false;

    async function loadConfig() {
      try {
        const config = await fetchViewerPathConfig(equipmentId);
        if (!cancelled) {
          setPathPoints(config);
          setLoadError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setPathPoints(createDefaultPathPoints());
          setLoadError(error instanceof Error ? error.message : "加载轨迹配置失败");
        }
      }
    }

    void loadConfig();
    return () => {
      cancelled = true;
    };
  }, [equipmentId]);

  const handleSavePathConfig = useCallback(async () => {
    try {
      setSaveState("saving");
      const saved = await saveViewerPathConfig(equipmentId, pathPoints);
      setPathPoints(saved);
      setSaveState("saved");
      setLoadError(null);
    } catch (error) {
      setSaveState("error");
      setLoadError(error instanceof Error ? error.message : "保存轨迹配置失败");
    }
  }, [equipmentId, pathPoints]);

  const handleResetDefaults = useCallback(() => {
    setPickedPoint(null);
    setPathPoints(createDefaultPathPoints());
    setSaveState("idle");
  }, []);

  return (
    <PresetCameraProvider>
      <div className="relative h-full w-full">
        <Canvas
          camera={{ position: [8, 12, 18], fov: 55 }}
          style={{
            background:
              "linear-gradient(180deg, #1a1a2e 0%, #16213e 100%)",
          }}
        >
          <ambientLight intensity={1.8} />
          <directionalLight position={[10, 15, 10]} intensity={2.5} castShadow />
          <directionalLight position={[-8, 10, -8]} intensity={1.2} />
          <directionalLight position={[0, -5, 8]} intensity={0.8} />
          <group position={MODEL_CONFIG.position} rotation={MODEL_CONFIG.rotation}>
            <EquipmentAxes />
          </group>
          <Suspense fallback={<ViewerLoadingFallback />}>
            <ViewerErrorBoundary
              onError={() => setModelLoadFailed(true)}
              fallback={<ModelPlaceholder />}
            >
              {USE_MODEL && !modelLoadFailed ? (
                <ModelViewer
                  partMapping={PART_MAPPING}
                  alarms={alarms}
                  telemetry={telemetry}
                  pathPoints={pathPoints}
                  calibrationTarget={calibrationTarget}
                  pendingCalibrationPoint={pickedPoint}
                  onCalibrationPick={setPickedPoint}
                  onPartHover={handlePartHover}
                  onPartClick={handlePartClick}
                />
              ) : (
                <ImageSphere onAngleChange={handleCameraChange} />
              )}
            </ViewerErrorBoundary>
          </Suspense>
          {USE_MODEL && !modelLoadFailed && <PresetCameraController />}
          <OrbitControls
              ref={orbitRef}
              target={[0, 2, 0]}
              enablePan={USE_MODEL && !modelLoadFailed}
              minPolarAngle={Math.PI / 6}
              maxPolarAngle={(5 * Math.PI) / 6}
              minDistance={5}
              maxDistance={80}
              rotateSpeed={0.5}
            />
          <Preload all />
        </Canvas>

        {showImageSphere && <ViewAngleIndicator angle={angle} />}

        {USE_MODEL && modelLoadFailed && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="rounded-lg bg-black/70 px-4 py-3 text-center text-sm text-gray-300">
              <p>3D 模型未加载</p>
              <p className="mt-1 text-xs text-gray-500">
                请将 001.glb 放入 sierac-twin/public/models/ 以显示设备模型
              </p>
            </div>
          </div>
        )}

        {USE_MODEL && !modelLoadFailed && (
          <>
            <div className="pointer-events-none absolute left-4 bottom-16 z-10 rounded-lg bg-gray-900/80 px-3 py-2 text-[11px] text-gray-200 backdrop-blur-sm">
              <div className="font-semibold text-gray-100">场景坐标系</div>
              <div>红: +前 FRONT</div>
              <div>蓝: +右 RIGHT</div>
              <div>绿: +上 UP</div>
            </div>
            <div className="absolute right-4 bottom-4 z-10 w-72 rounded-lg bg-gray-900/85 px-3 py-3 text-[11px] text-gray-200 backdrop-blur-sm">
              <div className="font-semibold text-gray-100">点击校准</div>
              <div className="mt-1 text-gray-400">先选目标，再在黄色平面点一下，然后点应用。</div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => void handleSavePathConfig()}
                  disabled={saveState === "saving"}
                  className="rounded bg-emerald-500 px-2 py-1 text-xs font-medium text-gray-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-gray-700 disabled:text-gray-500"
                >
                  {saveState === "saving" ? "保存中..." : "保存到项目配置"}
                </button>
                <button
                  type="button"
                  onClick={handleResetDefaults}
                  className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700"
                >
                  恢复默认
                </button>
              </div>
              <div className="mt-1 text-[10px] text-gray-400">
                {saveState === "saved"
                  ? "已保存到项目配置，刷新页面仍会保留。"
                  : saveState === "error"
                    ? "保存失败，请看下方错误信息。"
                    : "修改后记得点保存，才会写入项目配置。"}
              </div>
              {loadError && <div className="mt-1 text-[10px] text-amber-400">{loadError}</div>}
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => setCalibrationTarget("start")}
                  className={`rounded px-2 py-1 text-xs ${calibrationTarget === "start" ? "bg-emerald-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"}`}
                >
                  调起点
                </button>
                <button
                  type="button"
                  onClick={() => setCalibrationTarget("waypoint")}
                  className={`rounded px-2 py-1 text-xs ${calibrationTarget === "waypoint" ? "bg-sky-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"}`}
                >
                  调途径点
                </button>
                <button
                  type="button"
                  onClick={() => setCalibrationTarget("end")}
                  className={`rounded px-2 py-1 text-xs ${calibrationTarget === "end" ? "bg-rose-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"}`}
                >
                  调终点
                </button>
              </div>
              <div className="mt-2 rounded bg-gray-950/60 px-2 py-2">
                {pickedPoint ? (
                  <>
                    <div>{`候选点: 红 ${formatCoord(pickedPoint.front)} / 蓝 ${formatCoord(pickedPoint.right)} / 绿 ${formatCoord(pickedPoint.up)}`}</div>
                    <div className="mt-1 text-gray-400">{`世界坐标: x ${formatCoord(pickedPoint.x)} / z ${formatCoord(pickedPoint.z)}`}</div>
                  </>
                ) : (
                  <div className="text-gray-500">还没选点，直接点场景里的黄色平面。</div>
                )}
              </div>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  disabled={!pickedPoint}
                  onClick={() => {
                    if (!pickedPoint) return;
                    setPathPoints((prev) => ({
                      ...prev,
                      [calibrationTarget]: pickedPoint,
                    }));
                  }}
                  className="rounded bg-amber-500 px-2 py-1 text-xs font-medium text-gray-950 hover:bg-amber-400 disabled:cursor-not-allowed disabled:bg-gray-700 disabled:text-gray-500"
                >
                  {calibrationTarget === "start"
                    ? "设为箱子起点"
                    : calibrationTarget === "waypoint"
                      ? "设为箱子途径点"
                      : "设为箱子终点"}
                </button>
                <button
                  type="button"
                  onClick={() =>
                    setPathPoints((prev) => ({
                      ...prev,
                      waypoint: null,
                    }))
                  }
                  className="rounded bg-slate-800 px-2 py-1 text-xs text-gray-300 hover:bg-slate-700"
                >
                  清除途径点
                </button>
                <button
                  type="button"
                  onClick={() => setPickedPoint(null)}
                  className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300 hover:bg-gray-700"
                >
                  清除候选点
                </button>
              </div>
              <div className="mt-2 text-gray-400">
                <div>{`当前起点: 红 ${formatCoord(pathPoints.start.front)} / 蓝 ${formatCoord(pathPoints.start.right)}`}</div>
                <div>
                  {pathPoints.waypoint
                    ? `当前途径点: 红 ${formatCoord(pathPoints.waypoint.front)} / 蓝 ${formatCoord(pathPoints.waypoint.right)}`
                    : "当前途径点: 未设置"}
                </div>
                <div>{`当前终点: 红 ${formatCoord(pathPoints.end.front)} / 蓝 ${formatCoord(pathPoints.end.right)}`}</div>
              </div>
            </div>
            <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-0.5 rounded-lg bg-gray-900/80 px-1.5 py-1 backdrop-blur-sm">
              <span className="px-1 text-[10px] text-gray-500">缩放</span>
              <div className="flex gap-0.5">
                <button
                  type="button"
                  onClick={() => orbitRef.current?.dollyOut(ZOOM_STEP)}
                  className="rounded px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 hover:text-white"
                  title="缩小"
                >
                  −
                </button>
                <button
                  type="button"
                  onClick={() => orbitRef.current?.dollyIn(ZOOM_STEP)}
                  className="rounded px-2 py-1 text-xs text-gray-300 hover:bg-gray-700 hover:text-white"
                  title="放大"
                >
                  +
                </button>
              </div>
            </div>
            <PresetViews disabled={false} />
          </>
        )}

        {partLabel && (
          <div className="pointer-events-none absolute left-4 top-4 rounded bg-black/70 px-3 py-1.5 text-sm text-white">
            {partLabel}
          </div>
        )}

        {selectedPart && selectedMapping && (
          <PartInfoPopup
            selectedPart={selectedPart}
            mapping={selectedMapping}
            telemetry={telemetry}
            onClose={() => setSelectedPart(null)}
          />
        )}
      </div>
    </PresetCameraProvider>
  );
}
