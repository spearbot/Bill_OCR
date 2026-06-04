"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { billsApi } from "@/lib/api";
import { toast } from "sonner";
import { Upload, FileImage, Loader2, CheckCircle, XCircle, Camera } from "lucide-react";
import { cn } from "@/lib/utils";

interface UploadStatus {
  file: File;
  status: "pending" | "uploading" | "success" | "error";
  progress: number;
  error?: string;
  billId?: string;
}

export default function UploadPage() {
  const router = useRouter();
  const [uploads, setUploads] = useState<UploadStatus[]>([]);
  const [processing, setProcessing] = useState(false);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newUploads: UploadStatus[] = acceptedFiles.map((file) => ({
      file,
      status: "pending",
      progress: 0,
    }));
    setUploads((prev) => [...prev, ...newUploads]);
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "application/pdf": [".pdf"],
    },
    noClick: true,
  });

  const handleCameraCapture = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.capture = "environment";
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        onDrop(Array.from(files));
      }
    };
    input.click();
  };

  const uploadFile = async (upload: UploadStatus, index: number) => {
    setUploads((prev) =>
      prev.map((u, i) => (i === index ? { ...u, status: "uploading", progress: 10 } : u))
    );

    try {
      setUploads((prev) =>
        prev.map((u, i) => (i === index ? { ...u, progress: 50 } : u))
      );

      const response = await billsApi.upload(upload.file);

      setUploads((prev) =>
        prev.map((u, i) =>
          i === index
            ? { ...u, status: "success", progress: 100, billId: response.data.id }
            : u
        )
      );

      toast.success(`"${upload.file.name}" processed successfully`);

      // Auto-redirect to review page after short delay
      setTimeout(() => {
        router.push(`/review/${response.data.id}`);
      }, 1000);
    } catch (error: any) {
      setUploads((prev) =>
        prev.map((u, i) =>
          i === index
            ? {
                ...u,
                status: "error",
                progress: 0,
                error: error.response?.data?.detail || "Upload failed",
              }
            : u
        )
      );
      toast.error(`Failed to process "${upload.file.name}"`);
    }
  };

  const uploadAll = async () => {
    const pendingUploads = uploads.filter((u) => u.status === "pending");
    if (pendingUploads.length === 0) return;

    setProcessing(true);

    for (let i = 0; i < uploads.length; i++) {
      if (uploads[i].status === "pending") {
        await uploadFile(uploads[i], i);
      }
    }

    setProcessing(false);
    toast.success("All files processed");
  };

  const removeUpload = (index: number) => {
    setUploads((prev) => prev.filter((_, i) => i !== index));
  };

  const successCount = uploads.filter((u) => u.status === "success").length;
  const errorCount = uploads.filter((u) => u.status === "error").length;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Upload Bills</h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Upload medical/pharmacy bills for OCR processing
        </p>
      </div>

      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer",
          isDragActive
            ? "border-primary-500 bg-primary-50 dark:bg-primary-900/20"
            : "border-gray-300 dark:border-gray-600 hover:border-primary-400 dark:hover:border-primary-500"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
          {isDragActive ? "Drop files here" : "Drag & drop bills here"}
        </h3>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Supported formats: JPG, PNG, PDF (max 10MB)
        </p>
        <div className="mt-4 flex flex-wrap justify-center gap-3">
          <button
            onClick={open}
            className="btn-outline flex items-center gap-2"
          >
            <FileImage className="h-4 w-4" />
            Browse Files
          </button>
          <button
            onClick={handleCameraCapture}
            className="btn-outline flex items-center gap-2"
          >
            <Camera className="h-4 w-4" />
            Camera
          </button>
        </div>
      </div>

      {uploads.length > 0 && (
        <div className="card p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Upload Queue ({uploads.length})
            </h3>
            <div className="flex gap-2">
              {successCount > 0 && (
                <span className="text-sm text-green-600 dark:text-green-400 flex items-center gap-1">
                  <CheckCircle className="h-4 w-4" />
                  {successCount}
                </span>
              )}
              {errorCount > 0 && (
                <span className="text-sm text-red-600 dark:text-red-400 flex items-center gap-1">
                  <XCircle className="h-4 w-4" />
                  {errorCount}
                </span>
              )}
            </div>
          </div>

          <div className="space-y-3">
            {uploads.map((upload, index) => (
              <div
                key={index}
                className="flex items-center gap-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
              >
                <FileImage className="h-8 w-8 text-gray-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {upload.file.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {(upload.file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  {upload.status === "uploading" && (
                    <Loader2 className="h-5 w-5 animate-spin text-primary-600" />
                  )}
                  {upload.status === "success" && (
                    <CheckCircle className="h-5 w-5 text-green-600" />
                  )}
                  {upload.status === "error" && (
                    <XCircle className="h-5 w-5 text-red-600" />
                  )}
                  <button
                    onClick={() => removeUpload(index)}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    <XCircle className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 flex justify-end gap-3">
            <button
              onClick={() => setUploads([])}
              className="btn-outline"
            >
              Clear All
            </button>
            <button
              onClick={uploadAll}
              disabled={processing || uploads.every((u) => u.status !== "pending")}
              className="btn-primary flex items-center gap-2"
            >
              {processing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4" />
                  Upload & Process
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
