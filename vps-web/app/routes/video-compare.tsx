import { Suspense, use, useState } from "react";
import { useLoaderData, useSearchParams } from "react-router";
import { useMeasure } from "react-use";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getAnalysisApiVideosAnalysisGet } from "@/APIs";
import type { VideoDetailResponse, BaseResponseAnalysisResponse, AnalysisResultResponse } from "@/APIs/types.gen";
import VideoPlayCard from "@/components/video-play-card";
import VideoGridSkeleton from "@/components/video-grid-skeleton";
import type { SpeedCurveChartData } from "@/components/speed-curve-chart";
import SpeedMultiCurveChart from "@/components/speed-multi-curve-chart";
import { useModal } from "@/lib/react-modal-store";

type AnalysisPromise = Promise<
  | {
      data: BaseResponseAnalysisResponse;
      error: undefined;
    }
  | {
      data: undefined;
      error: unknown;
    }
>;

export async function clientLoader({ request }: { request: Request }) {
  const url = new URL(request.url);
  const aid = url.searchParams.get("aid") ?? "";
  const bid = url.searchParams.get("bid") ?? "";

  const myAnalysisPromise = aid
    ? (getAnalysisApiVideosAnalysisGet({ query: { id: aid } }) as AnalysisPromise)
    : null;

  const comparedAnalysisPromise = bid
    ? (getAnalysisApiVideosAnalysisGet({
        query: { id: bid },
      }) as AnalysisPromise)
    : null;

  return { aid, bid, myAnalysisPromise, comparedAnalysisPromise };
}

export default function VideoCompare() {
  const { aid, bid, myAnalysisPromise, comparedAnalysisPromise } =
    useLoaderData<typeof clientLoader>();

  return (
    <Suspense
      fallback={<VideoGridSkeleton />}
      key={`${aid || "no-aid"}-${bid || "no-bid"}`}
    >
      <VideoCompareContent
        aid={aid}
        bid={bid}
        myAnalysisPromise={myAnalysisPromise}
        comparedAnalysisPromise={comparedAnalysisPromise}
      />
    </Suspense>
  );
}

function VideoCompareContent({
  aid,
  bid,
  myAnalysisPromise,
  comparedAnalysisPromise,
}: {
  aid: string;
  bid: string;
  myAnalysisPromise: AnalysisPromise | null;
  comparedAnalysisPromise: AnalysisPromise | null;
}) {
  const [searchParams, setSearchParams] = useSearchParams();
  const openModal = useModal();
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
  const [curveContainerRef, { height: curveContainerHeight }] = useMeasure<HTMLDivElement>();


  const myResult = myAnalysisPromise ? use(myAnalysisPromise) : null;
  const comparedResult = comparedAnalysisPromise ? use(comparedAnalysisPromise) : null;

  const myResponse = myResult?.data;
  const comparedResponse = comparedResult?.data;

  const videoA = (myResponse?.data?.video || {}) as VideoDetailResponse;
  const videoB = (comparedResponse?.data?.video || {}) as VideoDetailResponse;

  const myAnalysis = myResponse?.data?.analysis ?? ({} as AnalysisResultResponse);
  const comparedAnalysis = comparedResponse?.data?.analysis ?? ({} as AnalysisResultResponse);

  const curveData1: SpeedCurveChartData = Array.isArray(myAnalysis.curve_data)
    ? (myAnalysis.curve_data as SpeedCurveChartData)
    : [];
  const curveData2: SpeedCurveChartData = Array.isArray(comparedAnalysis.curve_data)
    ? (comparedAnalysis.curve_data as SpeedCurveChartData)
    : [];

  const updateSearchParams = (patch: { aid?: string; bid?: string }) => {
    const next = new URLSearchParams(searchParams);
    const nextAid = patch.aid ?? aid;
    const nextBid = patch.bid ?? bid;

    next.delete("id");
    next.delete("comparedId");
    next.delete("compareId");

    if (nextAid) next.set("aid", nextAid);
    else next.delete("aid");

    if (nextBid) next.set("bid", nextBid);
    else next.delete("bid");

    setSearchParams(next);
  };

  const openMyVideoSelectModal = () =>
    openModal("VideoSelectModal", {
      title: "选择对比视频",
      disabledVideoIds: bid ? [bid] : undefined,
      onSelectVideoId: (videoId: string) => {
        if (!videoId) return;
        setAiAnalysis(null);
        updateSearchParams({ aid: videoId });
      },
    });

  const openComparedVideoSelectModal = () =>
    openModal("VideoSelectModal", {
      title: "选择对比视频",
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
        <VideoPlayCard title="A视频" url={videoA.url || ""} supportChildren>
          {!videoA.url ? (
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
              className="absolute left-1 top-1 bg-black text-white hover:bg-black/90 cursor-pointer"
              size="sm"
              onClick={openMyVideoSelectModal}
            >
              更换视频
            </Button>
          )}
        </VideoPlayCard>

        <VideoPlayCard title="B视频" url={videoB.url || ""} supportChildren>
          {!videoB.url ? (
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
              className="absolute left-1 top-1 bg-black text-white hover:bg-black/90 cursor-pointer"
              size="sm"
              onClick={openComparedVideoSelectModal}
            >
              更换视频
            </Button>
          )}
        </VideoPlayCard>
      </div>

      <div ref={curveContainerRef} className="flex-1 flex flex-col gap-4 h-full overflow-auto">
        <Card className="flex-1">
          <CardHeader>
            <CardTitle>速度曲线</CardTitle>
          </CardHeader>
          <CardContent className="h-full">
            <SpeedMultiCurveChart
              curveData1={curveData1}
              curveData2={curveData2}
              name1="我的视频"
              name2="对比视频"
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
