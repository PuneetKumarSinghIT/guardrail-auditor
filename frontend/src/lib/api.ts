// Axios instance with a Cognito JWT interceptor. Every request to the REST API
// carries the ID token in the Authorization header; the API Gateway Cognito
// authorizer validates it. Never call fetch() directly elsewhere.

import axios from "axios";
import { env } from "./env";
import { getIdToken } from "./auth";
import type {
  CreateScanResponse,
  ReportUrlResponse,
  ScanDetail,
  ScanSummary,
} from "./types";

export const api = axios.create({
  baseURL: env.apiUrl.replace(/\/$/, ""), // API GW url ends with '/'; normalize
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use(async (config) => {
  const token = await getIdToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Endpoint wrappers ────────────────────────────────────────────────────────

export async function fetchScans(): Promise<ScanSummary[]> {
  const { data } = await api.get<ScanSummary[]>("/v1/scans");
  return data;
}

export async function fetchScan(id: string): Promise<ScanDetail> {
  const { data } = await api.get<ScanDetail>(`/v1/scans/${id}`);
  return data;
}

export async function fetchReportUrl(id: string): Promise<ReportUrlResponse> {
  const { data } = await api.get<ReportUrlResponse>(`/v1/scans/${id}/report`);
  return data;
}

export async function createScan(
  fileName: string
): Promise<CreateScanResponse> {
  const { data } = await api.post<CreateScanResponse>("/v1/scans", {
    file_name: fileName,
  });
  return data;
}

// Uploads the file bytes straight to S3 via the presigned PUT URL. This does NOT
// go through the api instance (no Authorization header — the URL is pre-signed).
export async function uploadToPresignedUrl(
  presignedUrl: string,
  file: File
): Promise<void> {
  await axios.put(presignedUrl, file, {
    headers: { "Content-Type": "" }, // match the presign (no ContentType param)
  });
}
