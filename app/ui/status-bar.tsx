'use client'

/**
 * 实时状态顶栏
 *
 * 设计目标（与桌面版 run_biliup.ps1 的置顶状态区一致）：
 *   固定 3 行，日志区在其下方滚动，日志不会把状态顶掉。
 *
 * 数据源：
 *   GET /v1/status       房间录制/上传状态（SWR，1 秒刷新）
 *   logs (prop)上传进度（复用日志页已有的 WebSocket 流，零额外请求）
 *
 * 注意：
 *   1. 状态串实测为 "Idle" / "Pending" / "Working(...)"（2026-10 实测，
 *      不带Ok() 包装）。判定统一用 includes 子串匹配，
 *      这样无论是否带包装都能正确命中。
 *   2. logs 数组会不断增长，本组件只扫描末尾若干条，
 *      避免每次渲染都全量遍历。
 */

import { useMemo } from 'react'
import useSWR from 'swr'
import { fetcher } from '@/app/lib/api-streamer'

const isRecording = (s: string) => s.includes('Working')
const isUploading = (s: string) => /Working|Upload/.test(s)
const isPaused = (s: string) => s.includes('Pause')

interface Room {
  live_streamer?: { url?: string; remark?: string }
  downloader_status?: string
  uploader_status?: string
}

interface StatusResp {
  version?: string
  rooms?: Room[]
  download_semaphore?: number
  update_semaphore?: number
}

interface UploadInfo {
  name: string
  seg: string
  total: string
  speed: string
}

/** 从 URL 尾部取可读标识，优先用备注名 */
function shortName(url?: string, remark?: string): string {
  if (remark) return remark
  if (!url) return '未知'
  const t = url.replace(/\/+$/, '').split('/').pop() || '未知'
  return t.length > 22 ? t.slice(t.length - 22) : t
}

/**
 * 从日志行提取上传进度。
 * 匹配 biliup 的分片上传日志（见 biliup/plugins/bili_webup_sync.py）：
 *   xxx.mkv - chunks-(20/155) - down - speed: 3.70Mbps
 *   xxx.mkv - chunks-20 - up status: 200 - speed: 40.30Mbps
 *   upload_1 线路选择 => upos: upcdn=tx&probe_version=20221109.
 *
 * 只看末尾若干行：上传进度是高频滚动的，扫描全量没有意义。
 */
function parseUploads(logs: string[]): UploadInfo[] {
  if (!logs || logs.length === 0) return []
  const map = new Map<string, UploadInfo>()
  const from = Math.max(0, logs.length - 400)

  for (let i = from; i < logs.length; i++) {
    const ln = logs[i]
    if (!ln) continue

    // 「开始上传 xxx.mkv」—— 初始化条目，保证上传刚开始就能显示
    let m = ln.match(/开始上传\s+(.+?\.mkv)/)
    if (m) {
      map.set(m[1], { name: m[1], seg: '0', total: '?', speed: '?' })
      continue
    }

    // 「chunks-20 - up status: 200 - speed: 40.30Mbps」—— 最新进度
    m = ln.match(/^(.+?\.mkv)\s+-\s+chunks-(\d+)\s+-\s+up\s+status:.*?speed:\s*([\d.]+)Mbps/)
    if (m) {
      const prev = map.get(m[1])
      map.set(m[1], { name: m[1], seg: m[2], total: prev?.total ?? '?', speed: m[3] })
      continue
    }

    // 「chunks-(20/155) - down - speed: 3.70Mbps」—— 能拿到总段数
    m = ln.match(/^(.+?\.mkv)\s+-\s+chunks-\((\d+)\/(\d+)\)(?:.*?speed:\s*([\d.]+)Mbps)?/)
    if (m) {
      map.set(m[1], { name: m[1], seg: m[2], total: m[3], speed: m[4] ?? '?' })
    }
  }

  // 最多显示 3 个，按文件名去重后取最近的
  const list = Array.from(map.values())
  const seen = new Set<string>()
  const out: UploadInfo[] = []
  for (let i = list.length - 1; i >= 0 && out.length < 3; i--) {
    const base = list[i].name.replace(/\.mkv$/, '')
    if (seen.has(base)) continue
    seen.add(base)
    out.unshift(list[i])
  }
  return out
}

interface StatusBarProps {
  /** 日志页已持有的日志行（来自 WebSocket），用于提取上传进度 */
  logs?: string[]
}

export default function StatusBar({ logs = [] }: StatusBarProps) {
  const { data, error } = useSWR<StatusResp>('/v1/status', fetcher, {
    refreshInterval: 1000,
    revalidateOnFocus: false,
  })

  const uploads = useMemo(() => parseUploads(logs), [logs])

  const rooms = data?.rooms ?? []
  const recording = rooms.filter(r => isRecording(String(r.downloader_status ?? '')))
  const paused = rooms.filter(r => isPaused(String(r.downloader_status ?? '')))
  const uploadingRooms = rooms.filter(r => isUploading(String(r.uploader_status ?? '')))

  // ---- 第 1 行：录制概览 ----
  let line1: string
  let tone: 'idle' | 'rec' | 'warn' = 'idle'
  if (error) {
    line1 = '● 服务未响应（biliup 可能正在启动…）'
    tone = 'warn'
  } else if (recording.length > 0) {
    const items = recording.map(r => `[录制中] ${shortName(r.live_streamer?.url, r.live_streamer?.remark)}`)
    line1 = `● 正在录制 ${recording.length} 个房间 | ${items.join('  |  ')}`
    tone = 'rec'
  } else if (rooms.length === 0) {
    line1 = '[警告] 服务返回 0 个房间，配置可能未加载'
    tone = 'warn'
  } else {
    line1 = `o 当前没有房间在录制（监控运行中，等待开播）  ·  房间 ${rooms.length}`
  }

  // ---- 第 2 行：上传概览 ----
  let line2: string
  if (uploads.length > 0) {
    line2 = '↑ 上传中: ' + uploads.map(u => {
      const base = u.name.replace(/\.mkv$/, '')
      const seg = u.total !== '?' ? `${u.seg}/${u.total}` : u.seg
      const spd = u.speed !== '?' ? `  ${u.speed}Mbps` : ''
      return `${base} ${seg}${spd}`
    }).join('  |  ')
  } else if (uploadingRooms.length > 0) {
    line2 = '↑ 上传中: ' + uploadingRooms.map(r => shortName(r.live_streamer?.url, r.live_streamer?.remark)).join('  |  ')
  } else {
    line2 = '↑ 上传：空闲'
  }

  // ---- 第 3 行：汇总 ----
  const now = new Date()
  const p2 = (n: number) => String(n).padStart(2, '0')
  const line3 =
    `${p2(now.getHours())}:${p2(now.getMinutes())}:${p2(now.getSeconds())}` +
    `  ·  房间 ${data ? rooms.length : '?'}` +
    `  ·  下载并发 ${data?.download_semaphore ?? '?'}` +
    `  ·  上传并发 ${data?.update_semaphore ?? '?'}` +
    (paused.length > 0 ? `  ·  已暂停 ${paused.length}` : '')

  const dotColor = tone === 'rec' ? 'var(--semi-color-danger)'
    : tone === 'warn' ? 'var(--semi-color-warning)'
      : 'var(--semi-color-tertiary)'
  const textColor = tone === 'rec' ? 'var(--semi-color-danger)'
    : tone === 'warn' ? 'var(--semi-color-warning)'
      : 'var(--semi-color-text-1)'

  return (
    <div
      style={{
        // 关键：状态区固定在顶部，日志滚动时不被顶掉
        position: 'sticky',
        top: 0,
        zIndex: 10,
        backgroundColor: 'var(--semi-color-bg-1)',
        border: '1px solid var(--semi-color-border)',
        borderRadius: 4,
        padding: '8px 12px',
        marginBottom: 8,
        fontSize: 13,
        lineHeight: '21px',
        fontVariantNumeric: 'tabular-nums',
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            backgroundColor: dotColor,
            flexShrink: 0,
            animation: tone === 'rec' ? 'sb-pulse 1.4s ease-in-out infinite' : undefined,
          }}
        />
        <span style={{ color: textColor, fontWeight: 500 }}>{line1}</span>
      </div>
      <div style={{ color: 'var(--semi-color-text-1)', paddingLeft: 16 }}>{line2}</div>
      <div style={{ color: 'var(--semi-color-text-3)', paddingLeft: 16, fontSize: 12 }}>{line3}</div>

      <style jsx>{`
        @keyframes sb-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  )
}