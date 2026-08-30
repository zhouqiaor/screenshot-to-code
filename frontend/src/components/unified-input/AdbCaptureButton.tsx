/**
 * ADB Capture button — visible only when the selected stack is android_compose.
 * On click: calls the backend ADB pipeline, receives screenshot + design data,
 * and passes them back to the parent for auto-injection.
 */
import { useState } from "react";
import { LuSmartphone } from "react-icons/lu";
import { toast } from "react-hot-toast";
import { captureViaAdb, fetchAdbDevices, type AdbCaptureResult } from "../../lib/adb-api";
import type { Stack } from "../../lib/stacks";

interface Props {
  stack: Stack;
  onCaptureComplete: (result: AdbCaptureResult) => void;
}

function AdbCaptureButton({ stack, onCaptureComplete }: Props) {
  const [isCapturing, setIsCapturing] = useState(false);
  const [showDeviceInput, setShowDeviceInput] = useState(false);
  const [deviceId, setDeviceId] = useState("");
  const [devices, setDevices] = useState<string[]>([]);

  // Only show for Android Compose stack
  if (stack !== Stack.ANDROID_COMPOSE) {
    return null;
  }

  const handleCapture = async () => {
    setIsCapturing(true);
    try {
      const result = await captureViaAdb(deviceId || null);
      toast.success(
        `Captured from ${result.deviceId}. Design data injected — ready to generate!`
      );
      onCaptureComplete(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`ADB capture failed: ${msg}`);
    } finally {
      setIsCapturing(false);
    }
  };

  const handleListDevices = async () => {
    try {
      const deviceList = await fetchAdbDevices();
      if (deviceList.length === 0) {
        toast.error("No ADB devices connected.");
        return;
      }
      setDevices(deviceList.map((d) => d.deviceId));
      setDeviceId(deviceList[0].deviceId);
      setShowDeviceInput(true);
      toast.success(`Found ${deviceList.length} device(s).`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      toast.error(`Failed to list devices: ${msg}`);
    }
  };

  if (isCapturing) {
    return (
      <div className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
        <svg
          className="animate-spin h-4 w-4"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014.77 7.038L2.04 9.762a8 0 0114.318-2.176L13.5 5.5a8 8 0 00-7.5 7z"
          />
        </svg>
        <span>Capturing from device…</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center gap-2">
      <button
        type="button"
        onClick={handleCapture}
        className="flex items-center gap-2 px-4 py-2 rounded-lg border border-purple-300 dark:border-purple-700 bg-purple-50 dark:bg-purple-950/30 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900/40 transition-colors text-sm font-medium"
      >
        <LuSmartphone className="h-4 w-4" />
        <span>Capture from ADB Device</span>
      </button>

      {showDeviceInput && devices.length > 0 && (
        <div className="flex items-center gap-2 text-xs">
          <select
            value={deviceId}
            onChange={(e) => setDeviceId(e.target.value)}
            className="border border-gray-300 dark:border-zinc-600 rounded px-2 py-1 bg-white dark:bg-zinc-800 text-gray-700 dark:text-zinc-200"
          >
            {devices.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </div>
      )}

      <button
        type="button"
        onClick={handleListDevices}
        className="text-xs text-gray-400 dark:text-zinc-500 hover:text-gray-600 dark:hover:text-zinc-300 underline"
      >
        Select device
      </button>
    </div>
  );
}

export default AdbCaptureButton;
