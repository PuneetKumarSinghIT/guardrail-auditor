import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useCreateScan } from "../hooks/useScans";

const ACCEPTED = {
  "application/octet-stream": [
    ".tf",
    ".hcl",
    ".yaml",
    ".yml",
    ".json",
    ".template",
  ],
};

// Drag-drop (or click) IaC upload zone. On drop: POST /v1/scans for a presigned
// URL, then PUT the file to S3 — the ObjectCreated event drives the pipeline.
export function ScanUploader() {
  const createScan = useCreateScan();
  const [lastFile, setLastFile] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[]) => {
      const file = accepted[0];
      if (!file) return;
      setLastFile(file.name);
      createScan.mutate(file);
    },
    [createScan]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    multiple: false,
  });

  return (
    <div>
      <div
        {...getRootProps()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
          isDragActive
            ? "border-blue-500 bg-blue-50"
            : "border-slate-300 bg-white hover:border-blue-400 hover:bg-slate-50"
        }`}
      >
        <input {...getInputProps()} />
        <p className="text-sm font-medium text-slate-700">
          {isDragActive
            ? "Drop the IaC file here…"
            : "Drag & drop a Terraform or CloudFormation file, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-slate-400">
          .tf · .hcl · .yaml · .json · .template
        </p>
      </div>

      {createScan.isPending && lastFile && (
        <p className="mt-3 text-sm text-blue-600">Uploading {lastFile}…</p>
      )}
      {createScan.isSuccess && lastFile && (
        <p className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          Scan queued for <strong>{lastFile}</strong> — you'll receive an email
          when it completes.
        </p>
      )}
      {createScan.isError && (
        <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          Upload failed. Please try again.
        </p>
      )}
    </div>
  );
}
