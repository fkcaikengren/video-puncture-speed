

export default function VideoGridSkeleton() {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-[calc(100vh-100px)] animate-pulse">
            <div className="flex flex-col gap-4 h-full overflow-y-auto">
                <div className="flex-1 bg-muted rounded-md" />
                <div className="flex-1 bg-muted rounded-md" />
            </div>
            <div className="flex flex-col gap-4 h-full">
                <div className="flex-1 bg-muted rounded-md" />
                <div className="h-[220px] bg-muted rounded-md" />
            </div>
        </div>
    );
}
