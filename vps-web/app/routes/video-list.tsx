import { Suspense } from "react"
import { useLoaderData } from "react-router"
import { VideoStatusEnum } from "@/types/video"
import { getVideosApiVideosGet } from "@/APIs"
import type { BaseResponseVideoListResponse } from "@/APIs/types.gen"
import VideoSearchList from "@/components/biz/video-search-list"

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


export default function VideoList() {

    
    return (
        <VideoSearchList />
    )
}
