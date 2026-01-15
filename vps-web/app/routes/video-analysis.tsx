import { Suspense, use, useActionState, useState } from "react";
import { useLoaderData, useNavigate } from "react-router";
import ReactECharts from 'echarts-for-react';
import { useMeasure } from "react-use";
import { Button } from "@/components/ui/button";
import ReactPlayer from "react-player"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { analyzeVideoApiVideosAnalysisPost, getAnalysisApiVideosAnalysisGet } from "@/APIs";
import type { BaseResponseAnalysisResponse, VideoDetailResponse, AnalysisResultResponse } from "@/APIs/types.gen";
import { InfoIcon } from "lucide-react";
import { isNil } from '@/utils'

type AnalysisPromise = Promise<({
    data: BaseResponseAnalysisResponse;
    error: undefined;
} | {
    data: undefined;
    error: unknown;
})>;


interface CurveDataItem {
    t: number, //时间 (s)
    v: number, //速度（mm/s）
}

type CurveData = CurveDataItem[];

export async function clientLoader({ request }: { request: Request }) {
    const url = new URL(request.url);
    const id = url.searchParams.get("id") ?? "";

    const analysisPromise = getAnalysisApiVideosAnalysisGet({
        query: { id },
    }) as AnalysisPromise;

    return { id, analysisPromise };
}

export default function VideoAnalysis() {
    const { id, analysisPromise } = useLoaderData<typeof clientLoader>();

    return (
        <Suspense fallback={<VideoAnalysisSkeleton />} key={id || "no-id"}>
            <VideoAnalysisContent id={id} analysisPromise={analysisPromise} />
        </Suspense>
    );
}

function VideoAnalysisContent({
    id,
    analysisPromise,
}: {
    id: string;
    analysisPromise: AnalysisPromise;
}) {
    const navigate = useNavigate();
    const [analysisPromiseOverride, setAnalysisPromiseOverride] = useState<AnalysisPromise | null>(null);
    const result = use(analysisPromiseOverride ?? analysisPromise);

    const response = result.data;
    const video = response?.data?.video ?? {} as VideoDetailResponse;
    const analysis = response?.data?.analysis ?? {} as AnalysisResultResponse;
    const markedVideo = { ...video, url: analysis.marked_url || "" } as VideoDetailResponse;

    const [curveContainerRef, { height: curveContainerHeight }] = useMeasure<HTMLDivElement>();


        
    const coreMetrics = [
        {
            key:1, 
            name: "时间区间", 
            value: isNil(analysis.start_time) || isNil(analysis.end_time)
                ? "-"
                : `[${analysis.start_time!.toFixed(2)}s, ${analysis.end_time!.toFixed(2)}s]`, 
            tip: '基于分析的视频片段，从刺入开始到结束的速度计算范围，单位：秒' },
        {
            key:2, 
            name: "初始速度", 
            value: isNil(analysis.init_speed)  ? "-" : `${analysis.init_speed} mm/s` , 
            tip: '基于时间区间内的前几个速度点采样，单位：毫米/秒' },
        {
            key:3, 
            name: "平均速度", 
            value: isNil(analysis.avg_speed) ? "-" : `${analysis.avg_speed} mm/s` 
        },
    ]

    const curveDataArray: CurveData = Array.isArray(analysis.curve_data) ? (analysis.curve_data as CurveData) : [];
    const xAxisData =
        curveDataArray?.map((p, idx) => {
            if (!isNil(p.t)) {
                if (typeof p.t === "number") return `${p.t.toFixed(2)}`;
                if (typeof p.t === "string") return p.t;
            }
            return `${idx}s`;
        }) ?? ['0.00', '1.00', '2.00', '3.00', '4.00', '5.00', '6.00'];

    const ySeriesData =
        curveDataArray?.map((p, idx) => {
            if (!isNil(p.v)) {
                if (typeof p.v === "number") return p.v;
            }
            return idx === 0 ? 0 : idx * 3;
        }) ?? [0, 1, 2, 3, 4, 5, 6];

    const chartOption = {
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross',
                label: {
                    backgroundColor: '#6a7985'
                }
            }
        },
        xAxis: {
            type: 'category',
            name: '时间 (s)',
            boundaryGap: false,
            data: xAxisData
        },
        yAxis: {
            type: 'value',
            name: '速度 (mm/s)',
            min: 0,
            max: 12,
        },
        series: [
            {
                name: '速度曲线',
                type: 'line',
                smooth: true,
                // areaStyle: {}, 
                emphasis: {
                    focus: 'series'
                },
                data: ySeriesData
            }
        ]
    };

    const [analyzeError, runAnalyze, analyzePending] = useActionState<string | null, { id: string }>(
        async (_prev, payload) => {
            if (!payload.id) return "缺少视频 id";

            try {
                const { data, error: apiError } = await analyzeVideoApiVideosAnalysisPost({
                    query: { id: payload.id },
                });

                if (apiError) {
                    return "分析失败，请重试";
                }

                if (data && data.code >= 300) {
                    return data.err_msg || "分析失败";
                }

                setAnalysisPromiseOverride(
                    getAnalysisApiVideosAnalysisGet({
                        query: { id: payload.id },
                    }) as AnalysisPromise,
                );
                return null;
            } catch {
                return "发生未知错误，请重试";
            }
        },
        null,
    );

    return (
        <div className="flex flex-row gap-6 h-[calc(100vh-100px)]">
            {/* Left: Video Area */}
            <div className="flex flex-col gap-4 h-full min-h-0 ">
                <VideoCard title="原视频" video={video} />
                <VideoCard title="标记视频" video={markedVideo} />
            </div>

            {/* Right: Data Dashboard */}
            <div ref={curveContainerRef} className="flex-1 flex flex-col gap-4 h-full overflow-auto">
                <Card className="flex-1">
                     <CardHeader>
                        <CardTitle>速度曲线</CardTitle>
                    </CardHeader>
                    <CardContent className="h-full">
                        <ReactECharts option={chartOption} style={{ height: curveContainerHeight*0.5, width: '100%' }} />
                    </CardContent>
                </Card>
                
                <Card className="h-1/3">
                    <CardHeader>
                        <CardTitle>核心指标</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {coreMetrics.map((item) => (
                            <div key={item.key} className="flex flex-col">
                                <span className="text-muted-foreground text-xs flex items-center gap-1">
                                    {item.name}
                                    {typeof item.tip === "string" && item.tip ? (
                                        <Tooltip>
                                            <TooltipTrigger asChild>
                                                <button
                                                    type="button"
                                                    className="inline-flex items-center justify-center rounded-sm text-muted-foreground/70 hover:text-muted-foreground cursor-help focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
                                                >
                                                    <InfoIcon className="size-3.5" />
                                                    <span className="sr-only">提示</span>
                                                </button>
                                            </TooltipTrigger>
                                            <TooltipContent side="top" align="start" className="max-w-xs text-xs leading-relaxed">
                                                {item.tip}
                                            </TooltipContent>
                                        </Tooltip>
                                    ) : null}
                                </span>
                                <span className="text-md font-bold">{item.value}</span>
                            </div>
                        ))}

                    </CardContent>
                     <div className="p-4 pt-0">
                        {result.error ? (
                            <div className="text-sm text-red-500 font-medium">
                                Failed to load analysis data.
                            </div>
                        ) : null}
                        {analyzeError ? (
                            <div className="text-sm text-red-500 font-medium mb-2">
                                {analyzeError}
                            </div>
                        ) : null}
                        <div className="flex gap-2">
                            <Button
                                className="flex-1"
                                disabled={analyzePending || !id}
                                onClick={() => runAnalyze({ id })}
                            >
                                {analyzePending ? "分析中..." : "分析视频"}
                            </Button>
                            <Button
                                className="shrink-0"
                                variant="outline"
                                disabled={!id}
                                onClick={() => navigate(`/video/compare?id=${id}`)}
                            >
                                去比较
                            </Button>
                        </div>
                     </div>
                </Card>
            </div>
        </div>
    )
}


function VideoCard({
    title,
    video
}:{
    title: string,
    video: VideoDetailResponse
}){
    const [containerRef, { height: containerHeight }] = useMeasure<HTMLDivElement>();


    return (
        <Card 
            ref={containerRef} 
            className="py-0 overflow-hidden relative  bg-black flex items-center justify-center aspect-video lg:flex-1"
            style={{
                width: containerHeight * (16 / 9),
            }}
        >
            <div className="absolute top-0 right-0 bg-black text-white text-center py-1 px-1 rounded-bl-md">
                {title}
            </div>
            <CardContent  className="px-0 h-full w-full">
                    <ReactPlayer
                        slot="media"
                        src={video.url || ''}
                        controls={true}
                        style={{
                            width: "100%",
                            height: "100%",
                            objectFit: "contain",
                        }}
                    ></ReactPlayer>
            </CardContent>
        </Card>
    )
}

function VideoAnalysisSkeleton() {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-100px)] animate-pulse">
            <div className="flex flex-col gap-4 h-full overflow-y-auto">
                <div className="h-[260px] bg-muted rounded-md" />
                <div className="h-[260px] bg-muted rounded-md" />
            </div>
            <div className="flex flex-col gap-4 h-full">
                <div className="flex-1 bg-muted rounded-md" />
                <div className="h-[220px] bg-muted rounded-md" />
            </div>
        </div>
    );
}
