'use client'
import React, { useEffect } from 'react'
import styles from '../../styles/dashboard.module.scss'
import { Form, Select, Space, useFormApi } from '@douyinfe/semi-ui'
import { IconUpload, IconDownload } from '@douyinfe/semi-icons'

const Global: React.FC = () => {
  const formApi = useFormApi()

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
        <Form.InputNumber
          label="视频分段大小(file_size)"
          extraText={
            <div style={{ fontSize: '14px' }}>
              录制文件大小限制，超过此大小将文件分割。下载回放时无法使用。
              <br />
              单位以Byte表示，例如4294967296(4GB)
            </div>
          }
          field="file_size"
          placeholder=""
          suffix={'Byte'}
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
        />
        <Form.Input
          field="segment_time"
          extraText={
            <div style={{ fontSize: '14px' }}>
              录制文件时间限制，超过此时间将文件分割。
              <br />
              格式为'00:00:00'(时:分:秒)
            </div>
          }
          label="视频分段时间(segment_time)"
          placeholder="01:00:00"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
          rules={[
            {
              pattern: /^[^\u4e00-\u9fa5]*$/,
              message: '不能使用中文冒号',
            },
            {
              pattern: /^[0-9:]*$/,
              message: '只能包含数字和英文冒号',
            },
            {
              pattern: /^[0-9]{2,4}:[0-5][0-9]:[0-5][0-9]$/,
              message: '时间格式不符合规范',
            },
          ]}
          stopValidateWithError={true}
        />
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