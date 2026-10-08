# -*- coding: utf-8 -*-
"""ASS → B站 BCC 转换的离线验证（不联网、不投稿）。

⚠️ 样本刻意使用**真实弹幕 ASS 的行格式**：
   Dialogue: 0,0:00:00.82,0:00:05.03,Danmaku,,0,0,0,,{\\move(...)\\c&Hffffff&}文本
   即时间轴与文本在同一行，且带内联样式标签 —— 这是曾导致解析出 0 条的坑。
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from biliup.plugins.bili_webup_sync import BiliBili


ASS_SAMPLE = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Style: Danmaku,微软雅黑,40,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,3,1,2,60,60,320,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.82,0:00:05.03,Danmaku,,0,0,0,,{\\move(1920,50,-100,50)\\c&Hffffff&}如同喝了
Dialogue: 0,0:00:00.99,0:00:05.56,Danmaku,,0,0,0,,{\\move(1920,79,-275,79)\\c&Hffffff&}新的一天 新气象 哈哈
Dialogue: 0,0:01:07.50,0:01:10.00,Danmaku,,0,0,0,,没有样式标签的弹幕
Dialogue: 0,0:00:03.00,0:00:07.32,Danmaku,,0,0,0,,{\\an8\\fs30}顶部弹幕
"""


def check(name, cond):
    print(('[PASS] ' if cond else '[FAIL] ') + name)
    return bool(cond)


def main():
    ok = True
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'test.ass')
        with open(p, 'w', encoding='utf-8') as f:
            f.write(ASS_SAMPLE)

        bcc = BiliBili._ass_to_bcc(p)
        print('BCC 长度 =', len(bcc))
        data = json.loads(bcc)
        body = data['body']

        print('顶层键 =', sorted(data.keys()))
        print('条目数 =', len(body), '(期望 4)')

        ok &= check('解析出 4 条（时间轴与文本同行）', len(body) == 4)
        ok &= check('起止时间从同行正确提取', abs(body[0]['from'] - 0.82) < 0.01
                    and abs(body[0]['to'] - 5.03) < 0.01)
        ok &= check('分钟换算正确 0:01:07.50 -> 67.5',
                    abs(body[2]['from'] - 67.5) < 0.01)
        ok &= check('内联样式标签被剥离',
                    all('{' not in b['content'] and '}' not in b['content'] for b in body))
        ok &= check('内容无前导逗号',
                    all(not b['content'].startswith(',') for b in body))
        ok &= check('第1 条内容正确', body[0]['content'] == '如同喝了')
        ok &= check('无样式行也正确解析', body[2]['content'] == '没有样式标签的弹幕')
        ok &= check('to始终大于 from', all(b['to'] > b['from'] for b in body))
        ok &= check('BCC 顶层含 B站必需字段',
                    set(['font_size', 'margin_v', 'margin_h', 'bold',
                         'italic', 'color', 'body', 'version']) <= set(data.keys()))
        print('\n样例:', json.dumps(data, ensure_ascii=False)[:260])

    # 边界：空文件不应崩溃
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'empty.ass')
        open(p, 'w', encoding='utf-8').close()
        ok &= check('空文件返回空字符串而不抛异常', BiliBili._ass_to_bcc(p) == '')

    # 边界：只有头部没有 Dialogue
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, 'head.ass')
        with open(p, 'w', encoding='utf-8') as f:
            f.write('[Script Info]\nTitle: x\n')
        ok &= check('仅头部无 Dialogue 时返回空字符串', BiliBili._ass_to_bcc(p) == '')

    print('\n结果：' + ('全部通过' if ok else '存在失败用例'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())