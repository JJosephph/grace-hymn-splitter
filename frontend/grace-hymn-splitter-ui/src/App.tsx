import { useEffect } from "react"
import { FolderOpen, Play } from "lucide-react"

import { AppSidebar } from "@/components/app-sidebar"
import { OptionsPanel } from "@/components/options-panel"
import { PreviewPanel } from "@/components/preview-panel"
import { SongFields } from "@/components/song-fields"
import { UploadPanel } from "@/components/upload-panel"
import { Button } from "@/components/ui/button"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useAppStore } from "@/store/app-store"
import { cn } from "@/lib/utils"

function StatusPill() {
  const job = useAppStore((state) => state.job)
  const labels = {
    idle: "等待制作",
    running: "制作中",
    completed: "已完成",
    failed: "需要检查",
  }
  return (
    <span
      className={cn(
        "inline-flex h-7 items-center rounded-full border px-2.5 text-xs font-medium",
        job.status === "running" && "border-amber-300 bg-amber-50 text-amber-700",
        job.status === "completed" &&
          "border-emerald-300 bg-emerald-50 text-emerald-700",
        job.status === "failed" &&
          "border-destructive/30 bg-destructive/5 text-destructive",
      )}
    >
      {labels[job.status]}
    </span>
  )
}

export function App() {
  const initialize = useAppStore((state) => state.initialize)
  const pollJob = useAppStore((state) => state.pollJob)
  const image = useAppStore((state) => state.image)
  const job = useAppStore((state) => state.job)
  const outputRoot = useAppStore((state) => state.outputRoot)
  const startBuild = useAppStore((state) => state.startBuild)
  const openPath = useAppStore((state) => state.openPath)

  useEffect(() => {
    void initialize()
    const timer = window.setInterval(() => void pollJob(), 700)
    return () => window.clearInterval(timer)
  }, [initialize, pollJob])

  const canBuild = Boolean(image && outputRoot.trim()) && job.status !== "running"

  return (
    <TooltipProvider>
      <div className="flex h-svh min-h-0 overflow-hidden bg-background text-foreground">
        <AppSidebar />

        <ResizablePanelGroup orientation="horizontal" className="min-w-0 flex-1">
          <ResizablePanel defaultSize={58} minSize={44}>
            <main className="h-full min-w-0 overflow-y-auto">
              <header className="sticky top-0 z-10 flex items-center justify-between border-b bg-background/95 px-8 py-5 backdrop-blur">
                <div>
                  <div className="text-[11px] font-medium tracking-[0.14em] text-muted-foreground uppercase">
                    恩典歌谱转换PPT大图
                  </div>
                  <h1 className="mt-1 text-2xl font-semibold tracking-tight">
                    把简谱拆成适合投影的分段大图
                  </h1>
                </div>
                <div className="flex items-center gap-2">
                  <StatusPill />
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() =>
                          job.result.output_dir &&
                          openPath(job.result.output_dir)
                        }
                        disabled={!job.result.output_dir}
                      >
                        <FolderOpen />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>打开输出目录</TooltipContent>
                  </Tooltip>
                </div>
              </header>

              <div className="mx-auto flex w-full max-w-3xl flex-col gap-9 px-8 pt-8 pb-10">
                <UploadPanel />
                <SongFields />
                <OptionsPanel />

                <div className="flex items-center gap-3 pt-1">
                  <Button
                    size="lg"
                    className="min-w-32"
                    disabled={!canBuild}
                    onClick={startBuild}
                  >
                    <Play />
                    开始制作
                  </Button>
                  <Button
                    variant="outline"
                    size="lg"
                    disabled={!job.result.output_dir}
                    onClick={() =>
                      job.result.output_dir &&
                      openPath(job.result.output_dir)
                    }
                  >
                    <FolderOpen />
                    打开输出目录
                  </Button>
                </div>
              </div>
            </main>
          </ResizablePanel>

          <ResizableHandle withHandle />

          <ResizablePanel defaultSize={42} minSize={34}>
            <PreviewPanel />
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>
    </TooltipProvider>
  )
}

export default App
