import { useMemo, type ReactNode } from "react";
import { data, useNavigate, useSearchParams } from "react-router";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { VideoCard } from "@/components/video-card";
import { VideoStatusEnum, type Video } from "@/types/video";
import { getVideosApiVideosGet, getUploadersApiVideosUploadersGet } from "@/APIs";
import type { BaseResponseVideoListResponse, GetVideosApiVideosGetData, VideoResponse } from "@/APIs/types.gen";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Button } from "@/components/ui/button";
import { formatVideo } from "@/utils";
import { useModal } from "@/lib/react-modal-store";
import { toast } from "sonner";



export interface VideoSearchListParams {
  page: number;
  pageSize: number;
  keyword: string;
  uploader: string;
  status: string;
  sortBy: string;
}

type VideoSearchListProps = {
  initialParams?: Partial<VideoSearchListParams>;
  selectable?: boolean;
  disabledVideoIds?: string[];
  onSelectVideoId?: (videoId: string) => void;
};

function toStatusQuery(status: string) {
  if (status === "all") return undefined;
  const statusMap: Record<string, number> = {
    pending: VideoStatusEnum.PENDING,
    processing: VideoStatusEnum.PROCESSING,
    completed: VideoStatusEnum.COMPLETED,
    failed: VideoStatusEnum.FAILED,
  };
  if (status in statusMap) return statusMap[status];
  return undefined;
}

function parsePositiveInt(value: string | null, fallback: number) {
  if (!value) return fallback;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return fallback;
  return parsed;
}

function VideoSearchListSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="flex gap-2 w-full md:w-auto">
          <div className="h-10 w-[200px] bg-muted rounded" />
          <div className="h-10 w-[160px] bg-muted rounded" />
          <div className="h-10 w-[140px] bg-muted rounded" />
          <div className="h-10 w-[140px] bg-muted rounded" />
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {[...Array(10)].map((_, i) => (
          <div key={i} className="aspect-video bg-muted rounded-md" />
        ))}
      </div>
    </div>
  );
}

function VideoSearchListContent({
  response,
  params,
  onParamsChange,
  selectable,
  disabledVideoIds,
  onSelectVideoId,
}: {
  response?: BaseResponseVideoListResponse;
  params: VideoSearchListParams;
  onParamsChange: (next: VideoSearchListParams) => void;
  selectable?: boolean;
  disabledVideoIds?: string[];
  onSelectVideoId?: (videoId: string) => void;
}) {
  const navigate = useNavigate();
  const dispatchModal = useModal();

  const videos = (response?.data?.items || []) as VideoResponse[];
  const total = response?.data?.total || 0;
  const totalPages = Math.ceil(total / params.pageSize);

  const { data: uploadersData, isLoading: isUploadersLoading } = useQuery({
    queryKey: ["video-uploaders"],
    queryFn: async (): Promise<string[]> => {
      const { data:res, error } = await getUploadersApiVideosUploadersGet();
      if(error || (res && res.code >= 300)){
        toast.error(res?.err_msg || '加载上传人列表失败');
        return []
      }
      return res?.data || [];
    },
    staleTime: 60_000,
  });

  const uploaderSelectValue = params.uploader ? params.uploader : "__all__";


  const handlePageChange = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages) return;
    onParamsChange({ ...params, page: newPage });
  };

  const handleSearch = (value: string) => {
    onParamsChange({ ...params, keyword: value, page: 1 });
  };

  const handleUploaderChange = (value: string) => {
    onParamsChange({ ...params, uploader: value === "__all__" ? "" : value, page: 1 });
  };

  const handleStatusChange = (value: string) => {
    onParamsChange({ ...params, status: value, page: 1 });
  };

  const handleSortChange = (value: string) => {
    onParamsChange({ ...params, sortBy: value });
  };

  const paginationItems = useMemo(() => {
    const items: ReactNode[] = [];
    const maxVisiblePages = 5;
    let startPage = Math.max(1, params.page - Math.floor(maxVisiblePages / 2));
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    if (startPage > 1) {
      items.push(
        <PaginationItem key="1">
          <PaginationLink
            href="#"
            onClick={(e) => {
              e.preventDefault();
              handlePageChange(1);
            }}
          >
            1
          </PaginationLink>
        </PaginationItem>,
      );
      if (startPage > 2) {
        items.push(
          <PaginationItem key="ellipsis-start">
            <PaginationEllipsis />
          </PaginationItem>,
        );
      }
    }

    for (let i = startPage; i <= endPage; i += 1) {
      items.push(
        <PaginationItem key={i}>
          <PaginationLink
            href="#"
            isActive={i === params.page}
            onClick={(e) => {
              e.preventDefault();
              handlePageChange(i);
            }}
          >
            {i}
          </PaginationLink>
        </PaginationItem>,
      );
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        items.push(
          <PaginationItem key="ellipsis-end">
            <PaginationEllipsis />
          </PaginationItem>,
        );
      }
      items.push(
        <PaginationItem key={totalPages}>
          <PaginationLink
            href="#"
            onClick={(e) => {
              e.preventDefault();
              handlePageChange(totalPages);
            }}
          >
            {totalPages}
          </PaginationLink>
        </PaginationItem>,
      );
    }

    return items;
  }, [params.page, totalPages]);

  const formattedVideos = useMemo(() => videos.map(formatVideo), [videos]);

  const canSelect = (video: Video) => {
    if (video.statusStr !== "completed") return false;
    if (Array.isArray(disabledVideoIds) && disabledVideoIds.includes(video.id)) return false;
    return true;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="flex gap-2 w-full md:w-auto">
          <Input
            placeholder="Search videos..."
            className="max-w-[200px]"
            value={params.keyword}
            onChange={(e) => handleSearch(e.target.value)}
          />
          <Select value={uploaderSelectValue} onValueChange={handleUploaderChange} disabled={isUploadersLoading}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Uploader" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__all__">All Uploaders</SelectItem>
              {uploadersData?.map((uploader) => (
                <SelectItem key={uploader} value={uploader}>
                  {uploader}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={params.status} onValueChange={handleStatusChange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
            </SelectContent>
          </Select>
          <Select value={params.sortBy} onValueChange={handleSortChange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Sort By" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date">Date</SelectItem>
              <SelectItem value="name">Name</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {formattedVideos.map((video) => (
          <div key={video.id} className="space-y-2">
            <VideoCard
              video={video}
              onPlay={() => {
                dispatchModal("VideoPlayModal", { video });
              }}
              onAnalysis={selectable ? undefined : () => navigate(`/video/analysis?id=${video.id}`)}
            />
            {selectable ? (
              <Button
                type="button"
                variant="outline"
                className="w-full"
                disabled={!canSelect(video)}
                onClick={() => onSelectVideoId?.(video.id)}
              >
                {canSelect(video) ? "选择" : "仅 Completed 可选"}
              </Button>
            ) : null}
          </div>
        ))}
      </div>

      {totalPages > 1 ? (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  handlePageChange(params.page - 1);
                }}
                className={params.page <= 1 ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
            {paginationItems}
            <PaginationItem>
              <PaginationNext
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  handlePageChange(params.page + 1);
                }}
                className={params.page >= totalPages ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      ) : null}
    </div>
  );
}

export default function VideoSearchList(props: VideoSearchListProps) {
  const [searchParams, setSearchParams] = useSearchParams();

  const params = useMemo<VideoSearchListParams>(() => {
    const defaults: VideoSearchListParams = {
      page: 1,
      pageSize: 10,
      keyword: "",
      uploader: "",
      status: "all",
      sortBy: "date",
    };

    const base = { ...defaults, ...(props.initialParams ?? {}) };
    return {
      ...base,
      page: parsePositiveInt(searchParams.get("page"), base.page),
      pageSize: parsePositiveInt(searchParams.get("page_size"), base.pageSize),
      keyword: searchParams.get("keyword") ?? base.keyword,
      uploader: searchParams.get("uploader") ?? base.uploader,
      status: searchParams.get("status") ?? base.status,
      sortBy: searchParams.get("sort_by") ?? base.sortBy,
    };
  }, [props.initialParams, searchParams]);

  const onParamsChange = (next: VideoSearchListParams) => {
    setSearchParams((prev) => {
      const nextSearchParams = new URLSearchParams(prev);
      nextSearchParams.set("page", String(next.page));
      nextSearchParams.set("page_size", String(next.pageSize));
      if (next.keyword) nextSearchParams.set("keyword", next.keyword);
      else nextSearchParams.delete("keyword");
      if (next.uploader) nextSearchParams.set("uploader", next.uploader);
      else nextSearchParams.delete("uploader");
      nextSearchParams.set("status", next.status);
      nextSearchParams.set("sort_by", next.sortBy);
      return nextSearchParams;
    });
  };

  const query = useMemo<NonNullable<GetVideosApiVideosGetData["query"]>>(() => {
    const nextQuery: NonNullable<GetVideosApiVideosGetData["query"]> = {
      page: params.page,
      page_size: params.pageSize,
    };
    if (params.keyword) nextQuery.keyword = params.keyword;
    if (params.uploader) nextQuery.uploader = params.uploader;
    const statusQuery = toStatusQuery(params.status);
    if (typeof statusQuery === "number") nextQuery.status = statusQuery;
    return nextQuery;
  }, [params.keyword, params.page, params.pageSize, params.status, params.uploader]);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["videos", query],
    queryFn: async () => getVideosApiVideosGet({ query, throwOnError: true }),
    placeholderData: keepPreviousData,
    staleTime: 10_000,
  });

  if (isLoading) return <VideoSearchListSkeleton />;
  if (isError) {
    return (
      <div className="space-y-4">
        <div className="text-sm text-destructive">{String(error)}</div>
        <Button
          type="button"
          variant="outline"
          onClick={() => refetch()}
        >
          重试
        </Button>
      </div>
    );
  }

  const response = data?.data;

  return (
    <VideoSearchListContent
      response={response}
      params={params}
      onParamsChange={onParamsChange}
      selectable={props.selectable}
      disabledVideoIds={props.disabledVideoIds}
      onSelectVideoId={props.onSelectVideoId}
    />
  );
}
