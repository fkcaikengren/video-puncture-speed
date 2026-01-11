import type { VideoResponse } from "@/APIs";

export interface Video extends VideoResponse {
  dateStr?: string;
  durationStr?: string;
  statusStr?: string;
}
export enum VideoStatusEnum {
    PENDING = 0,
    PROCESSING = 1,
    COMPLETED = 2,
    FAILED = 3,
}
