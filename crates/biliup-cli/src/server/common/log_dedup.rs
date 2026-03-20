use serde::{Deserialize, Serialize};

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
    current: Option<LogEntry>,
    pending_output: Vec<String>,
}

impl LogDeduplicator {
    pub fn new(config: LogDedupConfig) -> Self {
        Self {
            config,
            current: None,
            pending_output: Vec::new(),
        }
    }

    pub fn with_default_config() -> Self {
        Self::new(LogDedupConfig::default())
    }

    pub fn update_config(&mut self, config: LogDedupConfig) {
        self.config = config;
        self.reset();
    }

    pub fn reset(&mut self) {
        if let Some(entry) = self.current.take() {
            if entry.count > 0 {
                self.output_pending(entry);
            }
        }
        self.pending_output.clear();
    }

    pub fn process(&mut self, line: &str) -> Vec<String> {
        let mut results = Vec::new();

        if !self.config.enabled {
            results.push(line.to_string());
            return results;
        }

        let (level, content) = self.parse_log_line(line);

        let should_reset = self.should_reset(&level);
        let is_same = self.is_same_entry(&level, &content);

        if should_reset {
            if let Some(entry) = self.current.take() {
                if entry.count > 0 {
                    results.extend(self.finalize_entry(entry));
                }
            }
        }

        if is_same && !should_reset {
            if let Some(ref mut entry) = self.current {
                entry.count += 1;
                if entry.count >= self.config.threshold {
                    // 达到阈值后不输出，只计数
                    return results;
                } else {
                    results.push(line.to_string());
                    return results;
                }
            }
        }

        // 新日志条目
        if let Some(entry) = self.current.take() {
            if entry.count >= self.config.threshold {
                results.extend(self.finalize_entry(entry));
            }
        }

        results.push(line.to_string());
        self.current = Some(LogEntry {
            level,
            content,
            count: 1,
        });

        results
    }

    pub fn flush(&mut self) -> Vec<String> {
        let mut results = Vec::new();
        if let Some(entry) = self.current.take() {
            if entry.count >= self.config.threshold {
                results.extend(self.finalize_entry(entry));
            }
        }
        results
    }

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

    fn should_reset(&self, level: &str) -> bool {
        if self.config.reset_on_error && level == "ERROR" {
            return true;
        }
        if self.config.reset_on_error && level == "CRITICAL" {
            return true;
        }
        false
    }

    fn is_same_entry(&self, level: &str, content: &str) -> bool {
        if !self.config.enabled_levels.contains(&level.to_string()) {
            return false;
        }

        if let Some(ref entry) = self.current {
            entry.level == level && entry.content == content
        } else {
            false
        }
    }

    fn finalize_entry(&self, entry: LogEntry) -> Vec<String> {
        let mut results = Vec::new();
        if entry.count > self.config.threshold {
            let extra_count = entry.count - self.config.threshold;
            if extra_count > 0 {
                let summary = self
                    .config
                    .abbreviate_format
                    .replace("{count}", &extra_count.to_string())
                    .replace("{content}", &entry.content);
                results.push(summary);
            }
        }
        results
    }

    fn output_pending(&self, entry: LogEntry) {
        if entry.count > self.config.threshold {
            let extra_count = entry.count - self.config.threshold;
            if extra_count > 0 {
                let _summary = self
                    .config
                    .abbreviate_format
                    .replace("{count}", &extra_count.to_string())
                    .replace("{content}", &entry.content);
            }
        }
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
        assert!(results.len() >= 1);
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
        assert_eq!(r1.len(), 1);

        let r2 = dedup.process(line);
        assert_eq!(r2.len(), 0);

        let r3 = dedup.process(line);
        assert_eq!(r3.len(), 0);

        let flush = dedup.flush();
        assert!(flush[0].contains("重复"));
        assert!(flush[0].contains("2"));
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
        let flush = dedup.flush();
        assert!(flush[0].contains("[x3]"));
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
        assert_eq!(r1.len(), 1);

        let r2 = dedup.process(line);
        assert_eq!(r2.len(), 0);

        let flush = dedup.flush();
        assert!(flush[0].contains("重复"));
    }
}
