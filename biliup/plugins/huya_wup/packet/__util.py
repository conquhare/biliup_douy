from functools import wraps
from biliup.common.tars import tarscore


STANDARD_CHARSET = 'utf-8'


def auto_decode_fields(cls):
    """鑷姩解码绫讳腑鐨刡ytes类型数据锛屽寘鎷瑅ector鍜宮ap涓殑字符涓?""
    original_read_from = cls.readFrom

    def _decode_recursive(obj):
        """递归解码瀵硅薄涓殑bytes瀛楁"""
        if isinstance(obj, bytes):
            try:
                return obj.decode(STANDARD_CHARSET)
            except UnicodeDecodeError:
                # 濡傛灉解码失败锛岃繑鍥炲師濮媌ytes
                return obj
        elif isinstance(obj, list):
            # 处理vector类型锛堢户鎵胯嚜list锛? 必须鍦?hasattr(__dict__) 涔嬪墠检鏌?
            for i in range(len(obj)):
                obj[i] = _decode_recursive(obj[i])
        elif isinstance(obj, dict):
            # 处理map类型锛堢户鎵胯嚜dict锛? 必须鍦?hasattr(__dict__) 涔嬪墠检鏌?
            keys_to_update = []
            for key in obj.keys():
                decoded_key = _decode_recursive(key)
                decoded_value = _decode_recursive(obj[key])
                keys_to_update.append((key, decoded_key, decoded_value))

            # 更新瀛楀吀
            for old_key, new_key, new_value in keys_to_update:
                if old_key != new_key:
                    del obj[old_key]
                    obj[new_key] = new_value
                else:
                    obj[old_key] = new_value
        elif hasattr(obj, '__dict__'):
            # 处理缁撴瀯浣撳璞?
            for attr_name, attr_value in vars(obj).items():
                setattr(obj, attr_name, _decode_recursive(attr_value))
        return obj

    @staticmethod
    @wraps(original_read_from)
    def wrapped_read_from(ios: tarscore.TarsInputStream):
        value = original_read_from(ios)
        # 閬嶅巻瀵硅薄鐨勬墍鏈夊睘鎬ц繘琛岃В鐮?
        for attr_name, attr_value in vars(value).items():
            setattr(value, attr_name, _decode_recursive(attr_value))
        return value

    cls.readFrom = wrapped_read_from
    return cls