import { useSearchParams, useNavigate } from "react-router";
import ReactECharts from 'echarts-for-react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function VideoAnalysis() {
    const [searchParams] = useSearchParams();
    const id = searchParams.get("id");
    const navigate = useNavigate();

    // Mock Data
    const analysisData = {
        interval: "[00:02.500, 00:05.100]",
        initialSpeed: "12.5 m/s",
        avgSpeed: "15.2 m/s",
    };

    const chartOption = {
        title: {
            text: 'Speed vs Time'
        },
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
            boundaryGap: false,
            data: ['0s', '1s', '2s', '3s', '4s', '5s', '6s']
        },
        yAxis: {
            type: 'value',
            name: 'Speed (m/s)'
        },
        series: [
            {
                name: 'Speed',
                type: 'line',
                smooth: true,
                areaStyle: {},
                emphasis: {
                    focus: 'series'
                },
                data: [0, 5, 12, 18, 22, 15, 10]
            }
        ]
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-100px)]">
            {/* Left: Video Area */}
            <div className="flex flex-col gap-4 h-full overflow-y-auto">
                <Card>
                    <CardHeader className="py-2">
                        <CardTitle className="text-sm">Original Video</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 aspect-video bg-black flex items-center justify-center">
                         <span className="text-white">Original Video Player (ID: {id})</span>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="py-2">
                        <CardTitle className="text-sm">Marked Video</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 aspect-video bg-black flex items-center justify-center relative">
                        <span className="text-white">Marked Video Player</span>
                        <div className="absolute top-2 right-2 bg-black/50 text-white p-1 text-xs rounded">Speed: 12 m/s</div>
                    </CardContent>
                </Card>
            </div>

            {/* Right: Data Dashboard */}
            <div className="flex flex-col gap-4 h-full">
                <Card className="flex-1">
                     <CardHeader>
                        <CardTitle>Speed Curve</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ReactECharts option={chartOption} style={{ height: '300px', width: '100%' }} />
                    </CardContent>
                </Card>
                
                <Card>
                    <CardHeader>
                        <CardTitle>Core Metrics</CardTitle>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="flex flex-col">
                            <span className="text-muted-foreground text-xs">Interval</span>
                            <span className="text-lg font-bold">{analysisData.interval}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-muted-foreground text-xs">Initial Speed</span>
                            <span className="text-lg font-bold">{analysisData.initialSpeed}</span>
                        </div>
                        <div className="flex flex-col">
                            <span className="text-muted-foreground text-xs">Avg Speed</span>
                            <span className="text-lg font-bold">{analysisData.avgSpeed}</span>
                        </div>
                    </CardContent>
                     <div className="p-4 pt-0">
                        <Button className="w-full" onClick={() => navigate(`/video/compare?id=${id}`)}>
                            Compare with Standard
                        </Button>
                     </div>
                </Card>
            </div>
        </div>
    )
}
