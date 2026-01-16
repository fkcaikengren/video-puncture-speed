import { useState } from "react";
import { useSearchParams } from "react-router";
import { useQuery } from "@tanstack/react-query";
import { useMeasure } from "react-use";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalysisApiVideosAnalysisGet } from "@/APIs";
import type { VideoDetailResponse, AnalysisResultResponse } from "@/APIs/types.gen";
import VideoPlayCard from "@/components/video-play-card";
import VideoGridSkeleton from "@/components/video-grid-skeleton";
import type { SpeedCurveChartData } from "@/components/speed-curve-chart";
import SpeedMultiCurveChart from "@/components/speed-multi-curve-chart";
import { useModal } from "@/lib/react-modal-store";

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
        <VideoPlayCard title={`A视频 - ${videoA.title}`} url={analysisA.marked_url || ""} supportChildren>
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

        <VideoPlayCard title={`B视频 - ${videoB.title}`} url={analysisB.marked_url || ""} supportChildren>
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
        <Card className="flex-1">
          <CardHeader>
            <CardTitle>A/B速度曲线</CardTitle>
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
            <CardTitle>AI 深度分析</CardTitle>
          </CardHeader>
	          <CardContent className="flex flex-col gap-4 h-full">
	            {!aiAnalysis ? (
	              <div className="flex flex-col items-center justify-center h-full gap-4">
	                <p className="text-muted-foreground text-sm text-center">
	                  点击按钮生成对比报告（当前为示例文案）。
	                </p>
	                <Button onClick={handleAIAnalysis} disabled={!aid || !bid}>
	                  生成对比分析
	                </Button>
	              </div>
            ) : (
              <div className="prose dark:prose-invert text-sm">
                <div
                  dangerouslySetInnerHTML={{
                    __html: aiAnalysis
                      .replace(/\n/g, "<br/>")
                      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>"),
                  }}
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
