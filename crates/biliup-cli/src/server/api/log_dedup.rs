use axum::Json;
use axum::http::StatusCode;

use crate::server::api::ws::{load_dedup_config, save_dedup_config};
use crate::server::common::log_dedup::LogDedupConfig;

pub async fn get_log_dedup_config() -> Result<Json<LogDedupConfig>, (StatusCode, String)> {
    let config = load_dedup_config().await;
    Ok(Json(config))
}

pub async fn put_log_dedup_config(
    Json(config): Json<LogDedupConfig>,
) -> Result<Json<LogDedupConfig>, (StatusCode, String)> {
    match save_dedup_config(&config).await {
        Ok(_) => Ok(Json(config)),
        Err(e) => Err((StatusCode::INTERNAL_SERVER_ERROR, format!("保存配置失败: {}", e))),
    }
}
