import { useSearchParams } from "react-router";
import ReactECharts from 'echarts-for-react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus } from "lucide-react";
import { useState } from "react";

export default function VideoCompare() {
    const [searchParams] = useSearchParams();
    const id = searchParams.get("id");
    const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);

    const handleAIAnalysis = () => {
        // Mock API call
        setAiAnalysis("**AI Analysis Result:**\n\n- **Video B** shows a more stable approach.\n- **Video A** has a higher initial impact force.\n- Suggestion: Reduce speed at entry.");
    };

    const chartOption = {
        title: { text: 'Speed Comparison' },
        tooltip: { trigger: 'axis' },
        legend: { data: ['My Video', 'Model Video'] },
        xAxis: { type: 'category', data: ['0s', '1s', '2s', '3s', '4s', '5s'] },
        yAxis: { type: 'value' },
        series: [
            { name: 'My Video', type: 'line', data: [0, 5, 12, 18, 15, 10] },
            { name: 'Model Video', type: 'line', data: [0, 6, 14, 20, 18, 12] }
        ]
    };

    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-100px)]">
            {/* Left: Video Area */}
            <div className="flex flex-col gap-4 h-full">
                <Card className="flex-1">
                    <CardHeader className="py-2">
                        <CardTitle className="text-sm">My Video {id ? `(ID: ${id})` : ""}</CardTitle>
                    </CardHeader>
                    <CardContent className="h-full min-h-[200px] bg-muted flex items-center justify-center p-0">
                        {id ? (
                            <span className="text-muted-foreground">Video A Player</span>
                        ) : (
                             <div className="flex flex-col items-center gap-2 text-muted-foreground cursor-pointer hover:text-foreground">
                                <Plus className="h-10 w-10" />
                                <span>Select from Library</span>
                             </div>
                        )}
                    </CardContent>
                </Card>
                <Card className="flex-1">
                    <CardHeader className="py-2">
                        <CardTitle className="text-sm">Model Video</CardTitle>
                    </CardHeader>
                    <CardContent className="h-full min-h-[200px] bg-muted flex items-center justify-center p-0">
                        <span className="text-muted-foreground">Video B Player</span>
                    </CardContent>
                </Card>
            </div>

            {/* Right: Data Area */}
            <div className="flex flex-col gap-4 h-full">
                <Card className="flex-1">
                    <CardHeader>
                        <CardTitle>Data Comparison</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ReactECharts option={chartOption} style={{ height: '100%', minHeight: '250px', width: '100%' }} />
                    </CardContent>
                </Card>
                <Card className="flex-1">
                    <CardHeader>
                        <CardTitle>AI Deep Analysis</CardTitle>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4">
                        {!aiAnalysis ? (
                            <div className="flex flex-col items-center justify-center h-full gap-4">
                                <p className="text-muted-foreground text-sm text-center">
                                    Click the button below to generate a professional comparison report using DeepSeek AI.
                                </p>
                                <Button onClick={handleAIAnalysis}>Trigger AI Analysis</Button>
                            </div>
                        ) : (
                            <div className="prose dark:prose-invert text-sm">
                                <div dangerouslySetInnerHTML={{ __html: aiAnalysis.replace(/\n/g, '<br/>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
