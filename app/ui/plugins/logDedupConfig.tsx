'use client'
import React, { useEffect, useState } from 'react'
import {
  Form,
  InputNumber,
  CheckboxGroup,
  Input,
  Button,
  Toast,
  Spin,
  Typography,
  Banner
} from '@douyinfe/semi-ui'
import { IconSave, IconRefresh } from '@douyinfe/semi-icons'

interface LogDedupConfig {
  enabled: boolean
  threshold: number
  enabled_levels: string[]
  abbreviate_format: string
  reset_on_error: boolean
  reset_on_change: boolean
}

const defaultConfig: LogDedupConfig = {
  enabled: true,
  threshold: 4,
  enabled_levels: ['DEBUG', 'INFO', 'WARNING'],
  abbreviate_format: '... [重复 {count} 次] {content}',
  reset_on_error: true,
  reset_on_change: true
}

const logLevelOptions = [
  { label: 'DEBUG', value: 'DEBUG' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CRITICAL', value: 'CRITICAL' }
]

const LogDedupConfig: React.FC = () => {
  const [config, setConfig] = useState<LogDedupConfig>(defaultConfig)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  // formKey 在每次从服务端加载完成后递增，强制 Form 重新挂载以同步 Semi 内部状态
  const [formKey, setFormKey] = useState(0)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const isDev = process.env.NODE_ENV === 'development'
      const server = isDev
        ? process.env.NEXT_PUBLIC_API_SERVER
        : ''
      const response = await fetch(`${server}/v1/log-dedup/config`)
      if (response.ok) {
        const data = await response.json()
        setConfig({ ...defaultConfig, ...data })
        setFormKey(k => k + 1)
      }
    } catch (error) {
      console.error('加载配置失败:', error)
      Toast.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  const saveConfig = async () => {
    setSaving(true)
    try {
      const isDev = process.env.NODE_ENV === 'development'
      const server = isDev
        ? process.env.NEXT_PUBLIC_API_SERVER
        : ''
      const response = await fetch(`${server}/v1/log-dedup/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      })
      if (response.ok) {
        Toast.success('配置保存成功')
      } else {
        Toast.error('配置保存失败')
      }
    } catch (error) {
      console.error('保存配置失败:', error)
      Toast.error('保存配置失败')
    } finally {
      setSaving(false)
    }
  }

  const resetConfig = () => {
    setConfig(defaultConfig)
    setFormKey(k => k + 1)
    Toast.info('已重置为默认配置')
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div style={{ padding: 16 }}>
      <Typography.Title heading={5} style={{ marginBottom: 16 }}>
        日志去重配置
      </Typography.Title>

      <Banner
        type="info"
        description="当日志内容连续重复出现时，系统会自动合并显示，减少日志刷屏问题。"
        style={{ marginBottom: 16 }}
      />

      <Form
        key={formKey}
        labelPosition="left"
        labelWidth={200}
        style={{ width: '100%' }}
      >
        <Form.Switch
          field="enabled"
          label="启用日志去重"
          initValue={config.enabled}
          onChange={(checked) => setConfig(prev => ({ ...prev, enabled: checked as boolean }))}
        />

        <Form.InputNumber
          field="threshold"
          label="重复阈值（条）"
          min={2}
          max={20}
          initValue={config.threshold}
          disabled={!config.enabled}
          onChange={(value) => setConfig(prev => ({ ...prev, threshold: value as number }))}
          helpText="连续出现相同日志达到此数量后开始合并显示（1-20）"
        />

        <Form.CheckboxGroup
          field="enabled_levels"
          label="应用去重的日志等级"
          options={logLevelOptions}
          initValue={config.enabled_levels}
          disabled={!config.enabled}
          onChange={(value) => setConfig(prev => ({ ...prev, enabled_levels: value as string[] }))}
          direction="horizontal"
        />

        <Form.Input
          field="abbreviate_format"
          label="缩写格式模板"
          initValue={config.abbreviate_format}
          disabled={!config.enabled}
          onChange={(value) => setConfig(prev => ({ ...prev, abbreviate_format: value }))}
          helpText="使用 {count} 表示重复次数，{content} 表示日志内容"
          placeholder="... [重复 {count} 次] {content}"
        />

        <Form.Switch
          field="reset_on_error"
          label="ERROR日志重置计数"
          initValue={config.reset_on_error}
          disabled={!config.enabled}
          onChange={(checked) => setConfig(prev => ({ ...prev, reset_on_error: checked as boolean }))}
          helpText="收到ERROR等级日志时立即结束当前重复计数"
        />

        <Form.Switch
          field="reset_on_change"
          label="内容变化重置计数"
          initValue={config.reset_on_change}
          disabled={!config.enabled}
          onChange={(checked) => setConfig(prev => ({ ...prev, reset_on_change: checked as boolean }))}
          helpText="收到不同内容的日志时立即结束当前重复计数"
        />

        <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
          <Button
            type="primary"
            theme="solid"
            icon={<IconSave />}
            loading={saving}
            onClick={saveConfig}
          >
            保存配置
          </Button>
          <Button
            icon={<IconRefresh />}
            onClick={resetConfig}
          >
            重置默认
          </Button>
          <Button
            onClick={loadConfig}
          >
            刷新
          </Button>
        </div>
      </Form>

      <div style={{ marginTop: 24 }}>
        <Typography.Title heading={6}>预览效果</Typography.Title>
        <div
          style={{
            padding: 12,
            backgroundColor: 'var(--semi-color-bg-1)',
            borderRadius: 4,
            fontFamily: 'monospace',
            fontSize: 12,
            whiteSpace: 'pre-wrap'
          }}
        >
          <div>2024-01-01 12:00:00 INFO Room [xxx] status changed to Idle</div>
          <div>2024-01-01 12:00:01 INFO Room [xxx] status changed to Idle</div>
          <div>2024-01-01 12:00:02 INFO Room [xxx] status changed to Idle</div>
          <div style={{ color: 'var(--semi-color-warning)' }}>
            {config.abbreviate_format
              .replace('{count}', '5')
              .replace('{content}', 'Room [xxx] status changed to Idle')}
          </div>
          <div style={{ color: 'var(--semi-color-danger)' }}>2024-01-01 12:00:08 ERROR Connection failed</div>
        </div>
      </div>
    </div>
  )
}

export default LogDedupConfig
