// React Query hooks for scan data. The list auto-refetches every 30s so a scan's
// status (QUEUED → SCANNING → COMPLETE) updates without a manual reload — this
// replaces the removed WebSocket push.

import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  createScan,
  fetchReportUrl,
  fetchScan,
  fetchScans,
  uploadToPresignedUrl,
} from "../lib/api";

export function useScans() {
  return useQuery({
    queryKey: ["scans"],
    queryFn: fetchScans,
    refetchInterval: 30_000,
  });
}

export function useScan(id: string | undefined) {
  return useQuery({
    queryKey: ["scan", id],
    queryFn: () => fetchScan(id as string),
    enabled: !!id,
    // While a scan is still processing, poll the detail view too.
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && ["COMPLETE", "FAILED"].includes(status) ? false : 15_000;
    },
  });
}

// Lazily fetched — only enabled when the user clicks "Download PDF Report".
export function useReportUrl(id: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: ["report", id],
    queryFn: () => fetchReportUrl(id as string),
    enabled: !!id && enabled,
    retry: false, // 404 until the report exists — don't hammer
    staleTime: 10 * 60_000,
  });
}

// Two-step upload: POST /v1/scans for a presigned URL + scan_job_id, then PUT the
// file bytes to S3. The S3 ObjectCreated event then drives the scan pipeline.
export function useCreateScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const { presigned_url, scan_job_id } = await createScan(file.name);
      await uploadToPresignedUrl(presigned_url, file);
      return { scan_job_id, file_name: file.name };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scans"] });
    },
  });
}
