import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { useMeasure } from "react-use";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";

import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { analyzeVideoApiVideosAnalysisPost, getAnalysisApiVideosAnalysisGet } from "@/APIs";
import type { VideoDetailResponse, AnalysisResultResponse } from "@/APIs/types.gen";
import { InfoIcon, Maximize2 } from "lucide-react";
import { isNil } from "@/utils";
import VideoPlayCard from "@/components/video-play-card";
import SpeedCurveChart, { type SpeedCurveChartData } from "@/components/speed-curve-chart";
import { useModal } from "@/lib/react-modal-store";

import VideoGridSkeleton from "@/components/video-grid-skeleton";

export default function VideoAnalysis() {
    const [searchParams] = useSearchParams();
    const id = searchParams.get("id") ?? "";
    const navigate = useNavigate();
    const openModal = useModal();
    const queryClient = useQueryClient();

    const [curveContainerRef, { height: curveContainerHeight }] = useMeasure<HTMLDivElement>();

    const [analyzeError, setAnalyzeError] = useState<string | null>(null);
    const analyzeMutation = useMutation({
        mutationFn: async (videoId: string) => {
            const { data, error: apiError } = await analyzeVideoApiVideosAnalysisPost({
                query: { id: videoId },
            });

            if (apiError) throw new Error("分析失败，请重试");
            if (data && data.code >= 300) throw new Error(data.err_msg || "分析失败");

            return data;
        },
        onSuccess: async (_data, videoId) => {
            setAnalyzeError(null);
            await queryClient.invalidateQueries({ queryKey: ["analysis", videoId] });
            await queryClient.refetchQueries({ queryKey: ["analysis", videoId] });
        },
        onError: (err) => {
            setAnalyzeError(err instanceof Error ? err.message : "发生未知错误，请重试");
        },
    });

    const analysisQuery = useQuery({
        queryKey: ["analysis", id],
        queryFn: async () => getAnalysisApiVideosAnalysisGet({ query: { id }, throwOnError: true }),
        enabled: Boolean(id),
        staleTime: 30_000,
    });

    if (id && analysisQuery.isLoading) return <VideoGridSkeleton />;

    const response = analysisQuery.data?.data;
    const video = (response?.data?.video ?? {}) as VideoDetailResponse;
    const analysisSource = response?.data?.analysis ?? null;
    const analysis = (analysisSource ?? {}) as AnalysisResultResponse;
    const markedVideo = { ...video, url: analysis.marked_url || "" } as VideoDetailResponse;

    const chartHeight = Math.max(curveContainerHeight * 0.5, 240);

    const coreMetrics = [
        {
            key: 1,
            name: "时间区间",
            value: isNil(analysis.start_time) || isNil(analysis.end_time)
                ? "-"
                : `[${analysis.start_time!.toFixed(2)}s, ${analysis.end_time!.toFixed(2)}s]`,
            tip: "基于分析的视频片段，从刺入开始到结束的速度计算范围，单位：秒",
        },
        {
            key: 2,
            name: "初始速度",
            value: isNil(analysis.init_speed) ? "-" : `${analysis.init_speed} mm/s`,
            tip: "基于时间区间内的前几个速度点采样，单位：毫米/秒",
        },
        {
            key: 3,
            name: "平均速度",
            value: isNil(analysis.avg_speed) ? "-" : `${analysis.avg_speed} mm/s`,
        },
    ];

    const curveDataArray: SpeedCurveChartData = Array.isArray(analysis.curve_data)
        ? (analysis.curve_data as SpeedCurveChartData)
        : [];

    const hasAnalysisResult = Boolean(
        analysisSource &&
            (analysisSource.marked_url ||
                analysisSource.processed_at ||
                (Array.isArray(analysisSource.curve_data) && analysisSource.curve_data.length > 0)),
    );
    const showAnalyzeSkeleton = analyzeMutation.isPending;

    return (
        <div className="flex flex-row gap-6 h-[calc(100vh-100px)]">
            <div className="flex flex-col gap-4 h-full min-h-0">
                <VideoPlayCard title="原视频" url={video.url} isPending={showAnalyzeSkeleton} />
                <VideoPlayCard title="标记视频" url={markedVideo.url || ""} isPending={showAnalyzeSkeleton}/>
            </div>

            <div ref={curveContainerRef} className="flex-1 flex flex-col gap-4 h-full overflow-auto">
                <Card className="flex-1">
                    <CardHeader>
                        <CardTitle>速度曲线</CardTitle>
                        <CardAction>
                            <Tooltip>
                                <TooltipTrigger asChild>
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="icon"
                                        disabled={showAnalyzeSkeleton || curveDataArray.length === 0}
                                        onClick={() =>
                                            openModal("SpeedChartModal", {
                                                title: "速度曲线",
                                                curveData: curveDataArray,
                                            })
                                        }
                                    >
                                        <Maximize2 className="size-4" />
                                        <span className="sr-only">全屏查看</span>
                                    </Button>
                                </TooltipTrigger>
                                <TooltipContent side="top" align="end">
                                    全屏查看
                                </TooltipContent>
                            </Tooltip>
                        </CardAction>
                    </CardHeader>
                    <CardContent className="h-full">
                        {showAnalyzeSkeleton ? (
                            <div className="bg-muted rounded-md animate-pulse" style={{ height: chartHeight }} />
                        ) : (
                            <SpeedCurveChart curveData={curveDataArray} style={{ height: chartHeight }} />
                        )}
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
                                                    disabled={showAnalyzeSkeleton}
                                                    className="inline-flex items-center justify-center rounded-sm text-muted-foreground/70 hover:text-muted-foreground cursor-help disabled:opacity-50 disabled:pointer-events-none disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
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
                        {analysisQuery.isError ? (
                            <div className="space-y-2">
                                <div className="text-sm text-destructive font-medium">
                                    分析数据加载失败：{String(analysisQuery.error)}
                                </div>
                                <Button type="button" variant="outline" onClick={() => analysisQuery.refetch()}>
                                    重试
                                </Button>
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
                                disabled={analyzeMutation.isPending || !id}
                                onClick={() => {
                                    if (!id) return;
                                    setAnalyzeError(null);
                                    analyzeMutation.mutate(id);
                                }}
                            >
                                {analyzeMutation.isPending ? "分析中..." : hasAnalysisResult ? "重新分析视频" : "分析视频"}
                            </Button>
                            <Button
                                className="shrink-0"
                                variant="outline"
                                disabled={showAnalyzeSkeleton || !id}
                                onClick={() => navigate(`/video/compare?id=${id}`)}
                            >
                                去比较
                            </Button>
                        </div>
                    </div>
                </Card>
            </div>
        </div>
    );
}
