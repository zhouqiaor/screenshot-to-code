/**
 * ADB capture API client.
 * Calls the backend /api/adb/* endpoints for Android device UI capture.
 */
import { HTTP_BACKEND_URL } from "../config";

export interface AdbDeviceInfo {
  deviceId: string;
  state: string;
}

export interface AdbCaptureResult {
  screenshotDataUrl: string;
  skeleton: Record<string, unknown>;
  theme: Record<string, unknown>;
  designSystemBlock: string;
  deviceId: string;
}

export async function fetchAdbDevices(): Promise<AdbDeviceInfo[]> {
  const response = await fetch(`${HTTP_BACKEND_URL}/api/adb/devices`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Failed to list ADB devices");
  }
  const data = await response.json();
  return data.devices || [];
}

export async function captureViaAdb(deviceId?: string | null): Promise<AdbCaptureResult> {
  const response = await fetch(`${HTTP_BACKEND_URL}/api/adb/capture`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ deviceId: deviceId ?? null }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "ADB capture failed");
  }
  return response.json();
}
