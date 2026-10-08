'use client'

/**
 * 任务平台 / 房间状态总览
 *
 * 原实现直接渲染 <JSONTree>，可读性很差。
 * 现改为与日志页状态栏一致的房间卡片列表。
 *
 * 数据源：GET /v1/status（SWR，1 秒刷新）
 *
 * 字段说明（实测 2026-10）：
 *   downloader_status 直接是 "Idle" / "Pending" / "Working(...)"，
 *   **不带 Ok() 包装**（早期记忆里的Ok(...) 是 /v1/status 之外的形态）。
 *   为兼容两者，判定统一用 includes 子串匹配，不做等值比较。
 */

import { useMemo } from 'react'
import useSWR from 'swr'
import { Layout, Nav, Spin, Typography, Tag, Empty } from '@douyinfe/semi-ui'
import { fetcher } from '@/app/lib/api-streamer'
import {
  IconCustomerSupport,
  IconSetting,
} from '@douyinfe/semi-icons'

interface LiveStreamer {
  id?: number
  url?: string
  remark?: string
  format?: string
  filename_prefix?: string
  time_range?: string
  excluded_keywords?: string[] | string
  postprocessor?: unknown[]
  preprocessor?: unknown[]
  downloaded_processor?: unknown[]
  segment_processor?: unknown
  upload_streamers_id?: number
}

interface Room {
  live_streamer?: LiveStreamer
  upload_streamer?: unknown
  downloader_status?: string
  uploader_status?: string
}

interface StatusResp {
  version?: string
  rooms?: Room[]
  download_semaphore?: number
  update_semaphore?: number
}

type Kind = 'rec' | 'upload' | 'pending' | 'pause' | 'idle' | 'unknown'

function kindOf(raw?: string): Kind {
  const s = String(raw ?? '')
  if (!s || s === 'Unknown') return 'unknown'
  if (s.includes('Pause')) return 'pause'
  if (s.includes('Working')) return 'rec'
  if (s.includes('Upload')) return 'upload'
  if (s.includes('Pending')) return 'pending'
  if (s.includes('Idle')) return 'idle'
  return 'unknown'
}

const KIND_META: Record<Kind, { text: string; color: string; bg: string }> = {
  rec: { text: '录制中', color: 'var(--semi-color-danger)', bg: 'var(--semi-color-danger-light-default)' },
  upload: { text: '上传中', color: 'var(--semi-color-primary)', bg: 'var(--semi-color-primary-light-default)' },
  pending: { text: '等待中', color: 'var(--semi-color-warning)', bg: 'var(--semi-color-warning-light-default)' },
  pause: { text: '已暂停', color: 'var(--semi-color-tertiary)', bg: 'var(--semi-color-fill-1)' },
  idle: { text: '空闲', color: 'var(--semi-color-text-2)', bg: 'var(--semi-color-fill-1)' },
  unknown: { text: '未知', color: 'var(--semi-color-text-3)', bg: 'var(--semi-color-fill-1)' },
}

function badge(kind: Kind) {
  const m = KIND_META[kind]
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '1px 8px',
        borderRadius: 4,
        fontSize: 12,
        color: m.color,
        backgroundColor: m.bg,
        border: `1px solid ${m.color}33`,
        whiteSpace: 'nowrap',
      }}
    >
      {m.text}
    </span>
  )
}

/** 从 URL 推断平台名（比裸 URL 更易读） */
function platformOf(url?: string): string {
  if (!url) return '未知'
  const u = url.toLowerCase()
  if (u.includes('douyin')) return '抖音'
  if (u.includes('bilibili')) return 'B站'
  if (u.includes('huya')) return '虎牙'
  if (u.includes('douyu')) return '斗鱼'
  if (u.includes('bililive')) return '哔哩哔哩'
  if (u.includes('kuaishou')) return '快手'
  if (u.includes('acfun')) return 'AcFun'
  if (u.includes('youtube')) return 'YouTube'
  if (u.includes('twitcasting')) return 'TwitCasting'
  if (u.includes('afreeca')) return 'AfreecaTV'
  return '其他'
}

/** 提取房间号 / 用户标识，便于和 bilibili list 等工具对照 */
function identOf(url?: string): string {
  if (!url) return ''
  const t = url.replace(/\/+$/, '').split('/').pop() || ''
  return t.length > 24 ? t.slice(t.length - 24) : t
}

export default function Home() {
  const { Header, Content } = Layout
  const { data, error, isLoading } = useSWR<StatusResp>('/v1/status', fetcher, {
    refreshInterval: 1000,
    revalidateOnFocus: false,
  })

  const rooms = data?.rooms ?? []

  const stats = useMemo(() => {
    let rec = 0, up = 0, pending = 0, paused = 0
    for (const r of rooms) {
      const d = kindOf(r.downloader_status)
      if (d === 'rec') rec++
      else if (d === 'pending') pending++
      else if (d === 'pause') paused++
      const u = kindOf(r.uploader_status)
      if (u === 'upload' || u === 'rec') up++
    }
    return { rec, up, pending, paused }
  }, [rooms])

  return (
    <>
      <Header style={{ backgroundColor: 'var(--semi-color-bg-1)' }}>
        <Nav
          style={{ border: 'none' }}
          header={
            <>
              <div
                style={{
                  backgroundColor: 'rgba(var(--semi-lime-2), 1)',
                  borderRadius: 'var(--semi-border-radius-large)',
                  color: 'var(--semi-color-bg-0)',
                  display: 'flex',
                  padding: '6px',
                }}
              >
                <IconSetting size="large" />
              </div>
              <h4 style={{ marginLeft: '12px' }}>任务平台</h4>
            </>
          }
          mode="horizontal"
        />
      </Header>

      <Content
        style={{
          padding: 12,
          backgroundColor: 'var(--semi-color-bg-0)',
        }}
      >
        {/* 汇总条 */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 10,
            alignItems: 'center',
            padding: '10px 14px',
            marginBottom: 12,
            backgroundColor: 'var(--semi-color-bg-1)',
            border: '1px solid var(--semi-color-border)',
            borderRadius: 4,
            fontSize: 13,
          }}
        >
          <span style={{ fontWeight: 600 }}>v{data?.version ?? '?'}</span>
          <Tag color="grey" type="light" size="small">房间 {data ? rooms.length : '?'}</Tag>
          <Tag color="red" type="light" size="small">录制 {stats.rec}</Tag>
          <Tag color="blue" type="light" size="small">上传 {stats.up}</Tag>
          <Tag color="amber" type="light" size="small">等待 {stats.pending}</Tag>
          {stats.paused > 0 && <Tag color="grey" type="light" size="small">暂停 {stats.paused}</Tag>}
          <span style={{ color: 'var(--semi-color-text-3)', marginLeft: 'auto' }}>
            下载并发 {data?.download_semaphore ?? '?'} · 上传并发 {data?.update_semaphore ?? '?'}
          </span>
          {stats.rec > 0 && (
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--semi-color-danger)' }}>
              <span
                style={{
                  width: 7, height: 7, borderRadius: '50%',
                  backgroundColor: 'var(--semi-color-danger)',
                  animation: 'st-pulse 1.4s ease-in-out infinite',
                }}
              />
              正在录制
            </span>
          )}
        </div>

        {isLoading ? (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
            <Spin size="large" />
          </div>
        ) : error ? (
          <div
            style={{
              padding: 16,
              color: 'var(--semi-color-danger)',
              backgroundColor: 'var(--semi-color-danger-light-default)',
              borderRadius: 4,
            }}
          >
            ● 服务未响应，biliup 可能正在启动或已停止。
            <br />
            <span style={{ fontSize: 12, color: 'var(--semi-color-text-2)' }}>
              若刚启动请等待 10 秒后刷新页面。
            </span>
          </div>
        ) : rooms.length === 0 ? (
          <Empty description="服务返回 0 个房间，配置可能未加载" />
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
              gap: 10,
            }}
          >
            {rooms.map((r, i) => {
              const ls = r.live_streamer || {}
              const dk = kindOf(r.downloader_status)
              const uk = kindOf(r.uploader_status)
              const name = ls.remark || identOf(ls.url) || '未命名'
              const plat = platformOf(ls.url)
              const post = Array.isArray(ls.postprocessor) ? ls.postprocessor.length : 0

              return (
                <div
                  key={ls.id ?? i}
                  style={{
                    padding: '10px 12px',
                    backgroundColor: 'var(--semi-color-bg-1)',
                    border: '1px solid var(--semi-color-border)',
                    borderLeft: `3px solid ${KIND_META[dk === 'idle' ? uk : dk].color}`,
                    borderRadius: 4,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                    <Tag size="small" color="grey" type="light" style={{ flexShrink: 0 }}>{plat}</Tag>
                    <span style={{ fontWeight: 600, fontSize: 14, flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {name}
                    </span>
                    {badge(dk)}
                  </div>

                  <div style={{ fontSize: 12, color: 'var(--semi-color-text-3)', marginBottom: 4 }}>
                    {identOf(ls.url)}
                  </div>

                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, fontSize: 12 }}>
                    <span>上传：{badge(uk)}</span>
                    {ls.format && <Tag size="small">格式 {ls.format}</Tag>}
                    {ls.time_range && <Tag size="small">时段 {ls.time_range}</Tag>}
                    {post > 0 && <Tag size="small">后处理 {post}</Tag>}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <style jsx>{`
          @keyframes st-pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
          }
        `}</style>
      </Content>
    </>
  )
}