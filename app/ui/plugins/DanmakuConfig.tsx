'use client'
import React from 'react'
import { Form, Select, Collapse } from '@douyinfe/semi-ui'

type DanmakuConfigProps = {
  prefix?: string
  platformName?: string
  inPanel?: boolean
}

const DanmakuConfigContent: React.FC<DanmakuConfigProps> = ({ prefix = '', platformName = '平台' }) => {
  const field = (name: string) => (prefix ? `${prefix}.${name}` : name)

  return (
    <>
      {/* 基础弹幕录制 */}
      <Form.Switch
        field={field('douyin_danmaku')}
        extraText={`录制${platformName}弹幕，默认关闭。开启后会同时启用弹幕处理功能。`}
        label="录制弹幕"
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
      />

      <Form.Select
        field={field('douyin_danmaku_types')}
        extraText={
          <div style={{ fontSize: '14px' }}>
            选择要录制的弹幕消息类型，为空则录制所有类型。
            <br />
            可选值：danmaku(弹幕)、like(点赞)、member(进场)、gift(礼物)、social(关注)、room_user_seq(统计)
          </div>
        }
        label="弹幕类型筛选"
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
        multiple
      >
        <Select.Option value="danmaku">弹幕消息</Select.Option>
        <Select.Option value="like">点赞消息</Select.Option>
        <Select.Option value="member">进场消息</Select.Option>
        <Select.Option value="gift">礼物消息</Select.Option>
        <Select.Option value="social">关注消息</Select.Option>
        <Select.Option value="room_user_seq">统计消息</Select.Option>
      </Form.Select>

      {/* ASS字幕生成 */}
      <Form.Switch
        field={field('danmaku_generate_ass')}
        extraText="生成ASS字幕文件，可用于视频合成或单独使用。"
        label="生成ASS字幕"
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
      />

      <Form.Input
        field={field('danmaku_ass_font')}
        extraText="ASS字幕使用的字体名称，如 Microsoft YaHei、SimHei 等。"
        label="字幕字体"
        placeholder="Microsoft YaHei"
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />

      <Form.InputNumber
        field={field('danmaku_ass_fontsize')}
        extraText="字幕字体大小，默认为25。"
        label="字体大小"
        placeholder={25}
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />

      <Form.Input
        field={field('danmaku_ass_color')}
        extraText="字幕颜色，BGR格式，默认为 00FFFFFF（白色）。"
        label="字幕颜色"
        placeholder="00FFFFFF"
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />

      <Form.InputNumber
        field={field('danmaku_ass_speed')}
        extraText="弹幕滚动速度（像素/帧），默认为8。数值越大速度越快。"
        label="弹幕速度"
        placeholder={8}
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />

      <Form.InputNumber
        field={field('danmaku_ass_line_count')}
        extraText="弹幕显示行数，默认为12行。"
        label="弹幕行数"
        placeholder={12}
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />

      {/* 视频合成 */}
      <Form.Switch
        field={field('danmaku_render_video')}
        extraText="使用FFmpeg将ASS字幕合成到视频中，生成带弹幕的视频文件。需要安装FFmpeg。"
        label="合成弹幕视频"
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
      />

      <Form.Switch
        field={field('danmaku_use_gpu')}
        extraText="使用NVIDIA GPU加速视频编码（NVENC），需要NVIDIA显卡支持。"
        label="使用GPU加速"
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
      />

      <Form.Select
        field={field('danmaku_video_codec')}
        extraText="视频编码器选择。使用GPU加速时自动使用h264_nvenc。"
        label="视频编码器"
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      >
        <Select.Option value="libx264">libx264 (CPU编码)</Select.Option>
        <Select.Option value="h264_nvenc">h264_nvenc (NVIDIA GPU)</Select.Option>
        <Select.Option value="h264_amf">h264_amf (AMD GPU)</Select.Option>
        <Select.Option value="h264_qsv">h264_qsv (Intel QuickSync)</Select.Option>
      </Form.Select>

      <Form.Select
        field={field('danmaku_preset')}
        extraText="编码预设，影响编码速度和文件大小。ultrafast最快但文件最大，veryslow最慢但文件最小。"
        label="编码预设"
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      >
        <Select.Option value="ultrafast">ultrafast (最快)</Select.Option>
        <Select.Option value="superfast">superfast</Select.Option>
        <Select.Option value="veryfast">veryfast</Select.Option>
        <Select.Option value="faster">faster</Select.Option>
        <Select.Option value="fast">fast</Select.Option>
        <Select.Option value="medium">medium (默认)</Select.Option>
        <Select.Option value="slow">slow</Select.Option>
        <Select.Option value="slower">slower</Select.Option>
        <Select.Option value="veryslow">veryslow (最小文件)</Select.Option>
      </Form.Select>

      <Form.InputNumber
        field={field('danmaku_crf')}
        extraText="视频质量因子，0-51，越小质量越好。默认23，18为 visually lossless。"
        label="质量因子(CRF)"
        placeholder={23}
        min={0}
        max={51}
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />

      {/* 高能检测 */}
      <Form.Switch
        field={field('danmaku_detect_energy')}
        extraText="根据弹幕密度自动检测直播高能时刻，生成高能区域JSON文件。"
        label="高能区域检测"
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
      />

      <Form.InputNumber
        field={field('danmaku_energy_window')}
        extraText="高能检测的时间窗口大小（秒），默认为30秒。"
        label="检测窗口"
        placeholder={30}
        suffix="秒"
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />

      <Form.InputNumber
        field={field('danmaku_energy_threshold')}
        extraText="高能阈值（0-1），默认为0.7。超过平均密度的(1+threshold)倍视为高能。"
        label="高能阈值"
        placeholder={0.7}
        min={0}
        max={1}
        step={0.1}
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />

      <Form.InputNumber
        field={field('danmaku_min_energy_duration')}
        extraText="最小高能持续时间（秒），默认为10秒。短于此时间的区域不视为高能。"
        label="最小持续时间"
        placeholder={10}
        suffix="秒"
        style={{ width: '100%' }}
        fieldStyle={{
          alignSelf: 'stretch',
          padding: 0,
        }}
        showClear={true}
      />
    </>
  )
}

const DanmakuConfig: React.FC<DanmakuConfigProps> = ({ prefix = '', platformName = '平台', inPanel = true }) => {
  if (inPanel) {
    return (
      <Collapse.Panel header="弹幕录制与处理" itemKey={`${prefix || 'global'}_danmaku`}>
        <DanmakuConfigContent prefix={prefix} platformName={platformName} inPanel={inPanel} />
      </Collapse.Panel>
    )
  }

  return <DanmakuConfigContent prefix={prefix} platformName={platformName} inPanel={inPanel} />
}

export default DanmakuConfig
