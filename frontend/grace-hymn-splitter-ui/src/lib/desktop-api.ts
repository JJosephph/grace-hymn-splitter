export type ApiResponse<T = Record<string, unknown>> = {
  ok: boolean
  error?: string
} & T

type PywebviewBridge = {
  api: Record<string, (...args: unknown[]) => Promise<unknown>>
}

declare global {
  interface Window {
    pywebview?: PywebviewBridge
  }
}

function bridgeReady(): boolean {
  return Boolean(window.pywebview?.api)
}

export function waitForDesktopBridge(): Promise<void> {
  if (bridgeReady()) return Promise.resolve()

  return new Promise((resolve) => {
    const started = Date.now()
    const timer = window.setInterval(() => {
      if (bridgeReady() || Date.now() - started > 8000) {
        window.clearInterval(timer)
        resolve()
      }
    }, 50)
  })
}

export async function callDesktop<T>(
  method: string,
  ...args: unknown[]
): Promise<ApiResponse<T>> {
  await waitForDesktopBridge()
  const handler = window.pywebview?.api?.[method]
  if (typeof handler !== "function") {
    return { ok: false, error: "客户端接口还没有准备好。" } as ApiResponse<T>
  }
  return (await handler(...args)) as ApiResponse<T>
}

export function fileUrl(path: string): string {
  if (!path) return ""
  const normalized = path.replaceAll("\\", "/")
  return encodeURI(`file:///${normalized}`)
}
