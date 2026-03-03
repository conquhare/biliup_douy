use crate::server::core::downloader::DownloaderType;
use crate::server::errors::{AppError, AppResult};
use crate::server::infrastructure::models::hook_step::HookStep;
use biliup::bilibili::Credit;
use error_stack::bail;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, path::Path, path::PathBuf};
use struct_patch::Patch;

/// ȫ�����ýṹ��
#[derive(bon::Builder, Debug, PartialEq, Clone, Serialize, Deserialize, Patch)]
#[patch(attribute(derive(Debug, Clone, Default, Deserialize, Serialize)))]
pub struct Config {
    // ===== ȫ��¼�����ϴ����� =====
    /// ���������ͣ�streamlink | ffmpeg | stream-gears | �Զ���
    #[serde(default)]
    pub downloader: Option<DownloaderType>,

    /// �ļ���С���ƣ��ֽڣ�
    #[builder(default = default_file_size())]
    #[serde(default = "default_file_size")]
    pub file_size: u64,

    /// �ֶ�ʱ�䣬��ʽ�� "00:00:00"������Ϊ�ַ����Ա���ֱ��
    #[serde(default = "default_segment_time")]
    pub segment_time: Option<String>,

    /// ������ֵ��MB��
    #[builder(default = default_filtering_threshold())]
    #[serde(default = "default_filtering_threshold")]
    pub filtering_threshold: u64,

    /// �ļ���ǰ׺
    #[serde(default)]
    pub filename_prefix: Option<String>,

    /// �ֶδ������Ƿ���ִ��
    #[serde(default)]
    pub segment_processor_parallel: Option<bool>,

    /// �ϴ������ͣ�Noop | bili_web | biliup-rs | ����
    #[serde(default)]
    pub uploader: Option<String>,

    /// �ύAPI���ͣ�web | client
    #[serde(default)]
    pub submit_api: Option<String>,

    /// �ϴ���·��AUTO | alia | bda2 | bldsa | qn | tx | txa
    #[builder(default = default_lines())]
    #[serde(default = "default_lines")]
    pub lines: String,

    /// �ϴ��߳���
    #[builder(default = default_threads())]
    #[serde(default = "default_threads")]
    pub threads: u32,

    /// �ӳ�ʱ�䣨�룩
    #[builder(default = default_delay())]
    #[serde(default = "default_delay")]
    pub delay: u64,

    /// �¼�ѭ��������룩
    #[builder(default = default_event_loop_interval())]
    #[serde(default = "default_event_loop_interval")]
    pub event_loop_interval: u64,

    /// ���������ʱ�䣨�룩
    #[builder(default = default_checker_sleep())]
    #[serde(default = "default_checker_sleep")]
    pub checker_sleep: u64,

    /// ���ӳ�1��С
    #[builder(default = default_pool1_size())]
    #[serde(default = "default_pool1_size")]
    pub pool1_size: u32,

    /// �Զ��������أ���ϵͳ����ʱ�Զ���������
    #[builder(default = default_auto_restart())]
    #[serde(default = "default_auto_restart")]
    pub auto_restart: bool,

    /// ���ӳ�2��С
    #[builder(default = default_pool2_size())]
    #[serde(default = "default_pool2_size")]
    pub pool2_size: u32,

    // ===== ��ƽ̨¼������ =====
    /// �Ƿ�ʹ��ֱ������
    #[serde(default)]
    pub use_live_cover: Option<bool>,

    // ����ƽ̨����
    /// ����CDN�ڵ�
    #[serde(default)]
    pub douyu_cdn: Option<String>,
    /// ���㵯Ļ¼��
    #[serde(default)]
    pub douyu_danmaku: Option<bool>,
    /// ��������
    #[serde(default)]
    pub douyu_rate: Option<u32>,

    // ����ƽ̨����
    /// ����CDN�ڵ�
    #[serde(default)]
    pub huya_cdn: Option<String>,
    /// ����CDN����
    #[serde(default)]
    pub huya_cdn_fallback: Option<bool>,
    /// ������Ļ¼��
    #[serde(default)]
    pub huya_danmaku: Option<bool>,
    /// ����������
    #[serde(default)]
    pub huya_max_ratio: Option<u32>,
    /// ���� Flv or Hls
    #[serde(default)]
    pub huya_protocol: Option<String>,

    // ����ƽ̨����
    /// ������Ļ¼��
    #[serde(default)]
    pub douyin_danmaku: Option<bool>,
    /// ��������
    #[serde(default)]
    pub douyin_quality: Option<String>,
    /// ˫��ֱ��¼�Ʒ�ʽ
    #[serde(default)]
    pub douyin_double_screen: Option<bool>,
    /// ������ԭ��
    #[serde(default)]
    pub douyin_true_origin: Option<bool>,
    /// ������Ļ��Ϣ����ɸѡ��Ϊ����¼���������ͣ�
    /// ��ѡֵ: danmaku(��Ļ), like(����), member(����), gift(����), social(��ע), room_user_seq(ͳ��)
    #[serde(default)]
    pub douyin_danmaku_types: Option<Vec<String>>,

    // ��������ƽ̨����
    /// Bվ��Ļ¼��
    #[serde(default)]
    pub bilibili_danmaku: Option<bool>,
    /// Bվ��Ļ��ϸ��Ϣ
    #[serde(default)]
    pub bilibili_danmaku_detail: Option<bool>,
    /// Bվ��Ļԭʼ����
    #[serde(default)]
    pub bilibili_danmaku_raw: Option<bool>,
    /// BվЭ�����ͣ�stream | hls_ts | hls_fmp4
    #[serde(default)]
    pub bili_protocol: Option<String>,
    /// BվCDN�ڵ��б�
    #[serde(default)]
    pub bili_cdn: Option<Vec<String>>,
    /// Bվǿ��ԭ��
    #[serde(default)]
    pub bili_force_source: Option<bool>,
    /// Bվֱ��API
    #[serde(default)]
    pub bili_liveapi: Option<String>,
    /// Bվ����API
    #[serde(default)]
    pub bili_fallback_api: Option<String>,
    /// BվCDN����
    #[serde(default)]
    pub bili_cdn_fallback: Option<bool>,
    /// Bվcn01�ڵ��滻
    #[serde(default)]
    pub bili_replace_cn01: Option<Vec<String>>,
    /// Bվ���ʱ��
    #[serde(default)]
    pub bili_qn: Option<u32>,
    /// Bվ���¼ԭ��
    #[serde(default)]
    pub bili_anonymous_origin: Option<bool>,

    // YouTubeƽ̨����
    /// YouTube��ѡ��Ƶ����
    #[serde(default)]
    pub youtube_prefer_vcodec: Option<String>,
    /// YouTube��ѡ��Ƶ����
    #[serde(default)]
    pub youtube_prefer_acodec: Option<String>,
    /// YouTube���ֱ���
    #[serde(default)]
    pub youtube_max_resolution: Option<u32>,
    /// YouTube�����Ƶ��С
    #[serde(default)]
    pub youtube_max_videosize: Option<String>,
    /// YouTube��ʼ����
    #[serde(default)]
    pub youtube_after_date: Option<String>,
    /// YouTube��������
    #[serde(default)]
    pub youtube_before_date: Option<String>,
    /// YouTube����ֱ������
    #[serde(default)]
    pub youtube_enable_download_live: Option<bool>,
    /// YouTube���ûط�����
    #[serde(default)]
    pub youtube_enable_download_playback: Option<bool>,

    // Twitchƽ̨����
    /// Twitch��Ļ¼��
    #[serde(default)]
    pub twitch_danmaku: Option<bool>,
    /// Twitch���ù��
    #[serde(default)]
    pub twitch_disable_ads: Option<bool>,

    // TwitCastingƽ̨����
    /// TwitCasting��Ļ¼��
    #[serde(default)]
    pub twitcasting_danmaku: Option<bool>,
    /// TwitCasting����
    #[serde(default)]
    pub twitcasting_password: Option<String>,

    /// ¼����������ӳ��
    #[serde(default)]
    pub streamers: HashMap<String, StreamerConfig>,

    /// �û�Cookie����
    #[serde(default)]
    pub user: Option<UserConfig>,

    pub loggers_level: Option<String>,
    
    // ===== ����������� =====
    /// HTTP������ַ���� http://127.0.0.1:7890��
    #[serde(default)]
    pub http_proxy: Option<String>,
    /// HTTPS������ַ���� http://127.0.0.1:7890��
    #[serde(default)]
    pub https_proxy: Option<String>,
}

/// �������ýṹ��
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize, Default)]
pub struct StreamerConfig {
    /// ֱ����URL�б�
    pub url: Vec<String>,

    /// ��Ƶ����
    #[serde(default)]
    pub title: Option<String>,

    /// ����ID
    #[serde(default)]
    pub tid: Option<u32>,

    /// ��Ȩ����
    #[serde(default)]
    pub copyright: Option<u8>,

    /// ����·��
    #[serde(default)]
    pub cover_path: Option<PathBuf>,

    /// ��Ƶ���������������Ͷ��и�ʽ��
    #[serde(default)]
    pub description: Option<String>,

    #[serde(default)]
    pub credits: Option<Vec<Credit>>,

    #[serde(default)]
    pub dynamic: Option<String>,

    #[serde(default)]
    pub dtime: Option<u64>,

    #[serde(default)]
    pub dolby: Option<u8>,

    #[serde(default)]
    pub hires: Option<u8>,

    #[serde(default)]
    pub charging_pay: Option<u8>,

    #[serde(default)]
    pub no_reprint: Option<u8>,

    #[serde(default)]
    pub is_only_self: Option<u8>,

    #[serde(default)]
    pub uploader: Option<String>,

    #[serde(default)]
    pub filename_prefix: Option<String>,

    #[serde(default)]
    pub user_cookie: Option<String>,

    #[serde(default)]
    pub use_live_cover: Option<bool>,

    #[serde(default)]
    pub tags: Option<Vec<String>>,

    #[serde(default)]
    pub time_range: Option<String>,

    #[serde(default)]
    pub excluded_keywords: Option<Vec<String>>,

    #[serde(default)]
    pub preprocessor: Option<Vec<HookStep>>,

    #[serde(default)]
    pub segment_processor: Option<Vec<HookStep>>,

    #[serde(default)]
    pub downloaded_processor: Option<Vec<HookStep>>,

    #[serde(default)]
    pub postprocessor: Option<Vec<HookStep>>,

    #[serde(default)]
    pub format: Option<String>,

    #[serde(default)]
    pub opt_args: Option<Vec<String>>,

    // ��override�� ���ֶ����������Ϊ override_cfg �����뱣���ֻ���
    #[serde(rename = "override", default)]
    pub override_cfg: Option<HashMap<String, serde_json::Value>>,
}

/// �û����ýṹ��
#[derive(bon::Builder, PartialEq, Debug, Clone, Serialize, Deserialize, Default, Patch)]
#[patch(attribute(derive(Debug, Default, Deserialize)))]
pub struct UserConfig {
    // Bվ����
    /// BվCookie�ַ���
    #[serde(default)]
    pub bili_cookie: Option<String>,
    /// BվCookie�ļ�·��
    #[serde(default)]
    pub bili_cookie_file: Option<PathBuf>,

    // ��������
    /// ����Cookie
    #[serde(default)]
    pub douyin_cookie: Option<String>,

    // Twitch����
    /// Twitch Cookie
    #[serde(default)]
    pub twitch_cookie: Option<String>,

    // YouTube����
    /// YouTube Cookie�ļ�·��
    #[serde(default)]
    pub youtube_cookie: Option<PathBuf>,

    // Niconico���ã�ʹ��rename�����������ļ�һ�£�
    /// Niconico����
    #[serde(rename = "niconico-email", default)]
    pub niconico_email: Option<String>,
    /// Niconico����
    #[serde(rename = "niconico-password", default)]
    pub niconico_password: Option<String>,
    /// Niconico�û��Ự
    #[serde(rename = "niconico-user-session", default)]
    pub niconico_user_session: Option<String>,
    /// Niconico���ƾ��
    #[serde(rename = "niconico-purge-credentials", default)]
    pub niconico_purge_credentials: Option<String>,

    // AfreecaTV����
    /// AfreecaTV�û���
    #[serde(default)]
    pub afreecatv_username: Option<String>,
    /// AfreecaTV����
    #[serde(default)]
    pub afreecatv_password: Option<String>,
}

/// Ĭ���ļ���С��2.5GB
fn default_file_size() -> u64 {
    2_621_440_000
}

/// Ĭ�Ϸֶ�ʱ�䣺2Сʱ
pub fn default_segment_time() -> Option<String> {
    Some("02:00:00".to_string())
}

/// Ĭ�Ϲ�����ֵ��20MB
fn default_filtering_threshold() -> u64 {
    20
}

/// Ĭ���ϴ���·���Զ�ѡ��
fn default_lines() -> String {
    "AUTO".to_string()
}

/// Ĭ���߳�����3
fn default_threads() -> u32 {
    3
}

/// Ĭ���ӳ٣�300��
fn default_delay() -> u64 {
    300
}

/// Ĭ���¼�ѭ�������30��
fn default_event_loop_interval() -> u64 {
    30
}

/// Ĭ�ϼ��������ʱ�䣺10��
fn default_checker_sleep() -> u64 {
    10
}

/// Ĭ�����ӳ�1��С��5
fn default_pool1_size() -> u32 {
    5
}

/// Ĭ�����ӳ�2��С��3
fn default_pool2_size() -> u32 {
    3
}

/// Ĭ���Զ��������ر�
fn default_auto_restart() -> bool {
    false
}

impl Config {
    /// ��ָ��·�����������ļ�������������򴴽�Ĭ������
    pub fn load_or_create<P: AsRef<Path>>(path: P) -> AppResult<Self> {
        bail!(AppError::Custom(format!(
            "load_or_create: {:?}",
            path.as_ref().display()
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // ��� 1: �ֶδ��������ַ���ֵ
    #[test]
    fn test_field_with_value() {
        let json = r#"{"maybe_name": "Alice"}"#;

        let patch = r#"{"maybe_name": "Alice"}"#;

        // Single Option: Some("Alice")
        let mut single: Config = serde_json::from_str(json).unwrap();

        let patch: ConfigPatch = serde_json::from_str(json).unwrap();

        single.apply(patch);

        // �� JSON �����л�ʱ,δָ�����ֶ�ʹ�� serde default (None)
        // �� builder �� default �� Some("02:00:00"),���߲�ͬ
        // ��Ҫ��ȷ���� segment_time Ϊ None ��ƥ�䷴���л����
        assert_eq!(
            single,
            Config::builder().streamers(Default::default()).build(),
            "��ͨOption��������һ��"
        );
    }
}

