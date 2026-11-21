import type {
  AnalyzeDocumentResponse,
  CompanyListResponse,
  HealthResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "";

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Health check failed (${res.status})`);
  }
  return res.json();
}

export async function uploadCompanyList(
  file: File
): Promise<CompanyListResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/company-list`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to parse company list (${res.status})`);
  }
  return res.json();
}

export async function analyzeDocument(
  file: File,
  companies: string[],
  useLlmFallback: boolean,
  onProgress?: (percent: number | null, label: string) => void
): Promise<AnalyzeDocumentResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("companies_json", JSON.stringify(companies));
  form.append("use_llm_fallback", String(useLlmFallback));

  return new Promise<AnalyzeDocumentResponse>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/analyze`);

    xhr.upload.onprogress = (event) => {
      if (!onProgress) return;
      if (event.lengthComputable && event.total > 0) {
        const uploadRatio = event.loaded / event.total;
        if (uploadRatio < 1) {
          onProgress(Math.round(uploadRatio * 35), "Uploading document…");
        } else {
          onProgress(null, "Reading document locally…");
        }
      }
    };

    xhr.upload.onload = () => {
      onProgress?.(null, "Reading document locally…");
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          onProgress?.(100, "Complete");
          resolve(JSON.parse(xhr.responseText) as AnalyzeDocumentResponse);
        } catch {
          reject(new Error("Invalid response from analysis server."));
        }
      } else {
        let detail = `Analysis failed (${xhr.status})`;
        try {
          const parsed = JSON.parse(xhr.responseText);
          if (parsed?.detail) detail = String(parsed.detail);
        } catch {
          // keep default message
        }
        reject(new Error(detail));
      }
    };

    xhr.onerror = () => {
      reject(new Error("Network error while analyzing document."));
    };

    onProgress?.(5, "Uploading document…");
    xhr.send(form);
  });
}

export async function exportRenamedZip(
  items: { file: File; targetName: string }[]
): Promise<Blob> {
  const form = new FormData();
  for (const item of items) {
    form.append("files", item.file);
  }
  form.append(
    "target_names_json",
    JSON.stringify(items.map((item) => item.targetName))
  );

  const res = await fetch(`${API_BASE}/api/export-zip`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Export failed (${res.status})`);
  }
  return res.blob();
}
