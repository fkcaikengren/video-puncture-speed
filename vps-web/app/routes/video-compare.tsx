import { useState } from "react";
import { useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { useMeasure } from "react-use";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle,CardAction } from "@/components/ui/card";
import { getAnalysisApiVideosAnalysisGet } from "@/APIs";
import type { VideoDetailResponse, AnalysisResultResponse } from "@/APIs/types.gen";
import VideoPlayCard from "@/components/video-play-card";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { SpeedCurveChartData } from "@/components/speed-curve-chart";
import SpeedMultiCurveChart from "@/components/speed-multi-curve-chart";
import { useModal } from "@/lib/react-modal-store";
import { Maximize2 } from "lucide-react";
import { isNil } from "@/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function VideoCompare() {
  const [searchParams, setSearchParams] = useSearchParams();
  const aid = searchParams.get("aid") ?? "";
  const bid = searchParams.get("bid") ?? "";

  const openModal = useModal();
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
  const [curveContainerRef, { height: curveContainerHeight }] = useMeasure<HTMLDivElement>();

  const myQuery = useQuery({
    queryKey: ["analysis", aid],
    queryFn: async () => getAnalysisApiVideosAnalysisGet({ query: { id: aid }, throwOnError: true }),
    enabled: Boolean(aid),
    staleTime: 30_000,
  });

  const comparedQuery = useQuery({
    queryKey: ["analysis", bid],
    queryFn: async () => getAnalysisApiVideosAnalysisGet({ query: { id: bid }, throwOnError: true }),
    enabled: Boolean(bid),
    staleTime: 30_000,
  });


  const myResponse = myQuery.data?.data;
  const comparedResponse = comparedQuery.data?.data;

  const videoA = (myResponse?.data?.video || {}) as VideoDetailResponse;
  const videoB = (comparedResponse?.data?.video || {}) as VideoDetailResponse;

  const analysisA = myResponse?.data?.analysis ?? ({} as AnalysisResultResponse);
  const analysisB = comparedResponse?.data?.analysis ?? ({} as AnalysisResultResponse);

  const curveDataA: SpeedCurveChartData = Array.isArray(analysisA.curve_data)
    ? (analysisA.curve_data as SpeedCurveChartData)
    : [];
  const curveDataB: SpeedCurveChartData = Array.isArray(analysisB.curve_data)
    ? (analysisB.curve_data as SpeedCurveChartData)
    : [];

  const timeRangeA =
    isNil(analysisA.start_time) || isNil(analysisA.end_time)
      ? "-"
      : `[${analysisA.start_time!.toFixed(2)}s, ${analysisA.end_time!.toFixed(2)}s]`;

  const timeRangeB =
    isNil(analysisB.start_time) || isNil(analysisB.end_time)
      ? "-"
      : `[${analysisB.start_time!.toFixed(2)}s, ${analysisB.end_time!.toFixed(2)}s]`;

  const initSpeedA = isNil(analysisA.init_speed) ? "-" : `${analysisA.init_speed} mm/s`;
  const initSpeedB = isNil(analysisB.init_speed) ? "-" : `${analysisB.init_speed} mm/s`;

  const avgSpeedA = isNil(analysisA.avg_speed) ? "-" : `${analysisA.avg_speed} mm/s`;
  const avgSpeedB = isNil(analysisB.avg_speed) ? "-" : `${analysisB.avg_speed} mm/s`;

  const formatSigned = (value: number, digits = 2) => {
    const fixed = value.toFixed(digits);
    return value > 0 ? `+${fixed}` : fixed;
  };

  const durationA =
    !isNil(analysisA.start_time) && !isNil(analysisA.end_time)
      ? analysisA.end_time! - analysisA.start_time!
      : undefined;

  const durationB =
    !isNil(analysisB.start_time) && !isNil(analysisB.end_time)
      ? analysisB.end_time! - analysisB.start_time!
      : undefined;

  const deltaTimeRange =
    isNil(durationA) || isNil(durationB)
      ? "-"
      : `${formatSigned(durationA! - durationB!)}s`;
  const deltaInitSpeed =
    isNil(analysisA.init_speed) || isNil(analysisB.init_speed)
      ? "-"
      : `${formatSigned(analysisA.init_speed! - analysisB.init_speed!)} mm/s`;

  const deltaAvgSpeed =
    isNil(analysisA.avg_speed) || isNil(analysisB.avg_speed)
      ? "-"
      : `${formatSigned(analysisA.avg_speed! - analysisB.avg_speed!)} mm/s`;

  const updateSearchParams = ({ aid: nextAid, bid: nextBid }: { aid?: string; bid?: string }) => {
    setSearchParams((prev) => {
      const nextSearchParams = new URLSearchParams(prev);
      if (typeof nextAid === "string") {
        if (nextAid) nextSearchParams.set("aid", nextAid);
        else nextSearchParams.delete("aid");
        nextSearchParams.delete("id");
      }
      if (typeof nextBid === "string") {
        if (nextBid) nextSearchParams.set("bid", nextBid);
        else nextSearchParams.delete("bid");
      }
      return nextSearchParams;
    });
  };

  const openMyVideoSelectModal = () =>
    openModal("VideoSelectModal", {
      title: "选择A视频",
      disabledVideoIds: bid ? [bid] : undefined,
      onSelectVideoId: (videoId: string) => {
        if (!videoId) return;
        setAiAnalysis(null);
        updateSearchParams({ aid: videoId });
      },
    });

  const openComparedVideoSelectModal = () =>
    openModal("VideoSelectModal", {
      title: "选择B视频",
      disabledVideoIds: aid ? [aid] : undefined,
      onSelectVideoId: (videoId: string) => {
        if (!videoId) return;
        setAiAnalysis(null);
        updateSearchParams({ bid: videoId });
      },
    });

  const handleAIAnalysis = () => {
    setAiAnalysis(
      "**AI Analysis Result:**\n\n- **Video B** shows a more stable approach.\n- **Video A** has a higher initial impact force.\n- Suggestion: Reduce speed at entry.",
    );
  };

  return (
    <div className="flex flex-row gap-6 h-[calc(100vh-100px)]">
      <div className="flex flex-col gap-4 h-full min-h-0">
        <VideoPlayCard title={videoA.title ? `A视频 - ${videoA.title}` : 'A视频'} url={analysisA.marked_url || ""} supportChildren>
          {!analysisA.marked_url ? (
            <div className="absolute left-0 top-0 right-0 bottom-0 bg-white flex items-center justify-center">
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer"
                size="sm"
                onClick={openMyVideoSelectModal}
              >
                选择A视频
              </Button>
            </div>
          ) : (
            <Button
              type="button"
              className="absolute left-1 top-1 z-10 bg-black/60 text-white hover:bg-black cursor-pointer"
              size="sm"
              onClick={openMyVideoSelectModal}
            >
              更换视频
            </Button>
          )}
        </VideoPlayCard>

        <VideoPlayCard title={videoB.title ? `B视频 - ${videoB.title}` : 'B视频'} url={analysisB.marked_url || ""} supportChildren>
          {!analysisB.marked_url ? (
            <div className="absolute left-0 top-0 right-0 bottom-0 bg-white flex items-center justify-center">
              <Button
                type="button"
                variant="outline"
                className="cursor-pointer"
                size="sm"
                onClick={openComparedVideoSelectModal}
              >
                选择B视频
              </Button>
            </div>
          ) : (
            <Button
              type="button"
              className="absolute left-1 top-1 z-20 bg-black/60 text-white hover:bg-black cursor-pointer"
              size="sm"
              onClick={openComparedVideoSelectModal}
            >
              更换视频
            </Button>
          )}
        </VideoPlayCard>
      </div>

      <div ref={curveContainerRef} className="flex-1 flex flex-col gap-4 h-full overflow-auto">
        {(myQuery.isError || comparedQuery.isError) && (
          <div className="space-y-2">
            {myQuery.isError && (
              <div className="text-sm text-destructive">A视频加载失败：{String(myQuery.error)}</div>
            )}
            {comparedQuery.isError && (
              <div className="text-sm text-destructive">B视频加载失败：{String(comparedQuery.error)}</div>
            )}
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                if (myQuery.isError) myQuery.refetch();
                if (comparedQuery.isError) comparedQuery.refetch();
              }}
            >
              重试
            </Button>
          </div>
        )}
        <Card className="flex-1 gap-0">
          <CardHeader>
            <CardTitle>A/B速度曲线</CardTitle>
            <CardAction>
              <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                          openModal("SpeedMultiChartModal", {
                              title: "A/B速度曲线",
                              curveData1: curveDataA,
                              curveData2: curveDataB,
                              name1: "A视频",
                              name2: "B视频",
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
            <SpeedMultiCurveChart
              curveData1={curveDataA}
              curveData2={curveDataB}
              name1="A视频"
              name2="B视频"
              style={{ height: curveContainerHeight * 0.5 }}
            />
          </CardContent>
        </Card>

        <Card className="h-1/3">
          <CardHeader>
            <CardTitle>A/B数据对比</CardTitle>
          </CardHeader>
	        <CardContent className="h-full flex flex-col justify-center">
          <div className="border rounded-md w-full max-w-[800px] mx-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-primary/30">
                  <TableHead className="w-[160px] text-center">视频</TableHead>
                  <TableHead className="text-center">时间区间</TableHead>
                  <TableHead className="text-center">初始速度</TableHead>
                  <TableHead className="text-center">平均速度</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TableRow>
                  <TableCell className="font-medium text-center bg-muted/50">A视频</TableCell>
                  <TableCell className="text-center">{timeRangeA}</TableCell>
                  <TableCell className="text-center">{initSpeedA}</TableCell>
                  <TableCell className="text-center">{avgSpeedA}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium text-center bg-muted/50">B视频</TableCell>
                  <TableCell className="text-center">{timeRangeB}</TableCell>
                  <TableCell className="text-center">{initSpeedB}</TableCell>
                  <TableCell className="text-center">{avgSpeedB}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell className="font-medium text-center bg-muted/50">
                    A比B
                  </TableCell>
                  <TableCell className="text-center">{deltaTimeRange}</TableCell>
                  <TableCell className="text-center">{deltaInitSpeed}</TableCell>
                  <TableCell className="text-center">{deltaAvgSpeed}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </div>
        </CardContent>
        </Card>
      </div>
    </div>
  );
}
