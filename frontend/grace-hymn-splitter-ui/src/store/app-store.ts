import { create } from "zustand"
import { toast } from "sonner"

import { callDesktop, fileUrl } from "@/lib/desktop-api"

export type BoldMode = "none" | "light" | "strong"
export type JobStatus = "idle" | "running" | "completed" | "failed"

export type SelectedImage = {
  name: string
  path: string
  url: string
}

export type PreviewImage = {
  name: string
  path: string
  url: string
}

export type LogLine = {
  time: string
  title: string
  message: string
}

export type JobState = {
  status: JobStatus
  message: string
  progress: number
  logs: LogLine[]
  error: string
  result: {
    output_dir?: string
    count?: number
    previews?: PreviewImage[]
  }
}

type Brand = {
  name: string
  subtitle: string
  tagline: string
  developer: string
  developer_email: string
  license: string
}

type Bootstrap = {
  version: string
  default_output_root: string
  project_dir: string
  brand: Brand
  settings?: Record<string, unknown>
}

type AppStore = {
  bootstrapped: boolean
  bootstrap: Bootstrap | null
  image: SelectedImage | null
  outputRoot: string
  songNumber: string
  songTitle: string
  boldMode: BoldMode
  keepMetadata: boolean
  makeChorus: boolean
  job: JobState
  initialize: () => Promise<void>
  setImage: (image: SelectedImage) => void
  clearImage: () => void
  setOutputRoot: (value: string) => void
  setSongNumber: (value: string) => void
  setSongTitle: (value: string) => void
  setBoldMode: (value: BoldMode) => void
  setKeepMetadata: (value: boolean) => void
  setMakeChorus: (value: boolean) => void
  chooseImage: () => Promise<void>
  chooseOutputRoot: () => Promise<void>
  startBuild: () => Promise<void>
  pollJob: () => Promise<void>
  openPath: (path: string) => Promise<void>
  checkUpdates: () => Promise<void>
}

const initialJob: JobState = {
  status: "idle",
  message: "等待制作",
  progress: 0,
  logs: [],
  error: "",
  result: {},
}

function parseSongName(fileName: string) {
  const stem = fileName.replace(/\.[^.]+$/, "").trim()
  const match = stem.match(/^(\d{1,4})[\s._-]+(.+)$/)
  if (!match) return { number: "", title: stem }
  return { number: match[1], title: match[2].trim() }
}

function normalizeImage(
  path: string,
  name?: string,
  url?: string,
): SelectedImage {
  return {
    path,
    name: name || path.split(/[\\/]/).pop() || "歌谱图片",
    url: url || fileUrl(path),
  }
}

export const useAppStore = create<AppStore>((set, get) => ({
  bootstrapped: false,
  bootstrap: null,
  image: null,
  outputRoot: "",
  songNumber: "",
  songTitle: "",
  boldMode: "none",
  keepMetadata: true,
  makeChorus: true,
  job: initialJob,

  initialize: async () => {
    const response = await callDesktop<{
      version: string
      default_output_root: string
      project_dir: string
      brand: Brand
      settings?: Record<string, unknown>
    }>("get_bootstrap")

    if (!response.ok) {
      toast.error(response.error || "软件初始化失败。")
      return
    }

    const settings = response.settings || {}
    const boldMode =
      settings.bold_mode === "light" || settings.bold_mode === "strong"
        ? settings.bold_mode
        : "none"

    set({
      bootstrapped: true,
      bootstrap: {
        version: response.version,
        default_output_root: response.default_output_root,
        project_dir: response.project_dir,
        brand: response.brand,
        settings,
      },
      outputRoot: response.default_output_root || "",
      boldMode,
      keepMetadata: settings.keep_metadata_first_page !== false,
      makeChorus: settings.make_chorus_page !== false,
    })
  },

  setImage: (image) => {
    const guessed = parseSongName(image.name)
    set({
      image,
      songNumber: guessed.number,
      songTitle: guessed.title,
    })
  },

  clearImage: () =>
    set({
      image: null,
      songNumber: "",
      songTitle: "",
    }),

  setOutputRoot: (value) => set({ outputRoot: value }),
  setSongNumber: (value) => set({ songNumber: value }),
  setSongTitle: (value) => set({ songTitle: value }),
  setBoldMode: (value) => set({ boldMode: value }),
  setKeepMetadata: (value) => set({ keepMetadata: value }),
  setMakeChorus: (value) => set({ makeChorus: value }),

  chooseImage: async () => {
    const response = await callDesktop<{ path: string; url: string }>(
      "choose_image",
    )
    if (!response.ok) {
      toast.error(response.error || "选择图片失败。")
      return
    }
    if (response.path) {
      get().setImage(
        normalizeImage(response.path, undefined, response.url),
      )
    }
  },

  chooseOutputRoot: async () => {
    const response = await callDesktop<{ path: string }>("choose_output_dir")
    if (!response.ok) {
      toast.error(response.error || "选择目录失败。")
      return
    }
    if (response.path) set({ outputRoot: response.path })
  },

  startBuild: async () => {
    const state = get()
    if (!state.image?.path) {
      toast.error("请先上传歌谱图片。")
      return
    }
    if (!state.outputRoot.trim()) {
      toast.error("请选择输出目录。")
      return
    }

    const response = await callDesktop(
      "start_build",
      state.image.path,
      state.songNumber,
      state.songTitle,
      state.outputRoot,
      state.boldMode,
      state.keepMetadata,
      state.makeChorus,
    )

    if (!response.ok) {
      toast.error(response.error || "无法开始制作。")
      return
    }

    set({
      job: {
        status: "running",
        message: "正在准备歌谱…",
        progress: 4,
        logs: [],
        error: "",
        result: {},
      },
    })
  },

  pollJob: async () => {
    const response = await callDesktop<{ job: JobState }>("get_job_state")
    if (!response.ok || !response.job) return

    const previous = get().job
    set({ job: response.job })

    if (
      previous.status === "running" &&
      response.job.status === "completed"
    ) {
      toast.success(response.job.message || "制作完成。")
    }
    if (previous.status === "running" && response.job.status === "failed") {
      toast.error(response.job.error || "制作没有完成。")
    }
  },

  openPath: async (path) => {
    const response = await callDesktop("open_path", path)
    if (!response.ok) toast.error(response.error || "无法打开路径。")
  },

  checkUpdates: async () => {
    const loading = toast.loading("正在检查更新…")
    const response = await callDesktop<{
      current: string
      latest?: string
      has_update?: boolean
      release_url?: string
    }>("check_updates")
    toast.dismiss(loading)

    if (!response.ok) {
      toast.error(response.error || "暂时无法检查更新。")
      return
    }
    if (response.has_update) {
      toast.success(`发现新版本 v${response.latest}`)
      if (response.release_url) {
        await callDesktop("open_url", response.release_url)
      }
      return
    }
    toast.success(`已是最新版本 v${response.current}`)
  },
}))
