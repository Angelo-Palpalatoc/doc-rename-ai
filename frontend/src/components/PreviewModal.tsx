"use client";

import { useEffect, useState } from "react";

interface PreviewModalProps {
  file: File;
  previewUrl: string;
  onClose: () => void;
}

export function PreviewModal({
  file,
  previewUrl,
  onClose,
}: PreviewModalProps) {
  const [zoom, setZoom] = useState(100);
  const isImage = file.type.startsWith("image/");

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex h-[100dvh] flex-col bg-[#17202B] text-white"
      role="dialog"
      aria-modal="true"
      aria-label={`Preview ${file.name}`}
    >
      {/* Top Bar */}
      <div className="flex items-center justify-between gap-2 px-4 py-3 pt-[max(0.75rem,env(safe-area-inset-top))]">
        <span className="min-w-0 flex-1 truncate text-sm font-bold text-white">
          {file.name}
        </span>
        <div className="flex shrink-0 items-center gap-1">
          {!isImage && (
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-lg px-3 py-2 text-xs font-medium text-[#B9D9FF] hover:bg-white/10"
            >
              Open PDF
            </a>
          )}
          <button
            type="button"
            onClick={onClose}
            className="min-h-[40px] rounded-lg px-3 py-1.5 text-sm font-medium text-white hover:bg-white/10"
          >
            Close
          </button>
        </div>
      </div>

      {/* Viewer Canvas */}
      <div className="flex flex-1 items-center justify-center overflow-auto px-3 py-2">
        {isImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={previewUrl}
            alt={file.name}
            style={{ width: `${zoom}%`, maxWidth: "none" }}
            className="max-h-full rounded bg-white shadow-xl"
          />
        ) : (
          <iframe
            src={previewUrl}
            title={file.name}
            className="h-full w-full max-w-5xl rounded bg-white shadow-xl"
          />
        )}
      </div>

      {/* Bottom Controls */}
      {isImage && (
        <div className="flex items-center justify-evenly border-t border-white/10 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] text-sm">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(50, z - 25))}
            className="min-h-[44px] rounded-lg px-3 py-1.5 font-medium text-white hover:bg-white/10"
          >
            Zoom out
          </button>
          <button
            type="button"
            onClick={() => setZoom(100)}
            className="min-h-[44px] rounded-lg px-3 py-1.5 font-medium text-white hover:bg-white/10"
          >
            Reset ({zoom}%)
          </button>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(300, z + 25))}
            className="min-h-[44px] rounded-lg px-3 py-1.5 font-medium text-white hover:bg-white/10"
          >
            Zoom in
          </button>
        </div>
      )}
    </div>
  );
}
