import type { ViewAngleImage } from "@/types/equipment";

/**
 * 14 images mapped to spherical coordinates (design §2.2).
 * theta: horizontal 0–360° (0=front, 90=right, 180=back, 270=left)
 * phi: vertical -90° to +90° (0=horizon, positive=above, negative=below)
 */
export const VIEW_ANGLES: ViewAngleImage[] = [
  { id: "front", src: "/images/front.png", theta: 0, phi: 0 },
  { id: "front-right", src: "/images/front-right.png", theta: 45, phi: 0 },
  { id: "right", src: "/images/right.png", theta: 90, phi: 0 },
  { id: "back-right", src: "/images/back-right.png", theta: 135, phi: 0 },
  { id: "back", src: "/images/back.png", theta: 180, phi: 0 },
  { id: "back-left", src: "/images/back-left.png", theta: 225, phi: 0 },
  { id: "left", src: "/images/left.png", theta: 270, phi: 0 },
  { id: "front-left", src: "/images/front-left.png", theta: 315, phi: 0 },
  { id: "top-front", src: "/images/top-front.png", theta: 0, phi: 45 },
  { id: "top-back", src: "/images/top-back.png", theta: 180, phi: 45 },
  { id: "top-left", src: "/images/top-left.png", theta: 270, phi: 45 },
  { id: "top-right", src: "/images/top-right.png", theta: 90, phi: 45 },
  { id: "top", src: "/images/top.png", theta: 0, phi: 90 },
  { id: "bottom", src: "/images/bottom.png", theta: 0, phi: -90 },
];
