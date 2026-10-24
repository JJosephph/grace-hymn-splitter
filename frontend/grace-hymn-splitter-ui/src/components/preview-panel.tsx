import {
  AlertCircle,
  CheckCircle2,
  FileImage,
  FolderOpen,
  LoaderCircle,
  Terminal,
} from "lucide-react"
import { AnimatePresence, motion } from "motion/react"

import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { useAppStore } from "@/store/app-store"
import { cn } from "@/lib/utils"

export function PreviewPanel() {
  const job = useAppStore((state) => state.job)
  const openPath = useAppStore((state) => state.openPath)
  const previews = job.result.previews || []

  return (
    <section className="flex h-full min-w-0 flex-col bg-muted/20">
      <div className="flex items-center justify-between border-b bg-background px-5 py-4">
        <div>
          <div className="text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
            预览
          </div>
          <h2 className="mt-1 text-base font-semibold tracking-tight">
            分段结果
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">
            {previews.length ? `已生成 ${previews.length} 张` : "还没有生成"}
          </span>
          <Button
            variant="outline"
            size="icon-sm"
            title="打开输出目录"
            disabled={!job.result.output_dir}
            onClick={() =>
              job.result.output_dir && openPath(job.result.output_dir)
            }
          >
            <FolderOpen />
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="space-y-5 p-5">
            <AnimatePresence initial={false}>
              {job.status === "running" && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  className="rounded-xl border bg-background p-4"
                >
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <LoaderCircle className="size-4 animate-spin text-primary" />
                    正在制作
                  </div>
                  <Progress value={job.progress} className="mt-3" />
                  <div className="mt-2 text-xs text-muted-foreground">
                    {job.message}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {job.status === "failed" && (
              <div className="flex gap-3 rounded-xl border border-destructive/25 bg-destructive/5 p-4 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <span>{job.error || "制作没有完成。"}</span>
              </div>
            )}

            {job.status === "completed" && !previews.length && (
              <div className="flex items-center gap-2 text-sm text-emerald-600">
                <CheckCircle2 className="size-4" />
                制作完成
              </div>
            )}

            {!previews.length && job.status !== "running" ? (
              <Empty className="min-h-72 border">
                <EmptyHeader>
                  <EmptyMedia variant="icon">
                    <FileImage />
                  </EmptyMedia>
                  <EmptyTitle>生成后在这里预览</EmptyTitle>
                </EmptyHeader>
              </Empty>
            ) : (
              <motion.div
                layout
                className="grid grid-cols-2 gap-3 xl:grid-cols-2"
              >
                {previews.map((preview, index) => (
                  <motion.button
                    layout
                    key={preview.path}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.04 }}
                    type="button"
                    onClick={() => openPath(preview.path)}
                    className="group overflow-hidden rounded-xl border bg-background text-left transition-shadow hover:shadow-sm"
                  >
                    <div className="flex aspect-[4/3] items-center justify-center overflow-hidden bg-muted">
                      <img
                        src={preview.url}
                        alt={preview.name}
                        className="h-full w-full object-contain transition-transform duration-300 group-hover:scale-[1.02]"
                      />
                    </div>
                    <div className="truncate border-t px-3 py-2 text-xs text-muted-foreground">
                      {preview.name}
                    </div>
                  </motion.button>
                ))}
              </motion.div>
            )}

            <Separator />

            <div>
              <div className="mb-3 flex items-center gap-2 text-xs font-medium tracking-[0.12em] text-muted-foreground uppercase">
                <Terminal className="size-3.5" />
                制作记录
              </div>
              <div className="space-y-2">
                {(job.logs.length
                  ? job.logs
                  : [
                      {
                        time: "",
                        title: "准备就绪",
                        message: "上传歌谱后即可开始制作。",
                      },
                    ]
                ).map((line, index) => (
                  <div
                    key={`${line.time}-${index}`}
                    className={cn(
                      "flex gap-2 text-xs leading-5",
                      line.title === "出错了" && "text-destructive",
                    )}
                  >
                    <span className="mt-2 size-1.5 shrink-0 rounded-full bg-muted-foreground/40" />
                    <span className="min-w-0 text-muted-foreground">
                      {line.title} · {line.message}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>
    </section>
  )
}
