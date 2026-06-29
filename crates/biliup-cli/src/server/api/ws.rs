use axum::extract::ws::{Message, Utf8Bytes, WebSocket};
use axum::extract::{Query, WebSocketUpgrade};
use serde::Deserialize;
use std::collections::VecDeque;
use std::io;
use std::io::ErrorKind;
use std::path::PathBuf;
use std::time::{Duration, Instant};
use tokio::fs;
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncSeekExt, BufReader};
use tokio::time::{MissedTickBehavior, interval};
use tracing::{debug, error, info, warn};

use crate::server::common::log_dedup::{LogDedupConfig, LogDeduplicator};

/// 允许监控的日志前缀 → 文件名后缀
static ALLOWED_LOG_TYPES: &[(&str, &str)] = &[
    ("ds_update", "log"),
    ("download", "log"),
    ("upload", "log"),
];

#[derive(Debug, Deserialize, Clone)]
pub struct LogsQuery {
    file: Option<String>,
}

pub async fn ws_logs(
    ws: WebSocketUpgrade,
    Query(query): Query<LogsQuery>,
) -> axum::response::Response {
    ws.on_upgrade(move |socket| websocket_logs(socket, query))
}

/// 根据请求的文件名解析出 (prefix, suffix)，验证是否在白名单中
fn parse_log_type(file_param: &str) -> Option<(&'static str, &'static str)> {
    for (prefix, suffix) in ALLOWED_LOG_TYPES {
        // 同时支持旧格式 "download.log" 和新格式 "download.2026-06-26.log"
        if file_param == format!("{}.{}", prefix, suffix)
            || (file_param.starts_with(prefix) && file_param.ends_with(suffix))
        {
            return Some((prefix, suffix));
        }
    }
    None
}

async fn websocket_logs(mut ws: WebSocket, query: LogsQuery) {
    let file_param = query.file.unwrap_or_else(|| "ds_update.log".to_string());
    let Some((prefix, suffix)) = parse_log_type(&file_param) else {
        let _ = ws
            .send(Message::Text(
                format!("不允许访问请求的文件: {}", file_param).into(),
            ))
            .await;
        let _ = ws.send(Message::Close(None)).await;
        return;
    };

    // 解析实际日志文件路径（支持每日滚动后的新文件名）
    let cwd = std::path::Path::new(".");
    let mut log_file = match resolve_latest_log_path(cwd, prefix, suffix).await {
        Ok(path) => path,
        Err(e) => {
            let _ = ws
                .send(Message::Text(
                    format!("找不到日志文件 ({}.{}): {}", prefix, suffix, e).into(),
                ))
                .await;
            let _ = ws.send(Message::Close(None)).await;
            return;
        }
    };

    let config = load_dedup_config().await;
    let mut dedup = LogDeduplicator::new(config);

    let mut file_size = match send_last_lines_dedup(&mut ws, &log_file, 50, &mut dedup).await {
        Ok(size) => size,
        Err(e) => {
            match e.kind() {
                ErrorKind::NotFound => {
                    let _ = ws
                        .send(Message::Text(
                            format!("日志文件 {} 不存在", log_file.display()).into(),
                        ))
                        .await;
                }
                _ => {
                    let _ = ws
                        .send(Message::Text(format!("读取日志文件错误: {}", e).into()))
                        .await;
                    error!("读取日志文件错误: {}", e);
                }
            }
            let _ = ws.send(Message::Close(None)).await;
            return;
        }
    };

    let mut tick = interval(Duration::from_millis(500));
    tick.set_missed_tick_behavior(MissedTickBehavior::Skip);
    let mut last_periodic_flush = Instant::now();
    const PERIODIC_FLUSH_INTERVAL: Duration = Duration::from_secs(10);
    // 每60秒检查一次日志滚动（避免频繁 I/O）
    let mut last_rotation_check = Instant::now();
    const ROTATION_CHECK_INTERVAL: Duration = Duration::from_secs(60);

    loop {
        tokio::select! {
            maybe_msg = ws.recv() => {
                match maybe_msg {
                    Some(Ok(Message::Close(_))) => {
                        let _ = ws.send(Message::Close(None)).await;
                        break;
                    }
                    Some(Ok(Message::Ping(payload))) => {
                        let _ = ws.send(Message::Pong(payload)).await;
                    }
                    Some(Ok(_)) => {}
                    Some(Err(e)) => {
                        error!("WebSocket连接错误: {}", e);
                        break;
                    }
                    None => {
                        info!("WebSocket连接已关闭");
                        break;
                    }
                }
            }

            _ = tick.tick() => {
                // 检查日志是否发生了滚动（文件名变化）
                if last_rotation_check.elapsed() >= ROTATION_CHECK_INTERVAL {
                    last_rotation_check = Instant::now();
                    let cwd = std::path::Path::new(".");
                    match resolve_latest_log_path(cwd, prefix, suffix).await {
                        Ok(latest) if latest != log_file => {
                            let _ = ws.send(Message::Text(Utf8Bytes::from(
                                format!("日志滚动: {} → {}", log_file.display(), latest.display())
                            ))).await;
                            // 读取旧文件的尾部（可能还有残留数据）
                            let meta = match fs::metadata(&log_file).await {
                                Ok(m) => m,
                                Err(_) => {
                                    log_file = latest;
                                    file_size = 0;
                                    dedup.reset();
                                    continue;
                                }
                            };
                            let current_size = meta.len();
                            if current_size > file_size {
                                if let Err(e) = send_new_lines_dedup(&mut ws, &log_file, file_size, &mut dedup).await {
                                    error!("读取旧日志文件尾部错误: {}", e);
                                }
                            }
                            // 切换到新文件
                            info!("切换到新日志文件: {}", latest.display());
                            log_file = latest;
                            file_size = 0;
                            dedup.reset();
                            continue;
                        }
                        Ok(_) => {} // 文件未变化
                        Err(_) => {
                            warn!("解析日志文件路径失败，保持当前文件: {}", log_file.display());
                        }
                    }
                }

                let meta = match fs::metadata(&log_file).await {
                    Ok(m) => m,
                    Err(e) if e.kind() == ErrorKind::NotFound => {
                        let _ = ws.send(Message::Text(format!(
                            "日志文件 {} 不再存在",
                            log_file.display()
                        ).into())).await;
                        break;
                    }
                    Err(e) => {
                        let _ = ws.send(Message::Text(format!("监控日志文件错误: {}", e).into())).await;
                        error!("websocket_logs错误: {}", e);
                        break;
                    }
                };

                let current_size = meta.len();

                if current_size < file_size {
                    let _ = ws.send(Message::Text(Utf8Bytes::from("日志文件被截断，重新加载...".to_string()))).await;
                    dedup.reset();
                    match send_last_lines_dedup(&mut ws, &log_file, 50, &mut dedup).await {
                        Ok(size) => file_size = size,
                        Err(e) => {
                            let _ = ws.send(Message::Text(format!("读取日志文件错误: {}", e).into())).await;
                            error!("读取日志文件错误: {}", e);
                            break;
                        }
                    }
                    continue;
                }

                if current_size > file_size {
                    if let Err(e) = send_new_lines_dedup(&mut ws, &log_file, file_size, &mut dedup).await {
                        let _ = ws.send(Message::Text(format!("监控日志文件错误: {}", e).into())).await;
                        error!("websocket_logs错误: {}", e);
                        break;
                    }
                    file_size = current_size;
                }

                // 周期性输出去重摘要（每30秒）
                if last_periodic_flush.elapsed() >= PERIODIC_FLUSH_INTERVAL {
                    let summaries = dedup.periodic_flush();
                    for summary in summaries {
                        if ws.send(Message::Text(Utf8Bytes::from(summary))).await.is_err() {
                            break;
                        }
                    }
                    last_periodic_flush = Instant::now();
                }
            }
        }
    }

    let flush_results = dedup.flush();
    for line in flush_results {
        let _ = ws.send(Message::Text(Utf8Bytes::from(line))).await;
    }

    let _ = ws.send(Message::Close(None)).await;
    debug!("WebSocket日志会话结束: {}", file_param);
}

async fn send_last_lines_dedup(
    ws: &mut WebSocket,
    path: &std::path::Path,
    n: usize,
    dedup: &mut LogDeduplicator,
) -> std::io::Result<u64> {
    let meta = fs::metadata(path).await?;
    let file_size = meta.len();

    let file = fs::File::open(path).await?;
    let reader = BufReader::new(file);
    let mut lines = reader.lines();

    let mut buf: VecDeque<String> = VecDeque::with_capacity(n);
    while let Some(line) = lines.next_line().await? {
        if buf.len() == n {
            buf.pop_front();
        }
        buf.push_back(line);
    }

    for line in buf {
        let processed = dedup.process(&line);
        for output_line in processed {
            ws.send(Message::Text(Utf8Bytes::from(output_line)))
                .await
                .map_err(|e| {
                    std::io::Error::new(
                        ErrorKind::ConnectionAborted,
                        format!("发送WebSocket消息失败: {}", e),
                    )
                })?;
        }
    }
    Ok(file_size)
}

async fn send_new_lines_dedup(
    ws: &mut WebSocket,
    path: &std::path::Path,
    offset: u64,
    dedup: &mut LogDeduplicator,
) -> std::io::Result<()> {
    let mut file = fs::File::open(path).await?;
    file.seek(std::io::SeekFrom::Start(offset)).await?;

    let mut s = String::new();
    if let Err(e) = file.read_to_string(&mut s).await {
        let mut bytes = Vec::new();
        file.seek(std::io::SeekFrom::Start(offset)).await?;
        file.read_to_end(&mut bytes).await?;
        s = String::from_utf8_lossy(&bytes).into_owned();
        if e.kind() != ErrorKind::InvalidData {
            error!("读取日志文件新内容失败: {}", e);
        }
    }

    for line in s.lines() {
        let processed = dedup.process(line);
        for output_line in processed {
            ws.send(Message::Text(Utf8Bytes::from(output_line)))
                .await
                .map_err(|e| {
                    std::io::Error::new(
                        ErrorKind::ConnectionAborted,
                        format!("发送WebSocket消息失败: {}", e),
                    )
                })?;
        }
    }
    Ok(())
}

pub async fn load_dedup_config() -> LogDedupConfig {
    use std::path::Path;
    use tokio::fs;

    let config_path = Path::new("log_dedup_config.json");
    match fs::read_to_string(config_path).await {
        Ok(content) => {
            serde_json::from_str(&content).unwrap_or_default()
        }
        Err(_) => LogDedupConfig::default(),
    }
}

pub async fn save_dedup_config(config: &LogDedupConfig) -> std::io::Result<()> {
    use std::path::Path;
    use tokio::fs;

    let config_path = Path::new("log_dedup_config.json");
    let content = serde_json::to_string_pretty(config).unwrap_or_default();
    fs::write(config_path, content).await
}

async fn resolve_latest_log_path(
    dir: &std::path::Path,
    prefix: &str,
    suffix: &str,
) -> io::Result<PathBuf> {
    let active = dir.join(format!("{}.{}", prefix, suffix));
    if fs::metadata(&active).await.is_ok() {
        return Ok(active);
    }

    let mut rd = fs::read_dir(dir).await?;
    let pre = format!("{}.", prefix);
    let suf = format!(".{}", suffix);

    let mut candidates: Vec<(String, PathBuf)> = Vec::new();
    while let Some(ent) = rd.next_entry().await? {
        let path = ent.path();
        if !path.is_file() {
            continue;
        }
        let Some(name) = path.file_name().and_then(|s| s.to_str()) else {
            continue;
        };
        if name.starts_with(&pre) && name.ends_with(&suf) {
            candidates.push((name.to_string(), path));
        }
    }

    if candidates.is_empty() {
        return Err(io::Error::new(ErrorKind::NotFound, "no log file found"));
    }

    candidates.sort_by(|a, b| a.0.cmp(&b.0));
    Ok(candidates.last().unwrap().1.clone())
}
