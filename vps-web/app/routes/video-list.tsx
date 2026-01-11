import { Suspense, use } from "react"
import { useSearchParams, useLoaderData, useNavigate } from "react-router"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { VideoCard } from "@/components/video-card"
import { VideoStatusEnum } from "@/types/video"
import { getVideosApiVideosGet } from "@/APIs"
import type { BaseResponseVideoListResponse } from "@/APIs/types.gen"
import {
    Pagination,
    PaginationContent,
    PaginationEllipsis,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
} from "@/components/ui/pagination"
import { formatVideo } from "@/utils"
import { useModal } from "@/lib/react-modal-store"

type VideoListPromise = Promise<({
    data: BaseResponseVideoListResponse;
    error: undefined;
} | {
    data: undefined;
    error: Error;
})>

interface LoaderParams {
    page: number;
    pageSize: number;
    keyword: string;
    status: string;
    sortBy: string;
}

export async function clientLoader({ request }: { request: Request }) {
    const url = new URL(request.url);
    const page = Number(url.searchParams.get("page")) || 1;
    const pageSize = Number(url.searchParams.get("page_size")) || 10;
    const keyword = url.searchParams.get("keyword") || "";
    const status = url.searchParams.get("status") || "all";
    const sortBy = url.searchParams.get("sort_by") || "date";

    const query: any = {
        page,
        page_size: pageSize,
        keyword,
    };

    if (status !== "all") {
        // Map status string to enum value if needed, assuming API accepts number
        // Check if status is a valid number or map from string
        const statusMap: Record<string, number> = {
            "pending": VideoStatusEnum.PENDING,
            "processing": VideoStatusEnum.PROCESSING,
            "completed": VideoStatusEnum.COMPLETED,
            "failed": VideoStatusEnum.FAILED
        };
        if (status in statusMap) {
            query.status = statusMap[status];
        }
    }
    
    // Note: sortBy is not supported by the API yet according to types, but we keep it in params for UI state

    const p = getVideosApiVideosGet({
        query: query
    })
    
    return {
        videoListPromise: p as VideoListPromise,
        params: { page, pageSize, keyword, status, sortBy } as LoaderParams
    } 
}


export default function VideoList() {
    const { videoListPromise, params } = useLoaderData<typeof clientLoader>()

    
    return (
        <Suspense fallback={<VideoListSkeleton />}  key={params.page || '1'}>
            <VideoListContent videoListPromise={videoListPromise} params={params} />
        </Suspense>
    )
}

function VideoListContent({
    videoListPromise,
    params,
}: {
    videoListPromise: VideoListPromise
    params: LoaderParams
}) {
    const navigate = useNavigate()
    const dispatchModal = useModal()
    const [, setSearchParams] = useSearchParams();
    console.log('pp: ', videoListPromise)

    const { data: response } = use(videoListPromise)

    const videos = response?.data?.items || [];
    const total = response?.data?.total || 0;
    const totalPages = Math.ceil(total / params.pageSize);

    const handlePageChange = (newPage: number) => {
        if (newPage < 1 || newPage > totalPages) return;
        setSearchParams((prev) => {
            prev.set("page", String(newPage));
            return prev;
        });
    };

    const handleSearch = (value: string) => {
        setSearchParams((prev) => {
            if (value) {
                prev.set("keyword", value);
            } else {
                prev.delete("keyword");
            }
            prev.set("page", "1");
            return prev;
        });
    };

    const handleStatusChange = (value: string) => {
        setSearchParams((prev) => {
            prev.set("status", value);
            prev.set("page", "1");
            return prev;
        });
    };

    const handleSortChange = (value: string) => {
        setSearchParams((prev) => {
            prev.set("sort_by", value);
            return prev;
        });
    };

    const renderPaginationItems = () => {
        const items = [] as JSX.Element[];
        const maxVisiblePages = 5;
        let startPage = Math.max(1, params.page - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        if (startPage > 1) {
            items.push(
                <PaginationItem key="1">
                    <PaginationLink href="#" onClick={(e) => { e.preventDefault(); handlePageChange(1); }}>1</PaginationLink>
                </PaginationItem>
            );
            if (startPage > 2) {
                items.push(
                    <PaginationItem key="ellipsis-start">
                        <PaginationEllipsis />
                    </PaginationItem>
                );
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            items.push(
                <PaginationItem key={i}>
                    <PaginationLink 
                        href="#" 
                        isActive={i === params.page}
                        onClick={(e) => { e.preventDefault(); handlePageChange(i); }}
                    >
                        {i}
                    </PaginationLink>
                </PaginationItem>
            );
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                items.push(
                    <PaginationItem key="ellipsis-end">
                        <PaginationEllipsis />
                    </PaginationItem>
                );
            }
            items.push(
                <PaginationItem key={totalPages}>
                    <PaginationLink href="#" onClick={(e) => { e.preventDefault(); handlePageChange(totalPages); }}>{totalPages}</PaginationLink>
                </PaginationItem>
            );
        }

        return items;
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
                <div className="flex gap-2 w-full md:w-auto">
                    <Input 
                        placeholder="Search videos..." 
                        className="max-w-[200px]" 
                        defaultValue={params.keyword}
                        onChange={(e) => handleSearch(e.target.value)}
                    />
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
                {videos.map(formatVideo).map((video) => (
                    <VideoCard 
                        key={video.id} 
                        video={video} 
                        onPlay={()=>{
                            dispatchModal('VideoPlayModal',{
                                video,
                            })
                        }}
                        onAnalysis={() => navigate(`/video/analysis?id=${video.id}`)}
                    />
                ))}
            </div>

            {totalPages > 1 && (
                <Pagination>
                    <PaginationContent>
                        <PaginationItem>
                            <PaginationPrevious 
                                href="#" 
                                onClick={(e) => { e.preventDefault(); handlePageChange(params.page - 1); }}
                                className={params.page <= 1 ? "pointer-events-none opacity-50" : ""}
                            />
                        </PaginationItem>
                        {renderPaginationItems()}
                        <PaginationItem>
                            <PaginationNext 
                                href="#" 
                                onClick={(e) => { e.preventDefault(); handlePageChange(params.page + 1); }}
                                className={params.page >= totalPages ? "pointer-events-none opacity-50" : ""}
                            />
                        </PaginationItem>
                    </PaginationContent>
                </Pagination>
            )}
        </div>
    )
}

function VideoListSkeleton() {
    return (
        <div className="space-y-6 animate-pulse">
            <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
                <div className="flex gap-2 w-full md:w-auto">
                    <div className="h-10 w-[200px] bg-muted rounded" />
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
    )
}
