import { VideoStatusEnum, type Video } from "@/types/video"
import dayjs from "dayjs"
import type { VideoResponse, ApiErrorResponse } from "@/APIs"

export const handleApiError = (apiError: ApiErrorResponse | undefined): string | null  => {
  if (apiError && apiError.code >= 400) {
    console.error(apiError.err_msg)
    return apiError?.err_msg || "Unknown error occurred"
  }
  return null
}

export const getVideoStatusStr = (
  status?: string | number,
): "completed" | "processing" | "failed" | "pending" | "default" => {
  if (typeof status === "string") {
    return (status && ["completed", "processing", "failed", "pending"].includes(status)
      ? status
      : "default") as "completed" | "processing" | "failed" | "pending" | "default";
  }

  if (typeof status === "number") {
    switch (status) {
      case VideoStatusEnum.PENDING:
        return "pending";
      case VideoStatusEnum.PROCESSING:
        return "processing";
      case VideoStatusEnum.COMPLETED:
        return "completed";
      case VideoStatusEnum.FAILED:
        return "failed";
      default:
        return "default";
    }
  }

  return "default";
};

export function formatDuration(ms: number | undefined | null): string {
  if (!ms || ms < 0) return "00:00";
  
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  const pad = (num: number) => num.toString().padStart(2, "0");

  if (hours > 0) {
    return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  }
  return `${pad(minutes)}:${pad(seconds)}`;
}

export function formatVideo(video: VideoResponse): Video {
  return {
    ...video,
    dateStr: video.created_at ? dayjs(video.created_at).format("YYYY-MM-DD") : "",
    durationStr: formatDuration(typeof video.duration === 'string' ? parseInt(video.duration) : video.duration),
    statusStr: getVideoStatusStr(video.status),
  }
}


/**
 * 将图片url转换为File对象
 * @param url 图片url
 * @param fileName 文件名
 * @returns 
 */
export async function urlToFile(url: string, fileName: string) {
    // 1. 下载资源并获取 Blob
    const response = await fetch(url);
    const blob = await response.blob();

    // 2. 将 Blob 包装成 File 对象
    // 获取文件的 MIME 类型（例如 image/jpeg）
    const mimeType = blob.type;
    return new File([blob], fileName, { type: mimeType });
}


export function isNil<T>(value: T | undefined | null): boolean {
  return value === undefined || value === null;
}