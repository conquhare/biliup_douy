/** @type {import('next').NextConfig} */
const nextConfig = {
    // reactStrictMode: true,
    output: 'export',
    images: {
        unoptimized: true
    },
    // 禁用 ESLint 检查，加快构建速度
    eslint: {
        ignoreDuringBuilds: true,
    },
    // 禁用 TypeScript 类型检查，加快构建速度
    typescript: {
        ignoreBuildErrors: true,
    },
}

module.exports = nextConfig
