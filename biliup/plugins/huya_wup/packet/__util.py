锘縡rom functools import wraps
from biliup.common.tars import tarscore


STANDARD_CHARSET = 'utf-8'


def auto_decode_fields(cls):
    """閼奉亜濮╄В鐮佺猾璁宠厬閻ㄥ垺ytes绫诲瀷鏁版嵁閿涘苯瀵橀幏鐟卐ctor閸滃ap娑擃厾娈戝瓧绗︽稉?""
    original_read_from = cls.readFrom

    def _decode_recursive(obj):
        """閫掑綊瑙ｇ爜鐎电钖勬稉顓犳畱bytes鐎涙顔?""
        if isinstance(obj, bytes):
            try:
                return obj.decode(STANDARD_CHARSET)
            except UnicodeDecodeError:
                # 婵″倹鐏夎В鐮佸け璐ラ敍宀冪箲閸ョ偛甯慨濯寉tes
                return obj
        elif isinstance(obj, list):
            # 澶勭悊vector绫诲瀷閿涘牏鎴烽幍鑳殰list閿? 蹇呴』閸?hasattr(__dict__) 娑斿澧犳閺?
            for i in range(len(obj)):
                obj[i] = _decode_recursive(obj[i])
        elif isinstance(obj, dict):
            # 澶勭悊map绫诲瀷閿涘牏鎴烽幍鑳殰dict閿? 蹇呴』閸?hasattr(__dict__) 娑斿澧犳閺?
            keys_to_update = []
            for key in obj.keys():
                decoded_key = _decode_recursive(key)
                decoded_value = _decode_recursive(obj[key])
                keys_to_update.append((key, decoded_key, decoded_value))

            # 鏇存柊鐎涙鍚€
            for old_key, new_key, new_value in keys_to_update:
                if old_key != new_key:
                    del obj[old_key]
                    obj[new_key] = new_value
                else:
                    obj[old_key] = new_value
        elif hasattr(obj, '__dict__'):
            # 澶勭悊缂佹挻鐎担鎾愁嚠鐠?
            for attr_name, attr_value in vars(obj).items():
                setattr(obj, attr_name, _decode_recursive(attr_value))
        return obj

    @staticmethod
    @wraps(original_read_from)
    def wrapped_read_from(ios: tarscore.TarsInputStream):
        value = original_read_from(ios)
        # 闁秴宸荤€电钖勯惃鍕閺堝鐫橀幀褑绻樼悰宀冃掗惍?
        for attr_name, attr_value in vars(value).items():
            setattr(value, attr_name, _decode_recursive(attr_value))
        return value

    cls.readFrom = wrapped_read_from
    return cls