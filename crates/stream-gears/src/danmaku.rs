use async_trait::async_trait;
use biliup_cli::server::core::downloader::DanmakuClient;
use biliup_cli::server::errors::{AppError, AppResult};
use error_stack::ResultExt;
use pyo3::prelude::*;
use std::sync::Arc;

/// DanmakuClient provides Rust bindings to the Python DanmakuClient
/// for recording live chat (danmaku) alongside video streams.
pub struct PyDanmakuClient {
    py_client: Arc<Py<PyAny>>,
}

impl PyDanmakuClient {
    /// Creates a new DanmakuClient instance
    pub fn new(py_client: Arc<Py<PyAny>>) -> Self {
        Self { py_client }
    }
}
#[async_trait]
impl DanmakuClient for PyDanmakuClient {
    /// Starts danmaku recording and manages lifecycle
    async fn download(&self) -> AppResult<()> {
        let py_client = self.py_client.clone();
        tokio::task::spawn_blocking(move || {
            Python::attach(|py| {
                let py_client = py_client.bind(py);
                py_client.call_method0("start")?;
                Ok::<_, PyErr>(())
            })
        })
        .await
        .map_err(|e| AppError::Custom(format!("弹幕录制线程异常退出: {e}")))?
        .map_err(|e| AppError::Custom(format!("弹幕录制启动失败: {e}")))?;

        // Start the danmaku recording
        // self.start()
        //     .map_err(|e| Box::new(e) as Box<dyn std::error::Error>)?;

        // Return downloading status - the actual recording runs in the background
        // The Python DanmakuClient handles the recording lifecycle internally
        Ok(())
    }

    /// Stops the danmaku recording
    async fn stop(&self) -> AppResult<()> {
        let py_client = self.py_client.clone();
        // Call the DanmakuClient's stop method (not the trait method)
        tokio::task::spawn_blocking(move || {
            Python::attach(|py| {
                let py_client = py_client.bind(py);
                py_client.call_method0("stop")?;
                Ok::<_, PyErr>(())
            })
        })
        .await
        .map_err(|e| AppError::Custom(format!("弹幕停止线程异常退出: {e}")))?
        .map_err(|e| AppError::Custom(format!("弹幕停止失败: {e}")))?;
        Ok(())
    }

    /// Saves current recording and starts new file (rolling)
    fn rolling(&self, file_name: &str) -> Result<(), Box<dyn std::error::Error>> {
        // Forward to Python client.save() - this saves current recording
        // and the Python client handles starting a new recording file
        let py_client = self.py_client.clone();
        let file_name = file_name.to_string();
        Python::attach(|py| {
            let py_client = py_client.bind(py);
            py_client.call_method1("save", (file_name,))?;
            Ok::<_, PyErr>(())
        })?;
        Ok(())
    }
}
