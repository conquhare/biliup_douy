/**
 * 录制分段参数的取值范围与估算。
 *
 * 背景（2026-10-09 实测）：
 *   用户手工填写 file_size（字节）时需要输入 `1621440000` 这类 10 位数，
 *   无法心算、极易少打一位，且截尾是**静默丢数据**（B站 total_size 是硬上限，
 *   超出部分被直接丢弃，用户毫无察觉）。
 *   因此改为「GB 档位下拉 + 实时体积预估」，把风险在配置阶段就暴露出来。
 *
 * 码率基准来自本项目 ds_update.log 的真实录制反推（10-06 ~ 10-09）：
 *   抖音直播实测 1.35 ~ 1.53 Mbps（房间配的是 douyin_quality=uhd）。
 *   参考区间按常见直播档位给出，取区间上限做保守估算，避免低估。
 */

/** 字节 / MB / GB 换算 */
export const KB = 1024
export const MB = 1024 * KB
export const GB = 1024 * MB

/**
 * file_size 档位（GB）。
 * 说明：真实字节数 = GB * 2^30，内部与Rust/Python 侧保持一致。
 */
export const FILE_SIZE_GB_OPTIONS = [0.5, 1, 2, 4, 8] as const

/** 分段时长档位（分钟）。0 表示不按时长切段。 */
export const SEGMENT_MINUTE_OPTIONS = [15, 30, 60, 120] as const

/**
 * 各画质档位的常见码率区间（Mbps）。
 * 索引对应 douyin_quality：origin / uhd / hd / sd / ld。
 * `实测` 标注的是本项目真实录制反推到的值。
 */
export interface QualityBitrate {
  key: string
  label: string
  /** 常见区间下限 Mbps */
  minMbps: number
  /** 常见区间上限 Mbps（估算取此值，保守） */
  maxMbps: number
  /** 本项目实测值（有则显示，可信度最高） */
  measuredMbps?: number
}

export const QUALITY_BITRATE: QualityBitrate[] = [
  { key: 'origin', label: '原画 origin', minMbps: 8, maxMbps: 20 },
  { key: 'uhd', label: '超清 uhd（1080P）', minMbps: 3, maxMbps: 8, measuredMbps: 1.4 },
  { key: 'hd', label: '高清 hd（720P）', minMbps: 1.5, maxMbps: 3 },
  { key: 'sd', label: '标清 sd（480P）', minMbps: 0.8, maxMbps: 1.5 },
  { key: 'ld', label: '流畅 ld（360P）', minMbps: 0.3, maxMbps: 0.8 },
]

/** 默认画质（与 douyin.py 中 quality_items[0] 一致） */
export const DEFAULT_QUALITY = 'origin'

/**
 * 码率兜底：房间未单独配quality 时用全局 global.tsx 的 douyin_quality。
 * 与 douyin.py 的取值校验保持一致（origin/uhd/hd/sd/ld/md）。
 */
const VALID_QUALITY = new Set(['origin', 'uhd', 'hd', 'sd', 'ld', 'md'])

export function resolveQuality(roomQuality?: string | null, globalQuality?: string | null): QualityBitrate {
  const pick = (q?: string | null) =>
    q && VALID_QUALITY.has(q) ? q : null
  const key = pick(roomQuality) ?? pick(globalQuality) ?? DEFAULT_QUALITY
  return (
    QUALITY_BITRATE.find((q) => q.key === key) ?? {
      key: DEFAULT_QUALITY,
      label: '原画 origin',
      minMbps: 8,
      maxMbps: 20,
    }
  )
}

/** 秒 → 'HH:MM:SS'（与后端 segment_time 格式一致） */
export function secondsToSegmentTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(h)}:${p(m)}:${p(s)}`
}

/** 'HH:MM:SS' / 'MM:SS' → 秒；非法返回 0 */
export function segmentTimeToSeconds(value?: string | null): number {
  if (!value) return 0
  const parts = String(value).split(':')
  if (parts.some((p) => !/^\d+$/.test(p))) return 0
  const nums = parts.map(Number)
  if (nums.length === 3) return nums[0] * 3600 + nums[1] * 60 + nums[2]
  if (nums.length === 2) return nums[0] * 60 + nums[1]
  return 0
}

/** 字节 → 人类可读（用于判断存量配置落在哪个档位） */
export function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return '未设置'
  if (bytes >= GB) {
    const g = bytes / GB
    return `${Number.isInteger(g) ? g : g.toFixed(2)} GB`
  }
  if (bytes >= MB) return `${Number((bytes / MB).toFixed(0))} MB`
  return `${bytes} Byte`
}

/**
 * 估算一段的体积范围（字节）。
 * 按码率区间上下限给出，区间更直观——单点值容易让人误以为很精确。
 */
export function estimateSegmentBytes(
  quality: QualityBitrate,
  segmentSeconds: number
): { minBytes: number; maxBytes: number } | null {
  if (!segmentSeconds || segmentSeconds <= 0) return null
  const lo = Math.ceil((quality.minMbps * 1e6 * segmentSeconds) / 8)
  const hi = Math.ceil((quality.maxMbps * 1e6 * segmentSeconds) / 8)
  return { minBytes: lo, maxBytes: hi }
}
