use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// version-tag: log_dedup_v3 (multi-entry + emit_summaries + diagnostics)
/// 多条目追踪上限，防止无限增长
const MAX_ENTRIES: usize = 200;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogDedupConfig {
    pub enabled: bool,
    pub threshold: u32,
    pub enabled_levels: Vec<String>,
    pub abbreviate_format: String,
    pub reset_on_error: bool,
    pub reset_on_change: bool,
}

impl Default for LogDedupConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            threshold: 4,
            enabled_levels: vec![
                "DEBUG".to_string(),
                "INFO".to_string(),
                "WARNING".to_string(),
            ],
            abbreviate_format: "... [重复 {count} 次] {content}".to_string(),
            reset_on_error: true,
            reset_on_change: true,
        }
    }
}

#[derive(Debug, Clone)]
struct LogEntry {
    level: String,
    content: String,
    count: u32,
}

pub struct LogDeduplicator {
    config: LogDedupConfig,
    /// 多条目追踪：key = "level:normalized_content"
    entries: HashMap<String, LogEntry>,
    /// 统计：已处理行数（用于诊断）
    total_processed: u64,
    total_suppressed: u64,
}

impl LogDeduplicator {
    pub fn new(config: LogDedupConfig) -> Self {
        tracing::info!(
            "[去重] 初始化: enabled={} threshold={} reset_on_change={} reset_on_error={} levels={:?}",
            config.enabled,
            config.threshold,
            config.reset_on_change,
            config.reset_on_error,
            config.enabled_levels,
        );
        Self {
            config,
            entries: HashMap::new(),
            total_processed: 0,
            total_suppressed: 0,
        }
    }

    pub fn with_default_config() -> Self {
        Self::new(LogDedupConfig::default())
    }

    pub fn update_config(&mut self, config: LogDedupConfig) {
        self.config = config;
        self.entries.clear();
    }

    pub fn reset(&mut self) {
        self.entries.clear();
    }

    pub fn process(&mut self, line: &str) -> Vec<String> {
        let mut results = Vec::new();

        if !self.config.enabled {
            results.push(line.to_string());
            return results;
        }

        let (level, raw_content) = self.parse_log_line(line);

        // 如果 level 不在启用列表中，直接透传
        if !self.config.enabled_levels.contains(&level.to_string()) {
            results.push(line.to_string());
            return results;
        }

        // 归一化 content：剥离 ThreadId 和源码位置前缀
        let content = Self::normalize_content(&raw_content);
        let key = format!("{}:{}", level, content);

        // ERROR / CRITICAL 触发 reset_on_error
        if self.config.reset_on_error && (level == "ERROR" || level == "CRITICAL") {
            self.drain_summaries(&mut results);
            results.push(line.to_string());
            return results;
        }

        // 查找已有条目
        if let Some(entry) = self.entries.get_mut(&key) {
            entry.count += 1;
            if entry.count < self.config.threshold {
                results.push(line.to_string());
            } else {
                self.total_suppressed += 1;
                if self.total_suppressed <= 10 || self.total_suppressed % 100 == 0 {
                    tracing::info!(
                        "[去重] 已抑制 {} 条日志, 当前: count={} > threshold={}",
                        self.total_suppressed,
                        entry.count,
                        self.config.threshold,
                    );
                }
                // count >= threshold: 不输出（抑制）
            }
        } else {
            // 全新条目：输出已达到阈值的摘要（不删除追踪状态）
            if self.config.reset_on_change {
                self.emit_summaries(&mut results);
            }

            // 上限保护
            if self.entries.len() >= MAX_ENTRIES {
                self.drain_summaries(&mut results);
            }

            results.push(line.to_string());
            self.entries.insert(
                key,
                LogEntry {
                    level,
                    content,
                    count: 1,
                },
            );
        }

        results
    }

    pub fn flush(&mut self) -> Vec<String> {
        let mut results = Vec::new();
        self.drain_summaries(&mut results);
        results
    }

    // ---- 内部方法 ----

    fn parse_log_line(&self, line: &str) -> (String, String) {
        let level_patterns = [
            (" DEBUG ", "DEBUG"),
            (" INFO ", "INFO"),
            (" WARNING ", "WARNING"),
            (" ERROR ", "ERROR"),
            (" CRITICAL ", "CRITICAL"),
            (" WARN ", "WARNING"),
        ];

        for (pattern, level_name) in level_patterns {
            if let Some(pos) = line.find(pattern) {
                let content = line[pos + pattern.len()..].to_string();
                return (level_name.to_string(), content);
            }
        }

        (String::new(), line.to_string())
    }

    /// 归一化日志 content：剥离 ThreadId(NN) 和源码位置前缀
    ///
    /// 输入：`ThreadId(16) biliup_cli::server::core::monitor: crates\...\monitor.rs:568: Room [...] status changed to Idle`
    /// 输出：`Room [...] status changed to Idle`
    fn normalize_content(raw: &str) -> String {
        let s = raw.trim();

        // 剥离 ThreadId(NN) 前缀
        let s = if let Some(rest) = s.strip_prefix("ThreadId(") {
            rest.find(") ")
                .map(|idx| rest[idx + 2..].to_string())
                .unwrap_or_else(|| s.to_string())
        } else {
            s.to_string()
        };

        // 剥离源码位置：module::path: file.rs:NNN: 
        // 寻找 ".rs:" 模式，跳过后续的数字和 ": " 直到消息正文
        if let Some(rs_pos) = s.find(".rs:") {
            let after_rs = &s[rs_pos + 4..]; // 跳过 ".rs:"
            // 跳过数字
            let digits_end = after_rs
                .find(|c: char| !c.is_ascii_digit())
                .unwrap_or(after_rs.len());
            let after_digits = &after_rs[digits_end..];
            // 跳过 ": " 分隔符
            if let Some(stripped) = after_digits.strip_prefix(": ") {
                return stripped.to_string();
            }
        }

        s
    }

    /// 输出所有达到阈值的条目的摘要（不删除条目，用于 reset_on_change 场景）
    fn emit_summaries(&self, results: &mut Vec<String>) {
        for (_, entry) in &self.entries {
            if entry.count >= self.config.threshold {
                if let Some(summary) = self.make_summary(entry) {
                    results.push(summary);
                }
            }
        }
    }

    /// 输出所有达到阈值的条目的摘要，并清空 entries（用于 flush / reset 场景）
    fn drain_summaries(&mut self, results: &mut Vec<String>) {
        let entries: Vec<_> = self.entries.drain().collect();
        for (_, entry) in entries {
            if entry.count >= self.config.threshold {
                if let Some(summary) = self.make_summary(&entry) {
                    results.push(summary);
                }
            }
        }
    }

    fn make_summary(&self, entry: &LogEntry) -> Option<String> {
        if entry.count > self.config.threshold {
            let extra_count = entry.count - self.config.threshold;
            if extra_count > 0 {
                return Some(
                    self.config
                        .abbreviate_format
                        .replace("{count}", &extra_count.to_string())
                        .replace("{content}", &entry.content),
                );
            }
        }
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_dedup() {
        let mut dedup = LogDeduplicator::with_default_config();
        let line = "2024-01-01 12:00:00 INFO Room [xxx] status changed to Idle";

        let r1 = dedup.process(line);
        assert_eq!(r1.len(), 1);

        let r2 = dedup.process(line);
        assert_eq!(r2.len(), 1);

        let r3 = dedup.process(line);
        assert_eq!(r3.len(), 1);

        let r4 = dedup.process(line);
        assert_eq!(r4.len(), 0);

        let r5 = dedup.process(line);
        assert_eq!(r5.len(), 0);

        let flush = dedup.flush();
        assert!(flush[0].contains("重复"));
    }

    #[test]
    fn test_reset_on_different_content() {
        let mut dedup = LogDeduplicator::with_default_config();
        let line1 = "2024-01-01 12:00:00 INFO Room [xxx] status changed to Idle";
        let line2 = "2024-01-01 12:00:01 INFO Room [yyy] status changed to Live";

        for _ in 0..3 {
            dedup.process(line1);
        }
        let results = dedup.process(line2);
        // line2 是全新内容，reset_on_change=true 会 emit 摘要（line1 未达阈值故无摘要）
        // 但不会删除 line1 的追踪条目！line1 的 entry 保留在 map 中
        // 输出包含 line2 本身
        assert!(results.len() >= 1);

        // 再次出现 line1 时，count 应该继续从 4 开始累积（之前3次+现在1次）
        let r = dedup.process(line1); // count=4 >= threshold=4 → 抑制
        // 注意：如果 reset_on_change 错误地清空了 entries，这里 count 会是 1 而非 4
    }

    #[test]
    fn test_reset_on_change_preserves_entries() {
        // 验证 reset_on_change 不删除追踪条目（多房间场景核心修复）
        let mut config = LogDedupConfig::default();
        config.threshold = 2;
        config.reset_on_change = true;
        let mut dedup = LogDeduplicator::new(config);

        let room_a = "2024-01-01 12:00:00 INFO Room [A] status changed to Idle";
        let room_b = "2024-01-01 12:00:01 INFO Room [B] status changed to Idle";

        // Room A 出现 2 次（达到阈值）
        dedup.process(room_a); // count=1, output
        dedup.process(room_a); // count=2 >= threshold, 抑制

        // Room B 出现（全新消息，触发 reset_on_change）
        let results = dedup.process(room_b);
        // 应输出 room_b 本身；room_a 未达额外重复所以没有摘要
        assert!(results.iter().any(|r| r.contains("Room [B]")), "应输出新消息 room_b");

        // Room A 再次出现时——关键：count 应继续从 3 累积（不是从 1 开始）
        let results = dedup.process(room_a); // count=3 > threshold, 抑制
        assert_eq!(results.len(), 0, "room_a count=3 >= threshold=2，应被抑制");

        // flush 应有 room_a 的摘要（extra_count = 3 - 2 = 1）
        let flush = dedup.flush();
        assert!(flush.iter().any(|r| r.contains("Room [A]") && r.contains("重复")),
            "flush 应包含 room_a 的去重摘要，说明条目一直被保留");
    }

    #[test]
    fn test_reset_on_error() {
        let mut dedup = LogDeduplicator::with_default_config();
        let line1 = "2024-01-01 12:00:00 INFO Room [xxx] status changed to Idle";
        let error_line = "2024-01-01 12:00:01 ERROR Something went wrong";

        for _ in 0..5 {
            dedup.process(line1);
        }
        let results = dedup.process(error_line);
        assert!(results.iter().any(|r| r.contains("重复")));
    }

    #[test]
    fn test_disabled() {
        let mut config = LogDedupConfig::default();
        config.enabled = false;
        let mut dedup = LogDeduplicator::new(config);
        let line = "2024-01-01 12:00:00 INFO Room [xxx] status changed to Idle";

        for _ in 0..10 {
            let results = dedup.process(line);
            assert_eq!(results.len(), 1);
        }
    }

    #[test]
    fn test_threshold_boundary() {
        let mut config = LogDedupConfig::default();
        config.threshold = 2;
        let mut dedup = LogDeduplicator::new(config);
        let line = "2024-01-01 12:00:00 INFO Test message";

        let r1 = dedup.process(line);
        assert_eq!(r1.len(), 1); // count=1, 输出

        let r2 = dedup.process(line);
        assert_eq!(r2.len(), 0); // count=2 >= threshold, 抑制

        let r3 = dedup.process(line);
        assert_eq!(r3.len(), 0); // count=3, 抑制

        // 共 3 次，threshold=2，超出 1 次 → 摘要含 "重复 1 次"
        let flush = dedup.flush();
        assert!(!flush.is_empty(), "flush 应产生摘要");
        assert!(flush[0].contains("重复"));
        assert!(flush[0].contains("1"));
    }

    #[test]
    fn test_different_levels_not_deduped() {
        let mut config = LogDedupConfig::default();
        config.enabled_levels = vec!["INFO".to_string()];
        let mut dedup = LogDeduplicator::new(config);

        let info_line = "2024-01-01 12:00:00 INFO Same message";
        let debug_line = "2024-01-01 12:00:01 DEBUG Same message";

        for _ in 0..5 {
            dedup.process(info_line);
        }
        let results = dedup.process(debug_line);
        // DEBUG 不在 enabled_levels 中，直接透传 1 行
        assert_eq!(results.len(), 1);
    }

    #[test]
    fn test_critical_resets_count() {
        let mut dedup = LogDeduplicator::with_default_config();
        let line1 = "2024-01-01 12:00:00 INFO Room [xxx] status changed to Idle";
        let critical_line = "2024-01-01 12:00:01 CRITICAL System failure";

        for _ in 0..5 {
            dedup.process(line1);
        }
        let results = dedup.process(critical_line);
        assert!(results.iter().any(|r| r.contains("重复")));
    }

    #[test]
    fn test_custom_format() {
        let mut config = LogDedupConfig::default();
        config.abbreviate_format = "[x{count}] {content}".to_string();
        let mut dedup = LogDeduplicator::new(config);
        let line = "2024-01-01 12:00:00 INFO Test message";

        for _ in 0..6 {
            dedup.process(line);
        }
        // 6 次，threshold=4，超出 2 → "[x2] Test message" → 等待 flush
        // 注意：第5次起就 count=5>4，但第4次 count=4≥4 已经开始抑制
        // count=4 → 抑制 (4>=4); count=5 → 抑制; count=6 → 抑制
        // extra = 6-4 = 2 → "[x2] Test message"
        let flush = dedup.flush();
        assert!(flush[0].contains("[x2]"));
    }

    #[test]
    fn test_config_serialization() {
        let config = LogDedupConfig::default();
        let json = serde_json::to_string(&config).unwrap();
        let parsed: LogDedupConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(config.threshold, parsed.threshold);
        assert_eq!(config.enabled, parsed.enabled);
        assert_eq!(config.enabled_levels, parsed.enabled_levels);
    }

    #[test]
    fn test_reset_on_change_disabled() {
        let mut config = LogDedupConfig::default();
        config.reset_on_change = false;
        let mut dedup = LogDeduplicator::new(config);
        let line1 = "2024-01-01 12:00:00 INFO Message A";
        let line2 = "2024-01-01 12:00:01 INFO Message B";

        for _ in 0..3 {
            dedup.process(line1);
        }
        let results = dedup.process(line2);
        // reset_on_change=false，不清空条目，line2 作为新条目输出
        assert!(results.len() >= 1);
    }

    #[test]
    fn test_max_threshold() {
        let mut config = LogDedupConfig::default();
        config.threshold = 20;
        let mut dedup = LogDeduplicator::new(config);
        let line = "2024-01-01 12:00:00 INFO Test message";

        for i in 0..25 {
            let results = dedup.process(line);
            if i < 19 {
                assert_eq!(results.len(), 1);
            } else {
                assert_eq!(results.len(), 0);
            }
        }
    }

    #[test]
    fn test_min_threshold() {
        let mut config = LogDedupConfig::default();
        config.threshold = 1;
        let mut dedup = LogDeduplicator::new(config);
        let line = "2024-01-01 12:00:00 INFO Test message";

        let r1 = dedup.process(line);
        assert_eq!(r1.len(), 1); // count=1 == threshold, 但 count=1, 1 >= 1 → 抑制? 等等...

        let r2 = dedup.process(line);
        assert_eq!(r2.len(), 0); // count=2, 抑制

        // threshold=1: 第1次输出(count=1>=1 → 抑制? 不对，count在increment之前)
        // 实际上代码逻辑：先 get_mut 再 increment。increment之前 count=0，increment后=1
        // 然后判断 1 >= 1 → true → 不输出
        // 所以第一次也不输出... 但测试期望 r1.len() == 1
        // 对于新条目：results.push(line)，插入count=1
        // 第二次：get_mut, count++, now count=2, 2 >= 1 → 不输出
        // flush：count=2 > 1 → summary

        // 修正断言：threshold=1 时第一次就输出（新条目），第二次抑制
        // 原测试断言保留，因为第一次是新条目始终输出
        let flush = dedup.flush();
        assert!(!flush.is_empty(), "threshold=1 应有摘要");
        assert!(flush[0].contains("重复"));
    }

    #[test]
    fn test_multi_entry_dedup() {
        // 模拟真实场景：7个房间循环输出 "status changed to Idle"
        let mut dedup = LogDeduplicator::with_default_config();
        let rooms = [
            "Room [https://live.douyin.com/74544384974] status changed to Idle",
            "Room [https://live.douyin.com/920853703794] status changed to Idle",
            "Room [https://live.douyin.com/793168762040] status changed to Idle",
            "Room [https://live.douyin.com/21696736606] status changed to Idle",
            "Room [https://live.douyin.com/wjs060515] status changed to Idle",
            "Room [https://live.douyin.com/28363992803] status changed to Idle",
            "Room [https://live.douyin.com/38432117839] status changed to Idle",
        ];

        // 循环 3 轮，每个房间出现 3 次（都 < threshold=4，所以都输出）
        for round in 0..3 {
            for room in &rooms {
                let line = format!(
                    "2024-01-01 12:00:00  INFO ThreadId(02) biliup_cli::server::core::monitor: crates\\biliup-cli\\src\\server\\core\\monitor.rs:568: {}",
                    room
                );
                let results = dedup.process(&line);
                assert_eq!(results.len(), 1, "前3轮每个房间都输出（未达threshold）");
            }
        }

        // 第4轮：每个房间 count=4 >= threshold，应全部抑制
        for room in &rooms {
            let line = format!(
                "2024-01-01 12:00:00  INFO ThreadId(16) biliup_cli::server::core::monitor: crates\\biliup-cli\\src\\server\\core\\monitor.rs:568: {}",
                room
            );
            let results = dedup.process(&line);
            assert_eq!(results.len(), 0, "第4轮应被抑制");
        }

        // flush 应有 7 个摘要
        let flush = dedup.flush();
        assert_eq!(flush.len(), 7, "7个房间各应有1条去重摘要");
        for line in &flush {
            assert!(line.contains("重复"), "摘要应含'重复': {}", line);
        }
    }

    #[test]
    fn test_content_normalization_strips_thread_id() {
        let mut dedup = LogDeduplicator::with_default_config();

        // 同一个房间，不同 ThreadId — 归一化后应视为同一内容
        let line_a = "2024-01-01 12:00:00  INFO ThreadId(02) biliup_cli::server::core::monitor: crates\\biliup-cli\\src\\server\\core\\monitor.rs:568: Room [xxx] status changed to Idle";
        let line_b = "2024-01-01 12:00:00  INFO ThreadId(16) biliup_cli::server::core::monitor: crates\\biliup-cli\\src\\server\\core\\monitor.rs:568: Room [xxx] status changed to Idle";

        dedup.process(line_a);
        dedup.process(line_b);
        dedup.process(line_a);
        // 3次，threshold=4，还没达到抑制阈值，都输出
        let r4 = dedup.process(line_b); // 第4次，count=4 >= 4，抑制
        assert_eq!(r4.len(), 0, "不同ThreadId的同内容应归一化后去重");
    }

    #[test]
    fn test_no_source_location_handled() {
        // 简化日志格式（无 ThreadId、无源码位置）也应该正常工作
        let mut dedup = LogDeduplicator::with_default_config();
        let line = "2024-01-01 12:00:00 INFO Simple message";

        for _ in 0..4 {
            dedup.process(&line);
        }
        let results = dedup.process(&line); // 第5次，count=5 >= 4
        assert_eq!(results.len(), 0, "简单格式也应去重");
    }
}
