import { Suspense, use, useEffect, useState } from "react"
import { Copy } from "lucide-react"
import { useLoaderData, useNavigate, useSearchParams } from "react-router"
import { getVideosApiDashboardVideosGet, getStatsApiDashboardStatsGet} from "@/APIs"
import type {  BaseResponseStatsData, BaseResponseListPendingVideoGroup, VideoStatus } from "@/APIs"
import { cn } from "@/lib/utils"
import { VideoCard } from "@/components/video-card"
import { formatVideo } from "@/utils"
import { useModal } from "@/lib/react-modal-store"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { useCopyToClipboard } from 'react-use'
import { toast } from "sonner"

type VideosPromise =  Promise<{
    data: BaseResponseListPendingVideoGroup;
}>;

type StatsPromise = Promise<{
    data: BaseResponseStatsData;
}>;

export async function clientLoader({ request }: { request: Request }) {
  const url = new URL(request.url)
  const rawStatus = url.searchParams.get("status")
  const parsedStatus =
    rawStatus === null || rawStatus.trim() === "" ? undefined : Number(rawStatus)
  const status =
    parsedStatus === 0 || parsedStatus === 1 || parsedStatus === 2 || parsedStatus === 3
      ? (parsedStatus as VideoStatus)
      : undefined

  const statsPromise = getStatsApiDashboardStatsGet()
  const videosPromise = getVideosApiDashboardVideosGet(
    status === undefined ? undefined : { query: { status } },
  )
  
  return {
    stats: statsPromise as StatsPromise,
    videos: videosPromise as VideosPromise,
  }
}

export function shouldRevalidate({
  currentUrl,
  nextUrl,
  defaultShouldRevalidate,
}: {
  currentUrl: URL
  nextUrl: URL
  defaultShouldRevalidate: boolean
}) {
  if (currentUrl.searchParams.get("status") !== nextUrl.searchParams.get("status")) {
    return true
  }
  return defaultShouldRevalidate
}

function StatsSection({ statsPromise }: { statsPromise: StatsPromise }) {
  const { data: response } = use(statsPromise)
  const stats = response?.data
  const [searchParams, setSearchParams] = useSearchParams()
  const activeStatus = searchParams.get("status")

  if (!stats) return null

  const items: Array<{
    key: string
    label: string
    count: number
    status: string | null
    countClassName: string
  }> = [
    {
      key: "all",
      label: "全部",
      count: stats.total,
      status: null,
      countClassName: "text-gray-600 dark:text-gray-400",
    },
    {
      key: "completed",
      label: "已完成",
      count: stats.completed,
      status: "2",
      countClassName: "text-green-600 dark:text-green-400",
    },
    {
      key: "pending",
      label: "待处理",
      count: stats.pending,
      status: "0",
      countClassName: "text-yellow-600 dark:text-yellow-400",
    },
    {
      key: "processing",
      label: "处理中",
      count: stats.processing,
      status: "1",
      countClassName: "text-blue-600 dark:text-blue-400",
    },
    {
      key: "failed",
      label: "失败",
      count: stats.failed,
      status: "3",
      countClassName: "text-red-600 dark:text-red-400",
    },
  ]

  return (
    <div className="inline-flex items-center overflow-hidden rounded-md border border-input bg-background shadow-xs">
      {items.map((item, idx) => {
        const isActive = item.status === null ? activeStatus === null : activeStatus === item.status
        return (
          <Button
            key={item.key}
            type="button"
            variant={isActive ? "secondary" : "ghost"}
            className={cn(
              "rounded-none px-3",
              idx !== 0 && "border-l border-input",
              idx === 0 && "rounded-l-md",
              idx === items.length - 1 && "rounded-r-md",
            )}
            onClick={() =>
              setSearchParams(
                (prev) => {
                  const next = new URLSearchParams(prev)
                  if (item.status === null) next.delete("status")
                  else next.set("status", item.status)
                  return next
                },
                { replace: true },
              )
            }
          >
            <span>{item.label}</span>
            <span
              className={cn(
                "ml-2 text-xs tabular-nums",
                item.countClassName,
                isActive ? "opacity-100" : "opacity-80",
              )}
            >
              {item.count}
            </span>
          </Button>
        )
      })}
    </div>
  )
}

function VideosSection({ videosPromise }: { videosPromise: VideosPromise }) {
  const { data: response } = use(videosPromise)
  const navigate = useNavigate()
  const dispatchModal = useModal()
  const [searchParams, setSearchParams] = useSearchParams()
  const pendingVideos =
    response?.data?.map((group) => ({
      ...group,
      list: group.list.map(formatVideo),
    })) ?? []

  const totalVideos = pendingVideos.reduce((sum, group) => sum + group.list.length, 0)
  const hasStatusFilter = searchParams.get("status") !== null

  if (totalVideos === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
          <div className="text-sm font-medium">暂无数据</div>
          <div className="text-sm text-muted-foreground">
            {hasStatusFilter ? "当前筛选条件下没有视频" : "暂时没有可展示的视频"}
          </div>
          {hasStatusFilter ? (
            <Button
              type="button"
              variant="secondary"
              onClick={() =>
                setSearchParams(
                  (prev) => {
                    const next = new URLSearchParams(prev)
                    next.delete("status")
                    return next
                  },
                  { replace: true },
                )
              }
            >
              查看全部
            </Button>
          ) : null}
      </div>
    )
  }

  return (
    <div className="space-y-8">
    {pendingVideos.map((group) => (
        <div key={group.date} className="space-y-4">
            <div className="flex items-center gap-2">
                <div className="h-px flex-1 bg-border"></div>
                <span className="text-sm text-muted-foreground font-medium">{group.date}</span>
                <div className="h-px flex-1 bg-border"></div>
            </div>
            
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {group.list.map((video) => (
                    <VideoCard 
                        key={video.id} 
                        video={video}
                        onPlay={() => 
                            dispatchModal('VideoPlayModal',{
                                video,
                            })
                        }
                        onAnalysis={() => navigate(`/video/analysis?id=${video.id}`)}
                    />
                ))}
            </div>
        </div>
    ))}
    </div>
  )
}

function StatsSkeleton() {
    return (
      <div className="inline-flex items-center overflow-hidden rounded-md border border-input bg-background shadow-xs animate-pulse">
        {[...Array(5)].map((_, idx) => (
          <div
            key={idx}
            className={cn("flex h-9 items-center px-3", idx !== 0 && "border-l border-input")}
          >
            <div className="h-4 w-10 bg-muted rounded" />
            <div className="ml-2 h-3 w-6 bg-muted rounded" />
          </div>
        ))}
      </div>
    )
}

function VideosSkeleton() {
    return (
        <div className="space-y-8 animate-pulse">
             {[...Array(2)].map((_, i) => (
                <div key={i} className="space-y-4">
                    <div className="h-4 bg-muted w-24 mx-auto rounded"></div>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                         {[...Array(5)].map((_, j) => (
                             <div key={j} className="aspect-video bg-muted rounded-md"></div>
                         ))}
                    </div>
                </div>
             ))}
        </div>
    )
}

export default function Dashboard() {
  const { stats, videos } = useLoaderData<typeof clientLoader>()
  const [copyState, copyToClipboard] = useCopyToClipboard();
  const [copyInteraction, setCopyInteraction] = useState<boolean>(false)

  useEffect(()=>{
    if(copyState.error){
      toast.error('复制失败')
    }else if(copyState.value){
      toast.success('复制成功')
    }
  }, [copyState.error, copyState.value, copyInteraction])

  const getH5Link = async ()=>{
    // TODO: 服务端支持创建 临时连接 （1天有效期，定时任务清理）
    copyToClipboard('http://localhost:3000/h5')
    setCopyInteraction((state)=>!state)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <Button className="ml-2" onClick={getH5Link}>
            获取h5上传地址
            <Copy className="mr-1"  />
          </Button>
        </div>

        
        <Suspense fallback={<StatsSkeleton />}>
            <StatsSection statsPromise={stats} />
        </Suspense>
      </div>

      <Suspense fallback={<VideosSkeleton />}>
          <VideosSection videosPromise={videos} />
      </Suspense>

    </div>
  )
}
