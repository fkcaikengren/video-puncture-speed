import { Suspense, use, useEffect, useRef, useState } from "react"
import { ExternalLink, Copy } from "lucide-react"
import { useLoaderData, useNavigate } from "react-router"
import { getPendingVideosApiDashboardPendingVideosGet, getStatsApiDashboardStatsGet} from "@/APIs"
import type {  BaseResponseStatsData, BaseResponseListPendingVideoGroup } from "@/APIs"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"
import { VideoCard } from "@/components/video-card"
import { formatVideo } from "@/utils"
import { useModal } from "@/lib/react-modal-store"
import { Button } from "@/components/ui/button"
import { useCopyToClipboard } from 'react-use'
import { toast } from "sonner"

type VideosPromise =  Promise<{
    data: BaseResponseListPendingVideoGroup;
}>;

type StatsPromise = Promise<{
    data: BaseResponseStatsData;
}>;

export async function clientLoader() {
  const statsPromise = getStatsApiDashboardStatsGet()
  const videosPromise = getPendingVideosApiDashboardPendingVideosGet()
  
  return {
    stats: statsPromise as StatsPromise,
    videos: videosPromise as VideosPromise,
  }
}

const statsValueVariants = cva(
  "text-sm font-semi-bold leading-none",
  {
    variants: {
      variant: {
        default: "text-gray-600 dark:text-gray-400",
        success: "text-green-600 dark:text-green-400",
        warning: "text-yellow-600 dark:text-yellow-400",
        info: "text-blue-600 dark:text-blue-400",
        destructive: "text-red-600 dark:text-red-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

interface StatsItemProps extends VariantProps<typeof statsValueVariants> {
  label: string
  value: number | string
  className?: string
}

function StatsItem({ label, value, variant, className }: StatsItemProps) {
  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      <span className="text-muted-foreground text-sm font-medium tracking-wider">
        {label}
      </span>
      <span className={statsValueVariants({ variant })}>
        {value}
      </span>
    </div>
  )
}

function StatsSection({ statsPromise }: { statsPromise: StatsPromise }) {
  const { data: response } = use(statsPromise)
  const stats = response?.data

  if (!stats) return null

  return (
    <div className="flex flex-wrap items-center gap-6">
        <StatsItem label="全部" value={stats.total} />
        <StatsItem label="已完成" value={stats.completed} variant="success" />
        <StatsItem label="待处理" value={stats.pending} variant="warning" />
        <StatsItem label="处理中" value={stats.processing} variant="info" />
        <StatsItem label="失败" value={stats.failed} variant="destructive" />
    </div>
  )
}

function VideosSection({ videosPromise }: { videosPromise: VideosPromise }) {
  const { data: response } = use(videosPromise)
  const navigate = useNavigate()
  const dispatchModal = useModal()
  const pendingVideos = response?.data?.map(group => ({
    ...group,
    list: group.list.map(formatVideo)
  }))

  if (!pendingVideos) return null

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
        <div className="flex flex-wrap items-center gap-6 animate-pulse">
             {[...Array(5)].map((_, i) => (
                <div key={i} className="flex flex-col items-center gap-1">
                    <div className="h-3 w-10 bg-muted rounded"></div>
                    <div className="h-6 w-8 bg-muted rounded"></div>
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
