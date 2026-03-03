'use client'
import React, { useEffect } from 'react'
import styles from '../../styles/dashboard.module.scss'
import { Form, Select, Space, useFormApi } from '@douyinfe/semi-ui'
import { IconUpload, IconDownload } from '@douyinfe/semi-icons'

const Global: React.FC = () => {
  const formApi = useFormApi()

  return (
    <>
      {/* ȫ������ */}
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
          <p className={styles.meegoSharedWebWorkIt}>ȫ����������</p>
        </div>
        <Form.Select
          label="���ز����downloader��"
          field="downloader"
          placeholder="stream-gears��Ĭ�ϣ�"
          // initValue="stream-gears"
          extraText={
            <div style={{ fontSize: '14px' }}>
              ѡ��ȫ��Ĭ�ϵ����ز��, ��ѡ:
              <br />
              1. streamlink������ hls ������֧�ֵ��������˵� ffmpeg���� Docker �û������а�װ FFmpeg��
              <br />
              2. ffmpeg���� Docker �û������а�װ FFmpeg��
              <br />
              3. stream-gears��Ĭ�ϡ��� FLV ��������
              <br />
              4. sync-downloader����ʽ��¼�ߴ�������Ϊ�����趨�ϴ�ģ�塣����
              pool2/threads/segment_time ���ƣ�Ĭ�� 3 �߳��ϴ�����ȷ���ϴ��������㡣�� Docker �û������а�װ FFmpeg����� Wiki <a href="https://github.com/biliup/biliup/wiki/%E8%BE%B9%E5%BD%95%E8%BE%B9%E4%BC%A0%E5%8A%9F%E8%83%BD" target="_blank" rel="noopener noreferrer" >����鿴</a>
              <br />
              5. ytarchive���������� Youtube Live��
              <br />
              {/* 6. mesio������ Rust ����������Ƶ����/�޸�������� <a href="https://github.com/hua0512/rust-srec/tree/main/mesio-cli" target="_blank" rel="noopener noreferrer" >��Ŀ��ҳ</a> */}
            </div>
          }
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        >
          <Select.Option value="streamlink">streamlink��hls���߳����أ�</Select.Option>
          <Select.Option value="ffmpeg">ffmpeg</Select.Option>
          <Select.Option value="stream-gears">stream-gears��Ĭ�ϣ�</Select.Option>
          <Select.Option value="sync-downloader">sync-downloader����¼�ߴ���</Select.Option>
          <Select.Option value="ytarchive">ytarchive���������� Youtube Live��</Select.Option>
          {/* <Select.Option value="mesio">mesio</Select.Option> */}
        </Form.Select>
        {formApi.getValue('downloader') === 'sync-downloader' ? (
          <>
            <Form.Input
              field="sync_save_dir"
              label="��¼�ߴ����Ᵽ�汾��Ŀ¼��sync_save_dir��"
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
                  message: '·���в��ܰ���Windows���������ַ� * | ? " < >',
                },
                {
                  pattern: /^(?![a-zA-Z]��).*$/,
                  message: '����ĸ��ͷʱ���ڶ����ַ�����������ð��',
                },
                {
                  pattern: /^[^:]*$|^[a-zA-Z]:[\/\\][^:]*$/,
                  message: 'ð��ֻ�ܳ����ڵڶ����ַ�λ�ã��Һ����������б��',
                },
                {
                  pattern: /^(?!.*?\.{3,})(?!.*?\.{2}(?![\/\\])).*$/,
                  message: '������ֻ�������������Σ��Һ����������б��',
                },
                {
                  pattern: /^(?!.*\/\\)(?!.*\\\/).*$/,
                  message: '��������������б��',
                },
                {
                  pattern: /^(?!.*([\\]{3,}|[\/]{2,})).*$/,
                  message: '��б�����ֻ�������������Σ���б�����ֻ����������һ��',
                },
              ]}
              stopValidateWithError={true}
            />
          </>
        ) : null}
        <Form.InputNumber
          label="��Ƶ�ֶδ�С��file_size��"
          extraText={
            <div style={{ fontSize: '14px' }}>
              ¼���ļ���С���ƣ������˴�С�����ļ��ָ���ػط�ʱ�޷�ʹ�á�
              <br />
              ��λ��Byte��ʾ����4294967296��4GB��
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
              ¼���ļ�ʱ�����ƣ�������ʱ�������ļ��ָ
              <br />
              ��ʽ��&apos;00:00:00&apos;��ʱ:��:�룩
            </div>
          }
          label="��Ƶ�ֶ�ʱ����segment_time��"
          placeholder="01:00:00"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
          rules={[
            {
              pattern: /^[^��]*$/,
              message: '��ʹ��Ӣ��ð��',
            },
            {
              pattern: /^[0-9:]*$/,
              message: 'ֻ�������ֺ�Ӣ��ð��',
            },
            {
              pattern: /^[0-9]{2,4}:[0-5][0-9]:[0-5][0-9]$/,
              message: '�ֻ��벻���Ϲ淶',
            },
          ]}
          stopValidateWithError={true}
        />
        <Form.Input
          field="filename_prefix"
          extraText={
            <div style={{ fontSize: '14px' }}>
              ȫ���ļ���ģ�塣�ɱ����������ļ���ģ�帲�ǡ����ñ�������
              <br />
              {'\u007B'}streamer{'\u007D'}: ¼����ע�����뱣����
              <span style={{ margin: '0 20px' }}></span>
              {'\u007B'}title{'\u007D'}: ֱ������
              <br />
              %Y-%m-%d %H_%M_%S: ��ʼ¼��ʱ�� ��-��-�� ʱ_��_��
            </div>
          }
          label="�ļ���ģ�壨filename_prefix��"
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
          extraText={<div style={{ fontSize: '14px' }}>�������޷���֤�ֶκ����Ⱥ�ִ��˳��</div>}
          label="��Ƶ�ֶκ������У�segment_processor_parallel)"
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
        />
        <Form.InputNumber
          field="filtering_threshold"
          extraText={
            <div style={{ fontSize: '14px' }}>
              С�ڴ˴�С����Ƶ�ļ����ᱻ����ɾ����
              <br />
              ��λ��MB
            </div>
          }
          label="��Ƭ���ˣ�filtering_threshold��"
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
          label="�²��ӳټ�⣨delay)"
          extraText={
            <div style={{ fontSize: '14px' }}>
              ����⵽�����²����ӳ�һ��ʱ���ٴμ��ȷ�ϣ���������������������ϴ����·ָ����
              <br />
              ��λ����
              <br />
              Ĭ���ӳ�ʱ��Ϊ 0 ��
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>?? �޸ĺ���Ҫ�������ò�����Ч</span>
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
              ƽ̨�����ʱ�䣬��λ���롣���綶�����������������ȴ���ʱ����ȥ���¼�⡣
              <br />
              ��λ����
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>?? �޸ĺ���Ҫ�������ò�����Ч</span>
            </div>
          }
          label="ƽ̨�������event_loop_interval��"
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
              �������������ʱ�䣬��λ���롣���綶����10��������ÿ������������ʱ���⡣
              <br />
              ��������û�����Ϊ0����ʹ��ƽ̨�������event_loop_interval����
              <br />
              ��λ����
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>?? �޸ĺ���Ҫ�������ò�����Ч</span>
            </div>
          }
          label="���������������checker_sleep��"
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
              ���������¼����̳߳ش�С�������������ͬʱ¼������
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>?? �޸ĺ���Ҫ�������������Ч</span>
            </div>
          }
          placeholder={5}
          label="�����̳߳ش�С��pool1_size��"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        />
      </div>

      <Space />

      {/* ȫ���ϴ� */}
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
          <p className={styles.meegoSharedWebWorkIt}>ȫ���ϴ�����</p>
        </div>

        <Form.Select
          field="submit_api"
          label="�ύ�ӿڣ�submit_api��"
          extraText="BվͶ���ύ�ӿڣ�Ĭ��Ϊ�Զ�ѡ��"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        >
          <Form.Select.Option value="app">��׿APP��app��</Form.Select.Option>
          <Form.Select.Option value="b-cut-android">BCut��׿APP��b-cut-android��</Form.Select.Option>
          <Form.Select.Option value="web">��ҳ��web��</Form.Select.Option>
        </Form.Select>
        <Form.Select
          field="uploader"
          label="�ϴ������uploader��"
          extraText="ȫ��Ĭ���ϴ����ѡ��"
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
          <Form.Select.Option value="Noop">Noop�������ϴ�������ִ�к�����</Form.Select.Option>
        </Form.Select>
        <Form.Select
          field="lines"
          label="�ϴ���·��lines��"
          extraText="bվ�ϴ���·ѡ��Ĭ��Ϊ�Զ�ģʽ�����ֶ��л�Ϊbda, bda2, ws, qn, bldsa, tx, txa"
          placeholder="AUTO���Զ���Ĭ�ϣ�"
          style={{ width: '100%' }}
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
          showClear={true}
        >
          <Form.Select.Option value="AUTO">AUTO���Զ���Ĭ�ϣ�</Form.Select.Option>
          <Form.Select.Option value="alia">alia������-�����ƣ�</Form.Select.Option>
          {/* <Form.Select.Option value="bda">bda</Form.Select.Option> */}
          <Form.Select.Option value="bda2">bda2����½-�ٶ��ƣ�</Form.Select.Option>
          <Form.Select.Option value="bldsa">bldsa����½-Bվ�Խ���</Form.Select.Option>
          <Form.Select.Option value="qn">qn��ȫ��-��ţ��</Form.Select.Option>
          <Form.Select.Option value="tx">tx����½-��Ѷ�ƣ�</Form.Select.Option>
          <Form.Select.Option value="txa">txa������-��Ѷ�ƣ�</Form.Select.Option>
        </Form.Select>
        <Form.InputNumber
          field="threads"
          placeholder={3}
          extraText="���ļ������ϴ���,δ�ﵽ��������ʱ,�����ֵ������ϴ��ٶ�(��Ҫ���ù���,������·����Ϊ8,���ٶȲ������ȵ����ϴ���·)"
          label="�ϴ�������threads��"
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
          extraText="¼���ϴ��������ޣ���ֹ�����������Bվ�ӿڳ�硢¼�������𻵵���¼�������ϴ��˷ѿ�����Bվ��أ�ע�������Ǽ�¼�ڳ����������еģ���������������ϴ��������ƣ���Ϊ�˱�֤�������Ķ����û�ʹ���߼���Ĭ�Ͻ���ֵ����Ϊһ���ϴ��ֵ��һ���Ƽ�����Ϊ2-3��"
          label="�ϴ����Դ������ƣ�max_upload_limit��"
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
              �����ϴ��¼����̳߳ش�С������ʵ�ʴ������á�
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>?? �޸ĺ���Ҫ�������������Ч</span>
            </div>
          }
          placeholder={3}
          label="�ϴ��̳߳ش�С��pool2_size��"
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
              ʹ��ֱ���������ΪͶ����档�˷������ȼ����ڵ�������ָ�����Զ�����棬������cover�ļ����£��ϴ����Զ�ɾ����
              <br />
              Ŀǰ֧��ƽ̨����������������������Twitch��YouTube��
            </div>
          }
          label="ʹ��ֱ���������ΪͶ����棨use_live_cover)"
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
        />
        <Form.Switch
          field="auto_restart"
          extraText={
            <div style={{ fontSize: '14px' }}>
              �����Զ��������ܡ���ϵͳ��⵽���У���¼�ƺ��ϴ�����ʱ�����Զ�����������Ӧ�������á�
              <br />
              <span style={{ color: 'var(--semi-color-warning)' }}>?? �޸ĺ���Ҫ�������������Ч</span>
              <br />
              <span style={{ color: 'var(--semi-color-text-2)' }}>�������ÿ���Ӽ��һ��ϵͳ״̬</span>
            </div>
          }
          label="�Զ�������auto_restart��"
          fieldStyle={{
            alignSelf: 'stretch',
            padding: 0,
          }}
        />
        
        <Form.Input
          field="http_proxy"
          extraText={
            <div style={{ fontSize: '14px' }}>
              HTTP������ַ�����ڽ���������绷���µ��������⡣
              <br />
              ��ʽ��http://127.0.0.1:7890
              <br />
              ������ʹ�ô���
            </div>
          }
          label="HTTP������http_proxy��"
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
              HTTPS������ַ�����ڽ���������绷���µ��������⡣
              <br />
              ��ʽ��http://127.0.0.1:7890
              <br />
              ������ʹ�ô���
            </div>
          }
          label="HTTPS������https_proxy��"
          placeholder="http://127.0.0.1:7890"
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

