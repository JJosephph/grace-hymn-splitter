import { FolderOpen } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Field,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { useAppStore } from "@/store/app-store"

export function SongFields() {
  const songNumber = useAppStore((state) => state.songNumber)
  const songTitle = useAppStore((state) => state.songTitle)
  const outputRoot = useAppStore((state) => state.outputRoot)
  const setSongNumber = useAppStore((state) => state.setSongNumber)
  const setSongTitle = useAppStore((state) => state.setSongTitle)
  const setOutputRoot = useAppStore((state) => state.setOutputRoot)
  const chooseOutputRoot = useAppStore((state) => state.chooseOutputRoot)

  return (
    <section className="space-y-4">
      <div>
        <div className="text-xs font-medium tracking-[0.14em] text-muted-foreground uppercase">
          02
        </div>
        <h2 className="mt-1 text-xl font-semibold tracking-tight">歌曲信息</h2>
      </div>

      <FieldGroup className="gap-4">
        <div className="grid grid-cols-[minmax(0,0.7fr)_minmax(0,1.3fr)] gap-3">
          <Field>
            <FieldLabel htmlFor="song-number">诗歌编号</FieldLabel>
            <Input
              id="song-number"
              value={songNumber}
              placeholder="诗歌编号"
              onChange={(event) => setSongNumber(event.target.value)}
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="song-title">诗歌名</FieldLabel>
            <Input
              id="song-title"
              value={songTitle}
              placeholder="诗歌名"
              onChange={(event) => setSongTitle(event.target.value)}
            />
          </Field>
        </div>

        <Field>
          <FieldLabel htmlFor="output-root">输出目录</FieldLabel>
          <div className="flex gap-2">
            <Input
              id="output-root"
              value={outputRoot}
              placeholder="输出目录"
              onChange={(event) => setOutputRoot(event.target.value)}
            />
            <Button variant="outline" onClick={chooseOutputRoot}>
              <FolderOpen />
              选择
            </Button>
          </div>
        </Field>
      </FieldGroup>
    </section>
  )
}
