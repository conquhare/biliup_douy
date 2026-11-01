// 前端静态资源由 `npm run build` 生成到仓库根 `out/`，
// 经 rust-embed 的 `#[folder = "../../out/"]`（相对本 crate 根）在编译期嵌入 exe。
//
// 关键陷阱：cargo 增量编译基于源文件内容哈希。若仅改了前端 TSX 而 Rust 源码未变，
// cargo 会命中 target 缓存直接跳过 biliup-cli 重编译，rust-embed 的嵌入过程不重新执行，
// 导致前端改动永不在 exe 中生效（连早期字符串如「弹幕录制与处理」都不出现）。
//
// 这里声明 `out/` 为本 crate 的编译依赖：当 `out/` 内容变化时强制重编译 biliup-cli，
// 使 rust-embed 重新嵌入最新前端。仅在 out/ 存在时声明，避免本地未 build 前端时报错。
fn main() {
    let out_dir = std::path::Path::new("../../out");
    if out_dir.exists() {
        println!("cargo:rerun-if-changed=../../out");
    }
}
