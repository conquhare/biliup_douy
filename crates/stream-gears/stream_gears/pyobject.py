from typing import Optional


class Segment:
    """视频分段设置"""

    @staticmethod
    def by_time(time: int) -> 'Segment':
        """
        按时长分段

        :param int time: 分段时长, 单位为秒
        :return: 视频分段设置
        """
        segment = Segment()
        segment.time = time
        return segment

    @staticmethod
    def by_size(size: int) -> 'Segment':
        """
        按大小分段

        :param int size: 分段大小, 单位为字节
        :return: 视频分段设置
        """
        segment = Segment()
        segment.size = size
        return segment


class Credit:
    """
    B站视频简介v2格式中的@对象

    用于在视频简介中@其他用户或话题

    :param int type_id: 类型ID，1表示@用户，2表示@话题
    :param str raw_text: 显示的原始文本
    :param Optional[str] biz_id: 业务ID，@用户时为UID，@话题时为话题ID
    """
    type_id: int
    raw_text: str
    biz_id: Optional[str]
