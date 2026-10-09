'use client'
import React, { useEffect, useMemo } from 'react'
import styles from '../../styles/dashboard.module.scss'
import { Form, Select, Space, useFormApi, Collapse } from '@douyinfe/semi-ui'
import { IconUpload, IconDownload } from '@douyinfe/semi-icons'
import DanmakuConfig from './DanmakuConfig'
import {
  FILE_SIZE_GB_OPTIONS,
  SEGMENT_MINUTE_OPTIONS,
  GB,
  MB,
  formatBytes,
  estimateSegmentBytes,
  resolveQuality,
  segmentTimeToSeconds,
  secondsToSegmentTime,
} from '@/app/lib/segment-presets'

/** 字节数 → 最接近的 GB 档位；不匹配任何档位时返回 'custom' */
function bytesToGbOption(bytes?: number | null): number | 'custom' {
  if (!bytes || bytes <= 0) return 4
  const hit = FILE_SIZE_GB_OPTIONS.find((gb) => Math.abs(gb * GB - bytes) < 1)
  return hit ?? 'custom'
}

/** 秒 → 最接近的分钟档位；无时长返回 'none'，不匹配返回 'custom' */
function secondsToMinuteOption(seconds: number): number | 'custom' | 'none' {
  if (!seconds || seconds <= 0) return 'none'
  const hit = SEGMENT_MINUTE_OPTIONS.find((m) => m * 60 === seconds)
  return hit ?? 'custom'
}

const Global: React.FC = () => {
  const formApi = useFormApi()

  // 读取当前画质（房间级 override 优先，其次全局），用于体积预估
  const quality = useMemo(() => {
    const streamer = formApi.getValue('streamers') ?? {}
    const first = Object.values(streamer)[0] as any
    const roomQuality = first?.override?.douyin_quality ?? null
    const globalQuality = formApi.getValue('douyin_quality') ?? null
    return resolveQuality(roomQuality, globalQuality)
  }, [formApi.getValue('streamers'), formApi.getValue('douyin_quality')])

  // 当前分段时长（秒）
  const segmentSeconds = useMemo(() => {
    const minutes = formApi.getValue('segment_time_minutes')
    if (minutes === 'none' || minutes === undefined || minutes === null) return 0
    if (minutes === 'custom') return segmentTimeToSeconds(formApi.getValue('segment_time'))
    return Number(minutes) * 60
  }, [formApi.getValue('segment_time_minutes'), formApi.getValue('segment_time')])

  // 当前体积上限（字节）
  const sizeBytes = useMemo(() => {
    const gb = formApi.getValue('file_size_gb')
    if (gb === 'custom') return Number(formApi.getValue('file_size')) || 0
    if (gb === undefined || gb === null) return 0
    return Number(gb) * GB
  }, [formApi.getValue('file_size_gb'), formApi.getValue('file_size')])

  // 实时预估与风险提示
  const sizeAdvice = useMemo(() => {
    const est = estimateSegmentBytes(quality, segmentSeconds)
    const segText =
      segmentSeconds > 0
        ? `${segmentSeconds >= 3600 ? `${segmentSeconds / 3600} 小时` : `${segmentSeconds / 60} 分钟`}`
        : '（未按时长切段）'

    if (!est) {
      return {
        level: 'warn' as const,
        title: '当前仅按体积切段',
        detail:
          `未设置分段时长，单段大小将由 file_size（${formatBytes(sizeBytes)}）决定。` +
          '若录制很久，建议同时设置分段时长，避免单段体积过大。',
      }
    }

    const { minBytes, maxBytes } = est
    const measured = quality.measuredMbps
    const base =
      `画质 ${quality.label}` +
      (measured ? `（本项目实测 ${measured} Mbps）` : `（常见 ${quality.minMbps}~${quality.maxMbps} Mbps）`) +
      ` · 分段 ${segText} → 单段约 ${formatBytes(minBytes)} ~ ${formatBytes(maxBytes)}`

    if (!sizeBytes) {
      return {
        level: 'warn' as const,
        title: '未设置体积上限',
        detail: base + '。建议把 file_size 设到区间上限之上，否则高码率时可能被提前切断。',
      }
    }

    if (sizeBytes < minBytes) {
      return {
        level: 'danger' as const,
        title: `体积上限偏小：${formatBytes(sizeBytes)} < 单段需要 ${formatBytes(minBytes)}`,
        detail:
          base +
          `。在 ${formatBytes(sizeBytes)} 处就会切段，` +
          `若码率高于 ${((sizeBytes * 8) / segmentSeconds / 1e6).toFixed(1)}Mbps 则` +
          '时长设置形同虚设；同时申报的 total_size 偏小，存在尾部数据被丢弃的风险。',
      }
    }

    if (sizeBytes < maxBytes) {
      return {
        level: 'warn' as const,
        title: `体积上限偏小：${formatBytes(sizeBytes)}（建议 ≥ ${formatBytes(maxBytes)}）`,
        detail:
          base +
          `。低码率下够用，但码率超过 ${((sizeBytes * 8) / segmentSeconds / 1e6).toFixed(1)}Mbps 时` +
          '会退化为按体积切段（每段短于设定时长）。',
      }
    }

    return {
      level: 'ok' as const,
      title: `配置合理（${formatBytes(sizeBytes)} ≥ 单段 ${formatBytes(maxBytes)}）`,
      detail: base + '。将以设定时长切段，体积上限不会误触。',
    }
  }, [quality, segmentSeconds, sizeBytes])

  // 存量配置反解：把后端的字节数/时间串映射到新档位，避免升级后变空值
  useEffect(() => {
    const rawSize = formApi.getValue('file_size')
    const rawTime = formApi.getValue('segment_time')
    if (rawSize || rawTime) {
      if (formApi.getValue('file_size_gb') === undefined) {
        formApi.setValue('file_size_gb', bytesToGbOption(Number(rawSize) || 0))
      }
      if (formApi.getValue('segment_time_minutes') === undefined) {
        const secs = segmentTimeToSeconds(rawTime)
        const opt = secondsToMinuteOption(secs)
        if (opt === 'custom') formApi.setValue('segment_time', rawTime)
        formApi.setValue('segment_time_minutes', opt)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 档位 → 后端原始字段 的同步。
  // 不依赖提交时机（formApi.submit 不可覆写），改为 onValueChange 立即回写，
  // 这样表单里file_size / segment_time 始终是后端认识的类型。
  const syncFromPreset = useMemo(() => {
    return (changed: string) => {
      if (changed === 'file_size_gb') {
        const gb = formApi.getValue('file_size_gb')
        if (gb !== 'custom') {
          formApi.setValue(
            'file_size',
            gb === undefined || gb === null ? undefined : Number(gb) * GB
          )
        }
      }
      if (changed === 'segment_time_minutes') {
        const minutes = formApi.getValue('segment_time_minutes')
        if (minutes === 'none') {
          formApi.setValue('segment_time', undefined)
        } else if (minutes !== 'custom' && minutes !== undefined && minutes !== null) {
          formApi.setValue('segment_time', secondsToSegmentTime(Number(minutes) * 60))
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formApi])

  useEffect(() => {
    // Semi FormApi 未在类型中暴露 onValueChange；同步已在各 Select 的
    // onChange 里直接调用 syncFromPreset，此处仅兜底处理自定义输入框。
    const anyApi = formApi as unknown as {
      onValueChange?: (cb: (changed: string) => void) => (() => void) | void
    }
    const handler = anyApi.onValueChange?.((changed: string) => syncFromPreset(changed))
    return () => {
      if (typeof handler === 'function') handler()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [formApi, syncFromPreset])

  return (
    <>
      {/* 全局下载 */}
      <div className={styles.frameDownload}>
        <div className={styles.frameInside}>
          <div className={styles.group}>
            <div className={styles.buttonOnlyIconSecond} />
            <div
              className={styles.lineStory}
              style={{
                color: 'var(--semi-color-bg-0)',
                display: 'flex',
              }}
            >
              <IconDownload size="small" />
            </div>
          </div>
          <p className={styles.meegoSharedWebWorkIt}>全局下载设置</p>
        </div>
        <Form.Select
          label="下载器类型(downloader)"
          field="downloader"
          placeholder="stream-gears(默认)"
          // initValue="stream-gears"
          extraText={
            <div style={{ fontSize: '14px' }}>
              选择全局默认的下载器, 可选:
              <br />
              1. streamlink(支持 hls 和 http 流，需要安装 ffmpeg，Docker 用户需要安装 FFmpeg)
              <br />
              2. ffmpeg(需要安装 ffmpeg，Docker 用户需要安装 FFmpeg)
              <br />
              3. stream-gears(默认，支持 FLV 和 HLS 流)
              <br />
              4. sync-downloader(同步下载器，用于边录边传模式。需要
              pool2/threads/segment_time 配置，默认 3 线程上传，确保上传速度足够。Docker 用户需要安装 FFmpeg，具体请查看{' '}
              <a href="https://github.com/biliup/biliup/wiki/%E8%BE%B9%E5%BD%95%E8%BE%B9%E4%BC%A0%E5%8A%9F%E8%83%BD" target="_blank" rel="noopener noreferrer">详细查看</a>
              <br />
              5. ytarchive(专门用于 Youtube Live)
              <br />
              {/* 6. mesio(基于 Rust 的异步视频下载/修改工具 <a href="https://github.com/hua0512/rust-srec/tree/main/mesio-cli" target="_blank" rel="noopener noreferrer" >项目主页</a> */}
            </div>
          }
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        >
          <Select.Option value="streamlink">streamlink(支持 hls 和 http 流)</Select.Option>
          <Select.Option value="ffmpeg">ffmpeg</Select.Option>
          <Select.Option value="stream-gears">stream-gears(默认)</Select.Option>
          <Select.Option value="sync-downloader">sync-downloader(同步下载器)</Select.Option>
          <Select.Option value="ytarchive">ytarchive(专门用于 Youtube Live)</Select.Option>
          {/* <Select.Option value="mesio">mesio</Select.Option> */}
        </Form.Select>
        {formApi.getValue('downloader') === 'sync-downloader' ? (
          <>
            <Form.Input
              field="sync_save_dir"
              label="同步下载器本地保存目录(sync_save_dir)"
              placeholder=""
              style={{ width: '100%' }}
              fieldStyle={{
                alignSelf: 'stretch',
                padding: 0,
              }}
              showClear={true}
              disabled={formApi.getValue('downloader') === 'sync-downloader' ? false : true}
              rules={[
                {
                  pattern: /^[^*|?"<>]*$/,
                  message: '路径中不能包含Windows系统保留字符 * | ? " < >',
                },
                {
                  pattern: /^(?![a-zA-Z]：).*$/,
                  message: '盘符开头时需要在第二个字符位置使用冒号',
                },
                {
                  pattern: /^[^:]*$|^[a-zA-Z]:[\\/][^:]*$/,
                  message: '冒号只能出现在第二个字符位置，并且后面不能跟冒号',
                },
                {
                  pattern: /^(?!.*?\.{3,})(?!.*?\.{2}(?![\\/])).*$/,
                  message: '文件名中只能包含单个点号，并且后面不能跟点号',
                },
                {
                  pattern: /^(?!.*[\\/][\\/])(?!.*[\\/][\\/]).*$/,
                  message: '路径中不能混合使用正斜杠和反斜杠',
                },
                {
                  pattern: /^(?!.*([\\]{3,}|[\\/]{2,})).*$/,
                  message: '反斜杠和正斜杠只能单独使用，不能连续使用超过两个',
                },
              ]}
              stopValidateWithError={true}
            />
          </>
        ) : null}
        <Form.Select
          label="视频分段大小(file_size)"
          extraText={
            <div style={{ fontSize: '14px' }}>
              单段体积上限，超过即自动切段。
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>
                体积上限同时是 B站 申报的 total_size（硬上限，超出部分会被丢弃）。
              </span>
              {' '}因此不宜设得小于「分段时长 × 画质码率」，否则会出现
              <b> 视频尾部被静默截断</b> 且没有任何报错。
            </div>
          }
          field="file_size_gb"
          placeholder="请选择分段体积上限"
          style={{ width: '100%' }}
          onChange={() => syncFromPreset('file_size_gb')}
        >
          {FILE_SIZE_GB_OPTIONS.map((gb) => (
            <Form.Select.Option key={gb} value={gb}>
              {gb < 1 ? `${gb * 1024} MB` : `${gb} GB`}
            </Form.Select.Option>
          ))}
          <Form.Select.Option value="custom">自定义（手动填写字节数）</Form.Select.Option>
        </Form.Select>
        {formApi.getValue('file_size_gb') === 'custom' ? (
          <Form.InputNumber
            label="自定义分段大小(字节)"
            extraText={
              <div style={{ fontSize: '14px' }}>
                单位 Byte。1 GB = {GB} 字节；1 MB = {MB} 字节。
                <br />
                留空则不设置体积上限（仅按下方分段时长切段）。
              </div>
            }
            field="file_size"
            placeholder={`例如 ${GB * 2}（2GB）`}
            suffix={'Byte'}
            style={{ width: '100%', marginTop: -12 }}
            fieldStyle={{ alignSelf: 'stretch', padding: 0 }}
            rules={[
              {
                // Semi的 validator 签名固定为 5 参；此处显式声明以匹配类型
                validator: ((
                  _rule: unknown,
                  value: unknown,
                  callback: (error?: string) => void
                ) => {
                  const fail = (msg: string) => {
                    callback(msg)
                    return false
                  }
                  const pass = () => {
                    callback()
                    return true
                  }
                  if (value === undefined || value === null || value === '') return pass()
                  if (typeof value !== 'number' || !Number.isFinite(value)) {
                    return fail('请输入数字')
                  }
                  if (value <= 0) return fail('必须大于 0')
                  if (value % MB !== 0) {
                    return fail(`必须是 ${MB} 字节(1MB) 的整数倍，否则 B站分块上传会失败`)
                  }
                  return pass()
                }) as never,
              },
            ]}
            stopValidateWithError={true}
          />
        ) : null}
        <Form.Select
          field="segment_time_minutes"
          label="视频分段时间(segment_time)"
          extraText={
            <div style={{ fontSize: '14px' }}>
              单段时长上限，超过即自动切段。建议 30 分钟——B站按分P 展示，过长不利观看与上传稳定性。
              <br />
              填「仅按体积」则不按时长切段（仅 file_size 生效）。
            </div>
          }
          placeholder="请选择分段时长"
          style={{ width: '100%' }}
          onChange={() => syncFromPreset('segment_time_minutes')}
        >
          {SEGMENT_MINUTE_OPTIONS.map((m) => (
            <Form.Select.Option key={m} value={m}>
              {m >= 60 ? `${m / 60} 小时` : `${m} 分钟`}
            </Form.Select.Option>
          ))}
          <Form.Select.Option value="none">仅按体积切段（不按时长）</Form.Select.Option>
        </Form.Select>

        {/* 实时预估：把「配了会怎样」提前暴露，避免静默截尾 */}
        <div
          style={{
            margin: '-8px 0 12px',
            padding: '10px 12px',
            borderRadius: 4,
            background: 'var(--semi-color-fill-1)',
            borderLeft: `3px solid ${
              sizeAdvice.level === 'danger'
                ? 'var(--semi-color-danger)'
                : sizeAdvice.level === 'warn'
                  ? 'var(--semi-color-warning)'
                  : 'var(--semi-color-success)'
            }`,
            fontSize: 13,
            lineHeight: '20px',
          }}
        >
          <div style={{ color: 'var(--semi-color-text-1)', fontWeight: 500 }}>
            {sizeAdvice.title}
          </div>
          <div style={{ color: 'var(--semi-color-text-2)', marginTop: 2 }}>
            {sizeAdvice.detail}
          </div>
        </div>

        <Form.Input
          field="filename_prefix"
          extraText={
            <div style={{ fontSize: '14px' }}>
              全局文件名模板。可包含变量和文件名模板，不是指保存路径
              <br />
              {'{streamer}'}: 录播主播名称备注
              <span style={{ margin: '0 20px' }}></span>
              {'{title}'}: 直播标题
              <br />
              %Y-%m-%d %H_%M_%S: 开始录制时间 年-月-日 时_分_秒
            </div>
          }
          label="文件名模板(filename_prefix)"
          placeholder="{streamer}%Y-%m-%dT%H_%M_%S"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
        <Form.Switch
          field="segment_processor_parallel"
          extraText={<div style={{ fontSize: '14px' }}>开启后无法保证分段后处理执行顺序</div>}
          label="视频分段后处理并行(segment_processor_parallel)"
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
        />
        <Form.InputNumber
          field="filtering_threshold"
          extraText={
            <div style={{ fontSize: '14px' }}>
              小于此大小的视频文件会被自动删除
              <br />
              单位为MB
            </div>
          }
          label="片段过滤(filtering_threshold)"
          suffix={'MB'}
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />

        <Form.InputNumber
          field="delay"
          label="开播延迟检测(delay)"
          extraText={
            <div style={{ fontSize: '14px' }}>
              当检测到主播开播后延迟一段时间再次检测确认，避免网络波动导致误上传或分段错误
              <br />
              单位为秒
              <br />
              默认延迟时间为 0 秒
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>⚠️ 修改后需要重启服务才能生效</span>
            </div>
          }
          placeholder="0"
          suffix="s"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
        <Form.InputNumber
          field="event_loop_interval"
          extraText={
            <div style={{ fontSize: '14px' }}>
              平台检测间隔时间，单位为秒。例如斗鱼平台会每30秒去检测一次直播状态
              <br />
              单位为秒
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>⚠️ 修改后需要重启服务才能生效</span>
            </div>
          }
          label="平台检测间隔(event_loop_interval)"
          suffix="s"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
        <Form.InputNumber
          field="checker_sleep"
          extraText={
            <div style={{ fontSize: '14px' }}>
              房间检测间隔时间，单位为秒。例如斗鱼平台每10秒检测一次每个房间
              <br />
              如果房间检测设置为0，则使用平台检测间隔(event_loop_interval)
              <br />
              单位为秒
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>⚠️ 修改后需要重启服务才能生效</span>
            </div>
          }
          label="房间检测间隔(checker_sleep)"
          suffix="s"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
        <Form.InputNumber
          field="pool1_size"
          extraText={
            <div style={{ fontSize: '14px' }}>
              录制下载线程池大小，决定可以同时录制多少个房间
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>⚠️ 修改后需要重启服务才能生效</span>
            </div>
          }
          placeholder={5}
          label="录制线程池大小(pool1_size)"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
      </div>

      <Space />

      {/* 弹幕录制与处理 */}
      <div className={styles.frameDownload}>
        <div className={styles.frameInside}>
          <div className={styles.group}>
            <div className={styles.buttonOnlyIconSecond} />
            <div
              className={styles.lineStory}
              style={{
                color: 'var(--semi-color-bg-0)',
                display: 'flex',
              }}
            >
              <IconDownload size="small" />
            </div>
          </div>
          <p className={styles.meegoSharedWebWorkIt}>弹幕录制与处理</p>
        </div>
        <Collapse keepDOM style={{ width: '100%' }}>
          <DanmakuConfig platformName="全局" />
        </Collapse>
      </div>

      <Space />

      {/* 全局上传 */}
      <div className={styles.frameUpload}>
        <div className={styles.frameInside}>
          <div className={styles.group}>
            <div className={styles.buttonOnlyIconSecond} />
            <div
              className={styles.lineStory}
              style={{
                color: 'var(--semi-color-bg-0)',
                display: 'flex',
              }}
            >
              <IconUpload size="small" />
            </div>
          </div>
          <p className={styles.meegoSharedWebWorkIt}>全局上传设置</p>
        </div>

        <Form.Select
          field="submit_api"
          label="提交接口(submit_api)"
          extraText="B站投稿提交接口，默认为自动选择"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        >
          <Form.Select.Option value="app">安卓APP(app)</Form.Select.Option>
          <Form.Select.Option value="b-cut-android">BCut安卓APP(b-cut-android)</Form.Select.Option>
          <Form.Select.Option value="web">网页端(web)</Form.Select.Option>
        </Form.Select>
        <Form.Select
          field="uploader"
          label="上传器类型(uploader)"
          extraText="全局默认上传器选择"
          placeholder="biliup-rs"
          noLabel={true}
          style={{ width: '100%', display: 'none' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
          initValue="Noop"
        >
          <Form.Select.Option value="bili_web">bili_web</Form.Select.Option>
          <Form.Select.Option value="biliup-rs">biliup-rs</Form.Select.Option>
          <Form.Select.Option value="Noop">Noop(不执行上传，只执行后处理)</Form.Select.Option>
        </Form.Select>
        <Form.Select
          field="lines"
          label="上传线路(lines)"
          extraText="b站上传线路选择，默认为自动模式，可手动切换为bda, bda2, ws, qn, bldsa, tx, txa"
          placeholder="AUTO(自动)(默认)"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        >
          <Form.Select.Option value="AUTO">AUTO(自动)(默认)</Form.Select.Option>
          <Form.Select.Option value="alia">alia(阿里云-海外线路)</Form.Select.Option>
          {/* <Form.Select.Option value="bda">bda</Form.Select.Option> */}
          <Form.Select.Option value="bda2">bda2(百度云-百度线路)</Form.Select.Option>
          <Form.Select.Option value="bldsa">bldsa(百度云-B站自建)</Form.Select.Option>
          <Form.Select.Option value="qn">qn(七牛-全牛网)</Form.Select.Option>
          <Form.Select.Option value="tx">tx(腾讯云-腾讯线路)</Form.Select.Option>
          <Form.Select.Option value="txa">txa(腾讯云-腾讯线路)</Form.Select.Option>
        </Form.Select>
        <Form.InputNumber
          field="threads"
          placeholder={3}
          extraText="上传文件线程数,未达到最大线程时,使用此值来限制上传速度(需要配合线路,推荐线路设置为8,速度不快请尝试其他上传线路)"
          label="上传线程数(threads)"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
        <Form.InputNumber
          field="max_upload_limit"
          placeholder={8}
          extraText="录制上传数量限制，防止因大量录制导致B站接口超载、录制文件过大导致录制失败或上传B站失败，注意这是指录制在队列中的，不是指同时上传数量，推荐设置为2-3个"
          label="上传数量限制(max_upload_limit)"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />

        <Form.InputNumber
          field="pool2_size"
          extraText={
            <div style={{ fontSize: '14px' }}>
              上传下载线程池大小，决定实际处理数量。
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>⚠️ 修改后需要重启服务才能生效</span>
            </div>
          }
          placeholder={3}
          label="上传线程池大小(pool2_size)"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
        />
        <Form.Switch
          field="use_live_cover"
          extraText={
            <div style={{ fontSize: '14px' }}>
              使用直播封面作为投稿封面。此方法优先级高于自定义封面，会自动下载cover文件到本地，上传后自动删除
              <br />
              目前支持平台：抖音、哔哩哔哩、Twitch、YouTube
            </div>
          }
          label="使用直播封面作为投稿封面(use_live_cover)"
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
        />
        <Form.Switch
          field="auto_restart"
          extraText={
            <div style={{ fontSize: '14px' }}>
              开启自动重启功能。当系统检测到录播和上传失败时，会自动重启对应的服务进程。
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>⚠️ 修改后需要重启服务才能生效</span>
              <br />
              <span style={{ color: 'var(--semi-color-text-2)' }}>开启后每30秒检测一次系统状态</span>
            </div>
          }
          label="自动重启(auto_restart)"
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
        />

        <Form.Input
          field="http_proxy"
          extraText={
            <div style={{ fontSize: '14px' }}>
              HTTP代理服务器地址，用于解决网络连接问题。
              <br />
              格式：http://127.0.0.1:7890
              <br />
              留空则不使用代理
            </div>
          }
          label="HTTP代理(http_proxy)"
          placeholder="http://127.0.0.1:7890"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
        <Form.Input
          field="https_proxy"
          extraText={
            <div style={{ fontSize: '14px' }}>
              HTTPS代理服务器地址，用于解决网络连接问题。
              <br />
              格式：http://127.0.0.1:7890
              <br />
              留空则不使用代理
            </div>
          }
          label="HTTPS代理(https_proxy)"
          placeholder="http://127.0.0.1:7890"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />

        <Form.InputNumber
          field="max_retry_count"
          extraText={
            <div style={{ fontSize: '14px' }}>
              上传失败重试次数，超过此次数则停止重试
              <br />
              默认值为 3 次
            </div>
          }
          label="上传重试次数(max_retry_count)"
          placeholder={3}
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />

        <Form.InputNumber
          field="max_retry_count_after_fail"
          extraText={
            <div style={{ fontSize: '14px' }}>
              上传失败后重试次数，超过此次数则停止重试
              <br />
              默认值为 3 次
            </div>
          }
          label="上传失败后重试次数(max_retry_count_after_fail)"
          placeholder={3}
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
      </div>
    </>
  )
}

export default Global
