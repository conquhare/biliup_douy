"""
stream_gears 上传功能测试

这个测试文件展示了如何使用 stream_gears.upload() 函数的各种功能：
1. 基础上传 - 使用关键字参数让代码更清晰
2. 多文件上传 - 上传多P视频
3. 定时发布 - 设置未来时间发布
4. 高级功能 - 使用富文本简介和额外字段
5. 最小参数 - 只使用必需参数，其他使用默认值

注意：运行前请确保：
- 存在有效的 cookies.json 文件
- 视频文件路径正确
- 网络连接正常
"""

import stream_gears
from typing import List, Dict, Any

video_path = ["E:\\Projects\\biliup\\target\\x86_64-pc-windows-msvc\\debug\\test.flv"]
cookie_file = "E:\\Projects\\biliup\\target\\x86_64-pc-windows-msvc\\debug\\cookies.json"
# submit_api = "BCutAndroid"

if __name__ == '__main__':
    # full kwargs 上传测试
    # stream_gears.upload(
    #     video_path=["examples/test.mp4"],
    # )

    # 视频简介v2
    def creditsToDesc_v2(desc: str, credits: List[Dict[str, Any]]):
        desc_v2 = []
        desc_v2_tmp = desc
        for credit in credits:
            try:
                num = desc_v2_tmp.index("@credit")
                desc_v2.append({
                    "raw_text": " " + desc_v2_tmp[:num],
                    "biz_id": "",
                    "type": 1
                })
                desc_v2.append({
                    "raw_text": credit["username"],
                    "biz_id": str(credit["uid"]),
                    "type": 2
                })
                desc = desc.replace(
                    "@credit", "@" + credit["username"] + "  ", 1)
                desc_v2_tmp = desc_v2_tmp[num + 7:]
            except IndexError:
                print('简介中的@credit占位符少于credits的数量,替换失败')
        desc_v2.append({
            "raw_text": str(desc_v2_tmp),
            "biz_id": "",
            "type": 1
        })
        # desc_v2[0]["raw_text"] = desc_v2[0]["raw_text"][1:]  # 开头空格会导致识别简介过长
        return desc_v2

    # 额外字段（JSON格式）
    extra_fields_json = '{"is_self_only": "1"}'

    # 测试
    stream_gears.upload(
        video_path=video_path,
        cookie_file=cookie_file,
        copyright=1,
        extra_fields=extra_fields_json,
        submit="b-cut-android",
        title="必剪投稿接口测试"
    )

    print("所有测试用例已完成！")
