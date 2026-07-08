'use client'
import React, { useEffect, useMemo, useState } from 'react'
import {
  Form,
  Select,
  Collapse,
  useFormApi,
  Button,
  Space,
  Tag,
  Typography,
  Banner,
  InputNumber,
  Switch,
  Tooltip,
  Card,
  Row,
  Col,
  Spin,
} from '@douyinfe/semi-ui'
import {
  IconHelpCircle,
  IconRefresh,
  IconVerify,
  IconWrench,
  IconLive,
  IconVideo,
} from '@douyinfe/semi-icons'
import DanmakuConfig from './DanmakuConfig'

type Props = {
  entity: any
  list: any
  initValues?: Record<string, any>
}

const QUALITY_OPTIONS = [
  { value: 'origin', label: '原画', resolution: '最高可用分辨率', warning: '可能为 HEVC' },
  { value: 'uhd', label: '蓝光', resolution: '1920×1080 左右', warning: '' },
  { value: 'hd', label: '超清', resolution: '1280×720 左右', warning: '' },
  { value: 'sd', label: '高清', resolution: '960×540 左右', warning: '' },
  { value: 'ld', label: '标清', resolution: '640×360 左右', warning: '' },
  { value: 'md', label: '流畅', resolution: '480×272 左右', warning: '' },
]

const URL_PATTERNS = [
  {
    label: '网页直播间',
    example: 'https://live.douyin.com/123456',
    color: 'blue',
    cookie: false,
  },
  {
    label: '分享链接',
    example: 'https://v.douyin.com/xxxxx',
    color: 'green',
    cookie: false,
  },
  {
    label: '用户主页',
    example: 'https://www.douyin.com/user/MS4wLjABxxxxx',
    color: 'orange',
    cookie: true,
  },
]

const COOKIE_FIELDS = [
  { key: 'sessionid', required: true, desc: '抖音登录态，必备' },
  { key: '__ac_nonce', required: true, desc: '反爬虫参数，必备' },
  { key: '__ac_signature', required: true, desc: '签名参数，必备' },
  { key: 'ttwid', required: false, desc: '访客 ID，通常自动补全' },
  { key: 'odin_ttid', required: false, desc: '设备标识，通常自动补全' },
]

const Douyin: React.FC<Props> = props => {
  const { initValues } = props
  const formApi = useFormApi()
  const [checking, setChecking] = useState(false)
  const [cookieStatus, setCookieStatus] = useState<'none' | 'valid' | 'invalid'>('none')

  useEffect(() => {
    if (initValues) {
      Object.entries(initValues).forEach(([key, value]) => {
        formApi.setValue(key, value)
      })
    }
  }, [initValues, formApi])

  const cookieValue = formApi.getValue('user.douyin_cookie') || ''

  const checkCookie = async () => {
    if (!cookieValue) {
      setCookieStatus('invalid')
      return
    }
    setChecking(true)
    try {
      // 前端格式校验：检查是否包含关键字段
      const required = ['sessionid', '__ac_nonce', '__ac_signature']
      const missing = required.filter(k => !cookieValue.includes(k))
      if (missing.length > 0) {
        setCookieStatus('invalid')
      } else {
        setCookieStatus('valid')
      }
    } finally {
      // 模拟网络延迟，给用户反馈
      setTimeout(() => setChecking(false), 400)
    }
  }

  const statusTag = useMemo(() => {
    switch (cookieStatus) {
      case 'valid':
        return <Tag color="green" type="light">Cookie 格式有效</Tag>
      case 'invalid':
        return <Tag color="red" type="light">Cookie 格式不完整</Tag>
      default:
        return <Tag color="grey" type="light">未检测</Tag>
    }
  }, [cookieStatus])

  const selectedQuality = formApi.getValue('douyin_quality') || 'origin'

  return (
    <>
      <Collapse.Panel header="抖音" itemKey="douyin">
        {/* 顶部平台状态栏 */}
        <Card
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 12 }}
          shadows="hover"
        >
          <Row type="flex" justify="space-between" align="middle">
            <Col>
              <Space>
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: '50%',
                    backgroundColor: '#00b578',
                    boxShadow: '0 0 0 4px rgba(0,181,120,0.2)',
                  }}
                />
                <Typography.Text strong>抖音平台状态</Typography.Text>
                <Tag color="green">已启用</Tag>
                {cookieStatus === 'valid' ? (
                  <Tag color="blue">Cookie 已配置</Tag>
                ) : cookieStatus === 'invalid' ? (
                  <Tag color="red">Cookie 异常</Tag>
                ) : (
                  <Tag color="grey">Cookie 未检测</Tag>
                )}
              </Space>
            </Col>
            <Col>
              <Typography.Text type="tertiary" size="small">
                检测间隔: {formApi.getValue('douyin_check_interval') || formApi.getValue('checker_sleep') || 10} 秒
              </Typography.Text>
            </Col>
          </Row>
        </Card>

        {/* Cookie 与认证 */}
        <Card
          title="Cookie 与认证"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 16 }}
        >
          <Banner
            type="warning"
            fullMode={false}
            description="如录制 www.douyin.com/user/ 类型链接或遇到 403/风控，请配置 Cookie。只需填入关键字段，不要粘贴全部 Cookie。"
            style={{ marginBottom: 16 }}
          />
          <Row gutter={16} type="flex" align="middle" style={{ marginBottom: 12 }}>
            <Col span={18}>
              <Form.Input
                field="user.douyin_cookie"
                placeholder="sessionid=xxx; __ac_nonce=xxx; __ac_signature=xxx;"
                label="抖音 Cookie"
                style={{ width: '100%' }}
                fieldStyle={{
                  alignSelf: 'stretch',
                  padding: 0,
                }}
                showClear={true}
              />
            </Col>
            <Col span={6} style={{ paddingTop: 24 }}>
              <Space>
                <Button
                  icon={<IconVerify />}
                  loading={checking}
                  onClick={checkCookie}
                  theme={cookieStatus === 'valid' ? 'solid' : 'light'}
                  type={cookieStatus === 'valid' ? 'primary' : 'tertiary'}
                >
                  检测格式
                </Button>
                {checking ? <Spin size="small" /> : statusTag}
              </Space>
            </Col>
          </Row>

          <div style={{ marginBottom: 12 }}>
            <Typography.Text type="secondary" size="small">
              字段说明（点击复制名称）：
            </Typography.Text>
            <Space wrap style={{ marginTop: 8 }}>
              {COOKIE_FIELDS.map(f => (
                <Tooltip key={f.key} content={f.desc} position="top">
                  <Tag
                    color={f.required ? 'red' : 'grey'}
                    type="light"
                    style={{ cursor: 'help' }}
                  >
                    {f.key} {f.required ? '（必填）' : '（自动）'}
                  </Tag>
                </Tooltip>
              ))}
            </Space>
          </div>

          <Banner
            type="danger"
            fullMode={false}
            closeIcon={null}
            description={
              <div>
                <Typography.Text strong>遇到 403 / 风控 / 验证码？</Typography.Text>
                <ol style={{ margin: '8px 0', paddingLeft: 18 }}>
                  <li>确认 Cookie 未过期，关键字段齐全</li>
                  <li>减少检测频率（建议抖音独立间隔 ≥ 15 秒）</li>
                  <li>避免同一 IP 多实例同时请求抖音</li>
                  <li>如仍失败，请使用浏览器无痕模式重新登录并提取 Cookie</li>
                </ol>
              </div>
            }
            style={{ marginTop: 12 }}
          />
        </Card>

        {/* URL 格式说明 */}
        <Card
          title="支持的 URL 格式"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 16 }}
        >
          <Space wrap>
            {URL_PATTERNS.map(u => (
              <Card
                key={u.label}
                bodyStyle={{ padding: 12 }}
                style={{ width: 220 }}
                shadows="hover"
              >
                <Space vertical align="start">
                  <Tag color={u.color as any}>{u.label}</Tag>
                  <Typography.Text
                    size="small"
                    copyable
                    style={{ wordBreak: 'break-all' }}
                  >
                    {u.example}
                  </Typography.Text>
                  {u.cookie ? (
                    <Tag color="orange" type="light" size="small">
                      需要 Cookie
                    </Tag>
                  ) : (
                    <Tag color="green" type="light" size="small">
                      无需 Cookie
                    </Tag>
                  )}
                </Space>
              </Card>
            ))}
          </Space>
        </Card>

        {/* 画质与协议 */}
        <Card
          title="画质与协议"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 16 }}
        >
          <Typography.Text type="secondary" size="small" style={{ display: 'block', marginBottom: 12 }}>
            选择优先录制的画质。若直播间未提供目标画质，会自动选择相近的较低清晰度。
          </Typography.Text>
          <Row gutter={12}>
            {QUALITY_OPTIONS.map(q => (
              <Col key={q.value} span={8} style={{ marginBottom: 12 }}>
                <div
                  onClick={() => formApi.setValue('douyin_quality', q.value)}
                  style={{
                    padding: 12,
                    cursor: 'pointer',
                    borderRadius: 'var(--semi-border-radius-medium)',
                    border:
                      selectedQuality === q.value
                        ? '1px solid var(--semi-color-primary)'
                        : '1px solid var(--semi-color-border)',
                    backgroundColor:
                      selectedQuality === q.value
                        ? 'rgba(var(--semi-blue-0), 1)'
                        : 'var(--semi-color-bg-0)',
                    transition: 'border-color 0.2s, background-color 0.2s',
                  }}
                >
                  <Space vertical align="start" spacing="tight">
                    <Typography.Text strong>{q.label}</Typography.Text>
                    <Typography.Text type="tertiary" size="small">
                      {q.resolution}
                    </Typography.Text>
                    {q.warning && (
                      <Tag color="orange" type="light" size="small">
                        {q.warning}
                      </Tag>
                    )}
                  </Space>
                </div>
              </Col>
            ))}
          </Row>
          <Form.Select
            field="douyin_quality"
            noLabel={true}
            style={{ display: 'none' }}
            showClear={false}
          >
            {QUALITY_OPTIONS.map(q => (
              <Select.Option key={q.value} value={q.value}>
                {q.label}
              </Select.Option>
            ))}
          </Form.Select>

          <div style={{ marginTop: 16 }}>
            <Typography.Text strong style={{ display: 'block', marginBottom: 8 }}>
              直播流协议
            </Typography.Text>
            <Space>
              <Tag
                color={formApi.getValue('douyin_protocol') !== 'hls' ? 'blue' : 'grey'}
                type={formApi.getValue('douyin_protocol') !== 'hls' ? 'solid' : 'light'}
                style={{ cursor: 'pointer' }}
                onClick={() => formApi.setValue('douyin_protocol', 'flv')}
              >
                FLV（推荐）
              </Tag>
              <Tooltip content="HLS 仅供测试，可能不稳定，且切换后部分播放器兼容性变差">
                <Tag
                  color={formApi.getValue('douyin_protocol') === 'hls' ? 'blue' : 'grey'}
                  type={formApi.getValue('douyin_protocol') === 'hls' ? 'solid' : 'light'}
                  style={{ cursor: 'pointer' }}
                  onClick={() => formApi.setValue('douyin_protocol', 'hls')}
                >
                  HLS（仅供测试）
                </Tag>
              </Tooltip>
            </Space>
            <Form.Select field="douyin_protocol" noLabel={true} style={{ display: 'none' }} showClear={false}>
              <Select.Option value="flv">flv</Select.Option>
              <Select.Option value="hls">hls</Select.Option>
            </Form.Select>
          </div>
        </Card>

        {/* 双屏直播录制 */}
        <Card
          title="双屏直播录制"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 16 }}
        >
          <Row gutter={24} type="flex" align="middle">
            <Col span={12}>
              <Form.Switch
                field="douyin_double_screen"
                extraText="开启后录制纵像素不变的原像素拼接流；关闭时录制横像素不变的缩放拼接流，可能存在画质损失。"
                label="录制原像素双屏流"
                fieldStyle={{
                  alignSelf: 'stretch',
                  padding: 0,
                }}
              />
            </Col>
            <Col span={12}>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '2fr 1fr',
                  gap: 4,
                  padding: 12,
                  background: 'var(--semi-color-fill-0)',
                  borderRadius: 8,
                  height: 80,
                }}
              >
                <div
                  style={{
                    background: 'rgba(var(--semi-blue-3), 0.6)',
                    borderRadius: 4,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    fontSize: 12,
                  }}
                >
                  主画面
                </div>
                <div
                  style={{
                    background: 'rgba(var(--semi-green-3), 0.6)',
                    borderRadius: 4,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    fontSize: 12,
                  }}
                >
                  副画面
                </div>
              </div>
              <Typography.Text
                type="tertiary"
                size="small"
                style={{ display: 'block', marginTop: 8, textAlign: 'center' }}
              >
                双屏布局示意：主画面 + 副画面拼接
              </Typography.Text>
            </Col>
          </Row>
        </Card>

        {/* 真原画 */}
        <Card
          title="真原画"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 16 }}
        >
          <Form.Switch
            field="douyin_true_origin"
            extraText="仅限 FLV 协议生效。开启后可能录制到 HEVC 编码，stream-gears（默认下载器）暂不支持，请切换为 ffmpeg / streamlink 后再录制。"
            label="抖音真原画"
            fieldStyle={{
              alignSelf: 'stretch',
              padding: 0,
            }}
          />
          {formApi.getValue('douyin_true_origin') && (
            <Banner
              type="danger"
              fullMode={false}
              description="已开启真原画，请确保下载器切换为 ffmpeg 或 streamlink，否则可能出现录制失败。"
              style={{ marginTop: 12 }}
            />
          )}
        </Card>

        {/* 检测间隔 */}
        <Card
          title="抖音检测频率"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 16 }}
        >
          <Form.InputNumber
            field="douyin_check_interval"
            extraText="抖音风控较严，建议设置为 15–20 秒。留空则使用全局「检测间隔(checker_sleep)」。"
            label="抖音独立检测间隔（秒）"
            placeholder={15}
            min={5}
            max={300}
            style={{ width: '100%' }}
            fieldStyle={{
              alignSelf: 'stretch',
              padding: 0,
            }}
            showClear={true}
          />
        </Card>

        {/* 弹幕配置 */}
        <Card
          title="弹幕录制"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: 16 }}
        >
          <DanmakuConfig platformName="抖音" inPanel={false} />
        </Card>
      </Collapse.Panel>
    </>
  )
}

export default Douyin
