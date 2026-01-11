 
import { Upload, X } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  FileUpload,
  FileUploadDropzone,
  FileUploadItem,
  FileUploadItemDelete,
  FileUploadItemMetadata,
  FileUploadItemPreview,
  FileUploadItemProgress,
  FileUploadList,
  FileUploadTrigger,
} from "@/components/ui/file-upload";

import { uploadVideoApiVideosUploadPost } from "@/APIs";
 
export default function VideoUpload() {
  const [files, setFiles] = React.useState<File[]>([]);
 
  const onUpload = React.useCallback(
    async (
      files: File[],
      {
        onProgress,
        onSuccess,
        onError,
      }: {
        onProgress: (file: File, progress: number) => void;
        onSuccess: (file: File) => void;
        onError: (file: File, error: Error) => void;
      },
    ) => {
      // console.log('files: ', files)
      try {
        const uploadPromises = files.map(async (file) => {
          let progressTimer: ReturnType<typeof setInterval> | undefined;

          try {
            const fileSizeInMB = file.size / (1024 * 1024);
            const totalDurationMs = fileSizeInMB > 0 ? fileSizeInMB * 1000 : 1000;
            const startTime = Date.now();

            onProgress(file, 0);

            progressTimer = setInterval(() => {
              const elapsedMs = Date.now() - startTime;
              const progress = Math.min(99, (elapsedMs / totalDurationMs) * 100);
              onProgress(file, progress);
            }, 200);

            const { data: response, error: apiError } =
              await uploadVideoApiVideosUploadPost({
                body: {
                  file,
                },
              });

            if (apiError) {
              console.error(apiError);
              throw new Error("Upload failed");
            }

            if (!response || response.code >= 300) {
              const message = response?.err_msg || "Upload failed";
              throw new Error(message);
            }

            if (progressTimer) {
              clearInterval(progressTimer);
              progressTimer = undefined;
            }

            onProgress(file, 100);
            onSuccess(file);

            toast("Upload successful", {
              description: file.name,
            });
          } catch (error) {
            if (progressTimer) {
              clearInterval(progressTimer);
              progressTimer = undefined;
            }

            onError(
              file,
              error instanceof Error ? error : new Error("Upload failed"),
            );
          }
        });
 
        // Wait for all uploads to complete
        await Promise.all(uploadPromises);
      } catch (error) {
        // This handles any error that might occur outside the individual upload processes
        console.error("Unexpected error during upload:", error);
      }
    },
    [],
  );
 
  const onFileReject = React.useCallback((file: File, message: string) => {
    toast(message, {
      description: `"${file.name.length > 20 ? `${file.name.slice(0, 20)}...` : file.name}" has been rejected`,
    });
  }, []);

  return (
    <div className="w-full flex flex-col items-center justify-center">
      <FileUpload
        value={files}
        onValueChange={setFiles}
        accept="video/*,.mp4,.mov,.avi,.mkv,.webm"
        maxSize={200 * 1024 * 1024}
        className="w-full max-w-md"
        onUpload={onUpload}
        onFileReject={onFileReject}
      >
        <FileUploadDropzone>
          <div className="flex flex-col items-center gap-1 text-center">
            <div className="flex items-center justify-center rounded-full border p-2.5">
              <Upload className="size-6 text-muted-foreground" />
            </div>
            <p className="font-medium text-sm">拖拽文件到此处</p>
            <p className="text-muted-foreground text-xs">
              或 点击选择文件 (限制为.mp4/.mov等视频格式，大小不超过200MB)
            </p>
          </div>
          <FileUploadTrigger asChild>
            <Button variant="outline" size="sm" className="mt-2 w-fit">
              Browse files
            </Button>
          </FileUploadTrigger>
        </FileUploadDropzone>
        <FileUploadList orientation="horizontal">
          {files.map((file, index) => (
            <FileUploadItem key={index} value={file} className="p-0">
              <FileUploadItemPreview
                className="size-20 [&>svg]:size-12"
              >
                <FileUploadItemProgress variant="linear" />
              </FileUploadItemPreview>
              <FileUploadItemMetadata className="sr-only" />
              <FileUploadItemDelete asChild>
                <Button
                  variant="secondary"
                  size="icon"
                  className="absolute -top-1 -right-1 size-5 rounded-full"
                >
                  <X className="size-3" />
                </Button>
              </FileUploadItemDelete>
            </FileUploadItem>
          ))}
        </FileUploadList>
      </FileUpload>
    </div>
  );
}
