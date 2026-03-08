# path: f2/utils/abogus.py

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
@Description:abogus.py
@Date       :2024/06/16 11:21:14
@Author     :JohnserfSeed
@version    :0.0.3
@License    :Apache License 2.0
@Github     :https://github.com/johnserf-seed
@Mail       :support@f2.wiki
-------------------------------------------------
Change Log  :
2024/06/16 17:27:47 - Create ABogus algorithm & black style
2024/06/16 17:27:47 - Limit custom ua late open source full version
2024/07/08 21:50:12 - Open the full version of the custom UA
2025/03/05 155:55:42 - Perf Post Method Generate
-------------------------------------------------
"""

import time
import random

from gmssl import sm3, func
from typing import Union, Callable, List, Dict


class StringProcessor:
    """
    StringProcessor 绫荤敤浜庤绠桝Bogus绠楁硶涓墍闇€鐨勫瓧绗︿覆处理鏂规硶銆?
    包括字符涓插拰 ASCII 鐮佷箣闂寸殑转换銆佹棤绗﹀彿鍙崇Щ杩愮畻绛夈€?

    绫绘柟娉?

        to_ord_str(s: str) -> str:
            灏嗗瓧绗︿覆转换涓?ASCII 鐮佸瓧绗︿覆銆?

        to_ord_array(s: str) -> List[int]:
            灏嗗瓧绗︿覆转换涓?ASCII 鐮佸垪琛ㄣ€?

        to_char_str(s: List[int]) -> str:
            灏?ASCII 鐮佸垪琛ㄨ浆鎹负字符涓层€?

        to_char_array(s: str) -> List[int]:
            灏嗗瓧绗︿覆转换涓?ASCII 鐮佸垪琛ㄣ€?

        js_shift_right(val: int, n: int) -> int:
            实现 JavaScript 中的鏃犵鍙峰彸绉昏繍绠椼€?

        generate_random_bytes(length: int = 3) -> str:
            鐢熸垚涓€缁勪吉闅忔満字节字符涓诧紝鐢ㄤ簬娣锋穯数据銆?

    使用绀轰緥:
    ```python
        # 灏嗗瓧绗︿覆转换涓?ASCII 鐮佸瓧绗︿覆
        ord_str = StringProcessor.to_ord_str("Hello, World!")
        print(ord_str)

        # 灏嗗瓧绗︿覆转换涓?ASCII 鐮佸垪琛?
        ord_array = StringProcessor.to_ord_array("Hello, World!")
        print(ord_array)

        # 灏?ASCII 鐮佸垪琛ㄨ浆鎹负字符涓?
        char_str = StringProcessor.to_char_str(ord_array)
        print(char_str)

        # 灏嗗瓧绗︿覆转换涓?ASCII 鐮佸垪琛?
        char_array = StringProcessor.to_char_array("Hello, World!")
        print(char_array)

        # 实现 JavaScript 中的鏃犵鍙峰彸绉昏繍绠?
        shifted_val = StringProcessor.js_shift_right(10, 2)
        print(shifted_val)

        # 鐢熸垚涓€缁勪吉闅忔満字节字符涓?
        random_bytes = StringProcessor.generate_random_bytes(3)
        print(random_bytes)
    ```
    """

    @staticmethod
    def to_ord_str(s: str) -> str:
        """
        灏嗗瓧绗︿覆转换涓?ASCII 鐮佸瓧绗︿覆 (Convert a string to an ASCII code string).

        Args:
            s (str): 杈撳叆字符涓?(Input string).

        Returns:
            str: 转换后的 ASCII 鐮佸瓧绗︿覆 (Converted ASCII code string).
        """
        return "".join([chr(i) for i in s])

    @staticmethod
    def to_ord_array(s: str) -> List[int]:
        """
        灏嗗瓧绗︿覆转换涓?ASCII 鐮佸垪琛?(Convert a string to a list of ASCII codes).

        Args:
            s (str): 杈撳叆字符涓?(Input string).

        Returns:
            List[int]: 转换后的 ASCII 鐮佸垪琛?(Converted list of ASCII codes).
        """
        return [ord(char) for char in s]

    @staticmethod
    def to_char_str(s: List[int]) -> str:
        """
        灏?ASCII 鐮佸垪琛ㄨ浆鎹负字符涓?(Convert a list of ASCII codes to a string).

        Args:
            s (str): ASCII 鐮佸垪琛?(List of ASCII codes).

        Returns:
            str: 转换后的字符涓?(Converted string).
        """
        return "".join([chr(i) for i in s])

    @staticmethod
    def to_char_array(s: str) -> List[int]:
        """
        灏嗗瓧绗︿覆转换涓?ASCII 鐮佸垪琛?(Convert a string to a list of ASCII codes).

        Args:
            s (str): 杈撳叆字符涓?(Input string).

        Returns:
            List[int]: 转换后的 ASCII 鐮佸垪琛?(Converted list of ASCII codes).
        """
        return [ord(char) for char in s]

    @staticmethod
    def js_shift_right(val: int, n: int) -> int:
        """
        实现 JavaScript 中的鏃犵鍙峰彸绉昏繍绠?(Implement the unsigned right shift operation in JavaScript).

        Args:
            val (int): 杈撳叆鍊?(Input value).
            n (int): 鍙崇Щ浣嶆暟 (Number of bits to shift right).

        Returns:
            int: 鍙崇Щ后的鍊?(Value after right shift).
        """
        return (val % 0x100000000) >> n

    @staticmethod
    def generate_random_bytes(length: int = 3) -> str:
        """
        鐢熸垚涓€缁勪吉闅忔満字节字符涓诧紝鐢ㄤ簬娣锋穯数据 (Generate a pseudo-random byte string to obfuscate the data).

        Args:
            length (int): 鐢熸垚鐨勫瓧鑺傚簭鍒楅暱搴?(Length of the byte sequence to generate).

        Returns:
            str: 鐢熸垚鐨勪吉闅忔満字节字符涓?(Generated pseudo-random byte string).
        """

        def generate_byte_sequence() -> List[str]:
            _rd = int(random.random() * 10000)
            return [
                chr(((_rd & 255) & 170) | 1),
                chr(((_rd & 255) & 85) | 2),
                chr((StringProcessor.js_shift_right(_rd, 8) & 170) | 5),
                chr((StringProcessor.js_shift_right(_rd, 8) & 85) | 40),
            ]

        result = []
        for _ in range(length):
            result.extend(generate_byte_sequence())

        return "".join(result)


class CryptoUtility:
    """
    CryptoUtility 绫荤敤浜庢彁渚涘姞瀵嗗拰编码鐨勫伐鍏锋柟娉曪紝包括 SM3 鍝堝笇銆佹坊鍔犵洂鍊笺€丅ase64 编码鍜?RC4 加密绛夈€?

    绫诲睘鎬?
        salt (str): 加密鐩愬€?(Encryption salt).
        base64_alphabet (List[str]): 鑷畾涔?Base64 字符琛?(Custom Base64 alphabet).

    绫绘柟娉?
        sm3_to_array(input_data: Union[str, List[int]]) -> List[int]:
            璁＄畻请求浣撶殑 SM3 鍝堝笇鍊硷紝骞跺皢结果转换涓烘暣鏁版暟缁勩€?

        add_salt(param: str) -> str:
            涓哄瓧绗︿覆参数娣诲姞鐩愬€笺€?

        process_param(param: Union[str, List[int]], add_salt: bool) -> Union[str, List[int]]:
            处理杈撳叆参数锛屾牴鎹渶瑕佹坊鍔犵洂鍊笺€?

        params_to_array(param: Union[str, List[int]], add_salt: bool = True) -> List[int]:
            获取杈撳叆参数鐨勫搱甯屾暟缁勩€?

        transform_bytes(bytes_list: List[int]) -> str:
            对输入的字节列表进行加密/解密操作锛岃繑鍥炲鐞嗗悗鐨勫瓧绗︿覆銆?

        base64_encode(input_string: str, selected_alphabet: int = 0) -> str:
            使用鑷畾涔夊瓧绗﹁〃对输鍏ュ瓧绗︿覆进行 Base64 编码銆?

        abogus_encode(abogus_bytes_str: str, selected_alphabet: int) -> str:
            对输入的字节字符涓茶繘琛岃嚜瀹氫箟 Base64 编码锛屽苟娣诲姞浣嶇Щ鍜屽～鍏呫€?

        rc4_encrypt(key: bytes, plaintext: str) -> bytes:
            使用 RC4 绠楁硶加密数据銆?

    使用绀轰緥:
    ```python
        # 璁＄畻请求浣撶殑 SM3 鍝堝笇鍊?
        sm3_hash = CryptoUtility.sm3_to_array("Hello, World!")
        print(sm3_hash)

        # 涓哄瓧绗︿覆参数娣诲姞鐩愬€?
        salted_param = CryptoUtility.add_salt("Hello, World!")
        print(salted_param)

        # 获取杈撳叆参数鐨勫搱甯屾暟缁?
        hash_array = CryptoUtility.params_to_array("Hello, World!")
        print(hash_array)

        # 对输入的字节列表进行加密/解密操作
        encrypted_str = CryptoUtility.transform_bytes([72, 101, 108, 108, 111, 44, 32, 87, 111, 114, 108, 100, 33])
        print(encrypted_str)

        # 使用鑷畾涔夊瓧绗﹁〃对输鍏ュ瓧绗︿覆进行 Base64 编码
        base64_str = CryptoUtility.base64_encode("Hello, World!")
        print(base64_str)

        # 对输入的字节字符涓茶繘琛岃嚜瀹氫箟 Base64 编码锛屽苟娣诲姞浣嶇Щ鍜屽～鍏?
        abogus_str = CryptoUtility.abogus_encode("Hello, World!", 0)
        print(abogus_str)

        # 使用 RC4 绠楁硶加密数据
        key = b"key"
        plaintext = "Hello, World!"
        ciphertext = CryptoUtility.rc4_encrypt(key, plaintext)
        print(ciphertext)
    ```
    """

    def __init__(self, salt: str, custom_base64_alphabet: List[str]):
        """
        鍒濆鍖?CryptoUtility 绫?
        Initialize the CryptoUtility class.

        Args:
            salt (str): 加密鐩愬€?(Encryption salt).
            custom_base64_alphabet (List[str]): 鑷畾涔?Base64 字符琛?(Custom Base64 alphabet).
        """
        self.salt = salt
        self.base64_alphabet = custom_base64_alphabet

        # fmt: off
        self.big_array = [
            121, 243,  55, 234, 103,  36,  47, 228,  30, 231, 106,   6, 115,  95,  78, 101, 250, 207, 198,  50,
            139, 227, 220, 105,  97, 143,  34,  28, 194, 215,  18, 100, 159, 160,  43,   8, 169, 217, 180, 120,
            247,  45,  90,  11,  27, 197,  46,   3,  84,  72,   5,  68,  62,  56, 221,  75, 144,  79,  73, 161,
            178,  81,  64, 187, 134, 117, 186, 118,  16, 241, 130,  71,  89, 147, 122, 129,  65,  40,  88, 150,
            110, 219, 199, 255, 181, 254,  48,   4, 195, 248, 208,  32, 116, 167,  69, 201,  17, 124, 125, 104,
             96,  83,  80, 127, 236, 108, 154, 126, 204,  15,  20, 135, 112, 158,  13,   1, 188, 164, 210, 237,
            222,  98, 212,  77, 253,  42, 170, 202,  26,  22,  29, 182, 251,  10, 173, 152,  58, 138,  54, 141,
            185,  33, 157,  31, 252, 132, 233, 235, 102, 196, 191, 223, 240, 148,  39, 123,  92,  82, 128, 109,
             57,  24,  38, 113, 209, 245,   2, 119, 153, 229, 189, 214, 230, 174, 232,  63,  52, 205,  86, 140,
             66, 175, 111, 171, 246, 133, 238, 193,  99,  60,  74,  91, 225,  51,  76,  37, 145, 211, 166, 151,
            213, 206,   0, 200, 244, 176, 218,  44, 184, 172,  49, 216,  93, 168,  53,  21, 183,  41,  67,  85,
            224, 155, 226, 242,  87, 177, 146,  70, 190,  12, 162,  19, 137, 114,  25, 165, 163, 192,  23,  59,
              9,  94, 179, 107,  35,   7, 142, 131, 239, 203, 149, 136,  61, 249,  14, 156
        ]
        # fmt: on

    @staticmethod
    def sm3_to_array(input_data: Union[str, List[int]]) -> List[int]:
        """
        璁＄畻请求浣撶殑 SM3 鍝堝笇鍊硷紝骞跺皢结果转换涓烘暣鏁版暟缁?(Calculate the SM3 hash value of the request body and convert the result to an array of integers).

        Args:
            input_data (Union[str, List[int]]): 杈撳叆数据 (Input data).

        Returns:
            List[int]: 鍝堝笇鍊肩殑鏁存暟鏁扮粍 (Array of integers representing the hash value).
        """
        # 如果杈撳叆鏄瓧绗︿覆锛屽垯灏嗗叾编码涓哄瓧鑺傛暟缁?
        if isinstance(input_data, str):
            input_data_bytes = input_data.encode("utf-8")
        else:
            input_data_bytes = bytes(input_data)  # 灏?List[int] 转换涓哄瓧鑺傛暟缁?

        # 灏嗗瓧鑺傛暟缁勮浆鎹负閫傚悎 sm3.sm3_hash 鍑芥暟处理鐨勫垪琛ㄦ牸寮?
        hex_result = sm3.sm3_hash(func.bytes_to_list(input_data_bytes))

        # 灏嗗崄鍏繘鍒跺瓧绗︿覆结果转换涓哄崄杩涘埗鏁存暟列表
        return [int(hex_result[i : i + 2], 16) for i in range(0, len(hex_result), 2)]

    def add_salt(self, param: str) -> str:
        """
        涓哄瓧绗︿覆参数娣诲姞鐩愬€?(Add salt to the string parameter).

        Args:
            param (str): 杈撳叆字符涓?(Input string).

        Returns:
            str: 娣诲姞鐩愬€煎悗鐨勫瓧绗︿覆 (String with added salt).
        """
        return param + self.salt

    def process_param(
        self, param: Union[str, List[int]], add_salt: bool
    ) -> Union[str, List[int]]:
        """
        处理杈撳叆参数锛屾牴鎹渶瑕佹坊鍔犵洂鍊?(Process input parameter and add salt if needed).

        Args:
            param (Union[str, List[int]]): 杈撳叆参数 (Input parameter).
            add_salt (bool): 鏄惁娣诲姞鐩愬€?(Whether to add salt).

        Returns:
            Union[str, List[int]]: 处理后的参数 (Processed parameter).
        """
        if isinstance(param, str) and add_salt:
            param = self.add_salt(param)
        return param

    def params_to_array(
        self, param: Union[str, List[int]], add_salt: bool = True
    ) -> List[int]:
        """
        获取杈撳叆参数鐨勫搱甯屾暟缁?(Get the hash array of the input parameter).

        Args:
            param (Union[str, List[int]]): 杈撳叆参数 (Input parameter).
            add_salt (bool): 鏄惁娣诲姞鐩愬€?(Whether to add salt).

        Returns:
            List[int]: 鍝堝笇鏁扮粍 (Hash array).
        """
        processed_param = self.process_param(param, add_salt)
        return self.sm3_to_array(processed_param)

    def transform_bytes(self, bytes_list: List[int]) -> str:
        """
        对输入的字节列表进行加密/解密操作锛岃繑鍥炲鐞嗗悗鐨勫瓧绗︿覆 (Encrypt/decrypt the input byte list and return the processed string).

        Args:
            bytes_list (List[int]): 杈撳叆鐨勫瓧鑺傚垪琛?(Input byte list).

        Returns:
            str: 处理后的字符涓?(Processed string).
        """
        # 灏嗗瓧鑺傚垪琛ㄨ浆鎹负字符字符涓?
        bytes_str = StringProcessor.to_char_str(bytes_list)
        result_str = []
        index_b = self.big_array[1]
        initial_value = 0

        for index, char in enumerate(bytes_str):
            if index == 0:
                initial_value = self.big_array[index_b]
                sum_initial = index_b + initial_value

                self.big_array[1] = initial_value
                self.big_array[index_b] = index_b
            else:
                sum_initial = initial_value + value_e

            char_value = ord(char)
            sum_initial %= len(self.big_array)
            value_f = self.big_array[sum_initial]
            encrypted_char = char_value ^ value_f
            result_str.append(chr(encrypted_char))

            # 浜ゆ崲鏁扮粍鍏冪礌
            value_e = self.big_array[(index + 2) % len(self.big_array)]
            sum_initial = (index_b + value_e) % len(self.big_array)
            initial_value = self.big_array[sum_initial]
            self.big_array[sum_initial] = self.big_array[
                (index + 2) % len(self.big_array)
            ]
            self.big_array[(index + 2) % len(self.big_array)] = initial_value
            index_b = sum_initial

        return "".join(result_str)

    def base64_encode(self, input_string: str, selected_alphabet: int = 0) -> str:
        """
        使用鑷畾涔夊瓧绗﹁〃对输鍏ュ瓧绗︿覆进行 Base64 编码 (Encode the input string using a custom Base64 alphabet).

        Args:
            input_string (str): 杈撳叆字符涓?(Input string).
            selected_alphabet (int): 选择鐨勮嚜瀹氫箟 Base64 字符琛ㄧ储寮?(Selected custom Base64 alphabet index).

        Returns:
            str: 编码后的字符涓?(Encoded string).
        """

        # 灏嗚緭鍏ュ瓧绗︿覆转换涓篈SCII鐮佺殑浜岃繘鍒跺舰寮?
        binary_string = "".join(["{:08b}".format(ord(char)) for char in input_string])

        # 琛ュ叏浜岃繘鍒跺瓧绗︿覆浣垮叾闀垮害涓?鐨勫€嶆暟
        padding_length = (6 - len(binary_string) % 6) % 6
        binary_string += "0" * padding_length

        # 灏嗕簩杩涘埗字符涓插垎鍓蹭负6浣嶄竴缁?
        base64_indices = [
            int(binary_string[i : i + 6], 2) for i in range(0, len(binary_string), 6)
        ]

        # 鏍规嵁鑷畾涔夊瓧绗﹁〃鐢熸垚杈撳嚭字符涓?
        output_string = "".join(
            [self.base64_alphabet[selected_alphabet][index] for index in base64_indices]
        )

        # 娣诲姞绛夊彿濉厖锛屼娇符合 Base64 编码规范
        output_string += "=" * (padding_length // 2)

        return output_string

    def abogus_encode(self, abogus_bytes_str: str, selected_alphabet: int) -> str:
        """
        对输入的字节字符涓茶繘琛岃嚜瀹氫箟 Base64 编码锛屽苟娣诲姞浣嶇Щ鍜屽～鍏?(Encode the input byte string using a custom Base64 alphabet, and add shifts and padding).

        Args:
            abogus_bytes_str (str): 杈撳叆鐨勫瓧鑺傚瓧绗︿覆 (Input byte string).
            selected_alphabet (int): 选择鐨勮嚜瀹氫箟 Base64 字符琛ㄧ储寮?(Selected custom Base64 alphabet index).

        Returns:
            str: 编码后的字符涓?(Encoded string).
        """
        abogus = []

        for i in range(0, len(abogus_bytes_str), 3):
            if i + 2 < len(abogus_bytes_str):
                n = (
                    (ord(abogus_bytes_str[i]) << 16)
                    | (ord(abogus_bytes_str[i + 1]) << 8)
                    | ord(abogus_bytes_str[i + 2])
                )
            elif i + 1 < len(abogus_bytes_str):
                n = (ord(abogus_bytes_str[i]) << 16) | (
                    ord(abogus_bytes_str[i + 1]) << 8
                )
            else:
                n = ord(abogus_bytes_str[i]) << 16

            for j, k in zip(range(18, -1, -6), (0xFC0000, 0x03F000, 0x0FC0, 0x3F)):
                if j == 6 and i + 1 >= len(abogus_bytes_str):
                    break
                if j == 0 and i + 2 >= len(abogus_bytes_str):
                    break
                abogus.append(self.base64_alphabet[selected_alphabet][(n & k) >> j])

        abogus.append("=" * ((4 - len(abogus) % 4) % 4))
        return "".join(abogus)

    @staticmethod
    def rc4_encrypt(key: bytes, plaintext: str) -> bytes:
        """
        使用 RC4 绠楁硶加密数据 (Encrypt data using the RC4 algorithm).

        Args:
            key (bytes): 加密瀵嗛挜 (Encryption key).
            plaintext (str): 鏄庢枃数据 (Plaintext data).

        Returns:
            bytes: 加密后的数据 (Encrypted data).
        """
        S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + key[i % len(key)]) % 256
            S[i], S[j] = S[j], S[i]

        i = j = 0
        ciphertext = []
        for char in plaintext:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            K = S[(S[i] + S[j]) % 256]
            ciphertext.append(ord(char) ^ K)

        return bytes(ciphertext)


class BrowserFingerprintGenerator:
    """
    BrowserFingerprintGenerator 鐢ㄤ簬鐢熸垚模拟鐨勬祻瑙堝櫒鎸囩汗信息锛岀敤浜庡湪不同娴忚鍣ㄧ幆澧冧腑进行娴嬭瘯鍜屾暟鎹噰闆嗐€?

    绫诲睘鎬?
        browsers (Dict[str, Callable[[], str]]): 娴忚鍣ㄧ被鍨嬪拰鐢熸垚娴忚鍣ㄦ寚绾圭殑鏄犲皠鍏崇郴銆?

    鏂规硶:
        generate_fingerprint(browser_type="Edge"):
            鏍规嵁鎸囧畾鐨勬祻瑙堝櫒类型鐢熸垚娴忚鍣ㄦ寚绾广€?

        generate_chrome_fingerprint():
            鐢熸垚 Chrome 娴忚鍣ㄦ寚绾广€?

        generate_firefox_fingerprint():
            鐢熸垚 Firefox 娴忚鍣ㄦ寚绾广€?

        generate_safari_fingerprint():
            鐢熸垚 Safari 娴忚鍣ㄦ寚绾广€?

        generate_edge_fingerprint():
            鐢熸垚 Edge 娴忚鍣ㄦ寚绾广€?

        _generate_fingerprint(platform="Win32"):
            鏍规嵁缁欏畾鐨勫弬鏁扮敓鎴愭祻瑙堝櫒鎸囩汗字符涓层€?

    使用绀轰緥:
    ```python
        chrome_fp = BrowserFingerprintGenerator.generate_fingerprint("Chrome")
        print(chrome_fp)
    ```
    """

    @classmethod
    def generate_fingerprint(cls, browser_type: str = "Edge") -> str:
        """
        鏍规嵁鎸囧畾鐨勬祻瑙堝櫒类型鐢熸垚娴忚鍣ㄦ寚绾广€?(Generate a browser fingerprint based on the specified browser type.)

        Args:
            browser_type (str): 娴忚鍣ㄧ被鍨?(Browser type).

        Returns:
            str: 鐢熸垚鐨勬祻瑙堝櫒鎸囩汗字符涓?(Generated browser fingerprint string).
        """
        cls.browsers: Dict[str, Callable[[], str]] = {
            "Chrome": cls.generate_chrome_fingerprint,
            "Firefox": cls.generate_firefox_fingerprint,
            "Safari": cls.generate_safari_fingerprint,
            "Edge": cls.generate_edge_fingerprint,
        }
        return cls.browsers.get(browser_type, cls.generate_chrome_fingerprint)()

    @classmethod
    def generate_chrome_fingerprint(cls) -> str:
        return cls._generate_fingerprint(platform="Win32")

    @classmethod
    def generate_firefox_fingerprint(cls) -> str:
        return cls._generate_fingerprint(platform="Win32")

    @classmethod
    def generate_safari_fingerprint(cls) -> str:
        return cls._generate_fingerprint(platform="MacIntel")

    @classmethod
    def generate_edge_fingerprint(cls) -> str:
        return cls._generate_fingerprint(platform="Win32")

    @staticmethod
    def _generate_fingerprint(platform: str) -> str:
        """
        鏍规嵁缁欏畾鐨勫弬鏁扮敓鎴愭祻瑙堝櫒鎸囩汗字符涓层€?(Generate a browser fingerprint string based on the given parameters.)

        Args:
            platform (str): 操作绯荤粺骞冲彴 (Operating system platform).

        Returns:
            str: 鐢熸垚鐨勬祻瑙堝櫒鎸囩汗字符涓?(Generated browser fingerprint string).
        """
        inner_wdth = random.randint(1024, 1920)
        inner_height = random.randint(768, 1080)
        outer_wdth = inner_wdth + random.randint(24, 32)
        outer_height = inner_height + random.randint(75, 90)
        screen_x = 0
        screen_y = random.choice([0, 30])
        size_wdth = random.randint(1024, 1920)
        size_height = random.randint(768, 1080)
        avail_wdth = random.randint(1280, 1920)
        avail_height = random.randint(800, 1080)

        fingerprint = (
            f"{inner_wdth}|{inner_height}|{outer_wdth}|{outer_height}|"
            f"{screen_x}|{screen_y}|0|0|{size_wdth}|{size_height}|"
            f"{avail_wdth}|{avail_height}|{inner_wdth}|{inner_height}|24|24|{platform}"
        )
        return fingerprint


class ABogus:
    """
    ABogus 绫荤敤浜庣敓鎴?ABogus 参数銆?

    绫诲睘鎬?
        array1 (List[int]): 加密请求浣?(Encrypted request body).
        array2 (List[int]): 加密请求澶?(Encrypted request header).
        array3 (List[int]): 加密 UA (Encrypted User-Agent).
        ad (int): AID 鍊?(AID value).
        pageId (int): 椤甸潰 ID (Page ID).
        salt (str): 加密鐩愬€?(Encryption salt).
        options (List[int]): 请求閫夐」 (Request options).
        ua_key (bytes): UA 加密瀵嗛挜 (UA encryption key).
        character (str): 鑷畾涔?Base64 字符琛?(Custom Base64 alphabet).
        character2 (str): 鑷畾涔?Base64 字符琛?(Custom Base64 alphabet).
        character_list (List[str]): 鑷畾涔?Base64 字符琛ㄥ垪琛?(List of custom Base64 alphabets).
        crypto_utility (CryptoUtility): 加密工具绫?(Encryption utility).
        user_agent (str): 鑷畾涔?UA (Custom User-Agent).
        browser_fp (str): 娴忚鍣ㄦ寚绾?(Browser fingerprint).
        sort_index (List[int]): 鎺掑簭绱㈠紩 (Sort index).
        sort_index_2 (List[int]): 鎺掑簭绱㈠紩 (Sort index).

    说明锛?
        options 参数鐢ㄤ簬鎸囧畾请求鐨勭被鍨嬶紝GET 请求使用 [0, 1, 8]锛孭OST 请求使用 [0, 1, 14]銆?4鍏煎8锛孭OST鍚屾牱鍙互编码params锛屾晠鍐欐銆?
        (The options parameter is used to specify the type of request. GET requests use [0, 1, 8], and POST requests use [0, 1, 14]. 14 is compatible with 8, and POST can also encode params, so it is hardcoded.)

    鏂规硶:
        encode_data(data: str, alphabet_index: int = 0) -> str:
            使用鎸囧畾鐨勫瓧绗﹁〃瀵规暟鎹繘琛?Base64 编码 (Encode the data using the specified Base64 alphabet).

        generate_abogus(params: str, request: str = "") -> str:
            鐢熸垚 ABogus 参数 (Generate the ABogus parameter).

    使用绀轰緥:
    ```python
        # 鐢熸垚 ABogus 参数锛岀疆绌轰娇鐢ㄩ粯璁?UA 鍜屾祻瑙堝櫒鎸囩汗
        abogus = ABogus(user_agent="xxx", fp="xxx")
        abogus_param = abogus.generate_abogus("device_platform=webapp&ad=6383&channel=channel_pc_web&aweme_d=7380308675841297704鈥︹€︾渷鐣モ€︹€?)
        print(abogus_param[1])
    ```
    """

    def __init__(
        self,
        fp: str = "",
        user_agent: str = "",
        options: List[int] = [0, 1, 14],
    ):
        self.ad = 6383
        self.pageId = 0  # 1.0.1.19 ->  6241
        self.salt = "cus"  # 1.0.1.19 -> 加密鐩?# dhzx
        self.boe = False
        self.ddrt = 8.5
        self.ic = 8.5
        self.paths = [
            "^/webcast/",
            "^/aweme/v1/",
            "^/aweme/v2/",
            "/v1/message/send",
            "^/live/",
            "^/captcha/",
            "^/ecom/",
        ]
        self.array1 = []  # 加密请求浣?
        self.array2 = []  # 加密请求澶?涓虹┖
        self.array3 = []  # 加密UA
        self.options = options  # GET [0, 1, 8] POST [0, 1, 14]
        self.ua_key = b"\x00\x01\x0E"  # ua加密key

        self.character = (
            "Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe"
        )
        self.character2 = (
            "ckdp1h4ZKsUB80/Mfvw36XIgR25+WQAlEi7NLboqYTOPuzmFjJnryx9HVGDaStCe"
        )
        self.character_list = [self.character, self.character2]  # 鑷畾涔塨ase64字符琛?

        self.crypto_utility = CryptoUtility(
            self.salt, self.character_list
        )  # 加密工具绫?

        self.user_agent = (
            user_agent
            if user_agent is not None and user_agent != ""
            else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
        )  # 鑷畾涔塽a锛屼负绌哄垯设置涓€涓粯璁a

        self.browser_fp = (
            fp
            if fp is not None and fp != ""
            else BrowserFingerprintGenerator.generate_fingerprint("Edge")
        )  # 鑷畾涔夋祻瑙堝櫒鎸囩汗锛屼负绌哄垯鐢熸垚Edge鎸囩汗

        # fmt: off
        self.sort_index = [
            18, 20, 52, 26, 30, 34, 58, 38, 40, 53, 42, 21, 27, 54, 55, 31, 35, 57, 39, 41, 43, 22, 28,
            32, 60, 36, 23, 29, 33, 37, 44, 45, 59, 46, 47, 48, 49, 50, 24, 25, 65, 66, 70, 71
        ]
        self.sort_index_2 = [
            18, 20, 26, 30, 34, 38, 40, 42, 21, 27, 31, 35, 39, 41, 43, 22, 28, 32, 36, 23, 29, 33, 37,
            44, 45, 46, 47, 48, 49, 50, 24, 25, 52, 53, 54, 55, 57, 58, 59, 60, 65, 66, 70, 71
        ]
        # fmt: on

    def encode_data(self, data: str, alphabet_index: int = 0) -> str:
        """
        使用鎸囧畾鐨勫瓧绗﹁〃瀵规暟鎹繘琛?Base64 编码 (Encode the data using the specified Base64 alphabet).

        Args:
            data (str): 杈撳叆数据 (Input data).
            alphabet_index (int): 鑷畾涔夊瓧绗﹁〃绱㈠紩 (Custom alphabet index).

        Returns:
            str: 编码后的数据 (Encoded data).
        """
        return self.crypto_utility.abogus_encode(data, alphabet_index)

    def generate_abogus(self, params: str, body: str = "") -> tuple:
        """
        鐢熸垚 abogus 参数 (Generate the ABogus parameter).

        Args:
            params (str): 请求参数 (Request parameters).
            body (str): 请求浣擄紝GET鎺ュ彛鍒欎负绌?(Request body, empty for GET interfaces).

        Returns:
            tuple: params 鐢熸垚鐨?abogus 参数 鍜?ua (ABogus parameter generated by params and ua).
        """
        ab_dir = {
            8: 3,  # 鍥哄畾
            15: {
                "ad": self.ad,
                "pageId": self.pageId,
                "boe": self.boe,
                "ddrt": self.ddrt,
                "paths": self.paths,
                "track": {"mode": 0, "delay": 300, "paths": []},
                "dump": True,
                "rpU": "",
            },
            18: 44,
            19: [1, 0, 1, 0, 1],
            66: 0,  # 鍥哄畾
            69: 0,  # 鍥哄畾
            70: 0,  # 鍥哄畾
            71: 0,  # 鍥哄畾
        }

        # 寮€濮嬪姞瀵嗘椂闂?
        start_encryption = int(time.time() * 1000)

        # params参数鍔犵洂加密
        array1 = self.crypto_utility.params_to_array(
            self.crypto_utility.params_to_array(params)
        )
        array2 = self.crypto_utility.params_to_array(
            self.crypto_utility.params_to_array(body)
        )
        array3 = self.crypto_utility.params_to_array(
            self.crypto_utility.base64_encode(
                StringProcessor.to_ord_str(
                    self.crypto_utility.rc4_encrypt(self.ua_key, self.user_agent)
                ),
                1,
            ),
            add_salt=False,
        )

        # 结束加密时间
        end_encryption = int(time.time() * 1000)

        # 插入加密寮€濮嬫椂闂?
        ab_dir[20] = (start_encryption >> 24) & 255
        ab_dir[21] = (start_encryption >> 16) & 255
        ab_dir[22] = (start_encryption >> 8) & 255
        ab_dir[23] = start_encryption & 255
        ab_dir[24] = int(start_encryption / 256 / 256 / 256 / 256) >> 0
        ab_dir[25] = int(start_encryption / 256 / 256 / 256 / 256 / 256) >> 0

        # 插入请求澶撮厤缃?
        ab_dir[26] = (self.options[0] >> 24) & 255
        ab_dir[27] = (self.options[0] >> 16) & 255
        ab_dir[28] = (self.options[0] >> 8) & 255
        ab_dir[29] = self.options[0] & 255

        # 插入请求鏂规硶
        ab_dir[30] = int(self.options[1] / 256) & 255
        ab_dir[31] = (self.options[1] % 256) & 255
        ab_dir[32] = (self.options[1] >> 24) & 255
        ab_dir[33] = (self.options[1] >> 16) & 255

        # 插入请求澶村姞瀵?
        ab_dir[34] = (self.options[2] >> 24) & 255
        ab_dir[35] = (self.options[2] >> 16) & 255
        ab_dir[36] = (self.options[2] >> 8) & 255
        ab_dir[37] = self.options[2] & 255

        # 插入请求浣撳姞瀵?
        ab_dir[38] = array1[21]
        ab_dir[39] = array1[22]
        # 插入body加密
        ab_dir[40] = array2[21]
        ab_dir[41] = array2[22]
        # 插入ua加密
        ab_dir[42] = array3[23]
        ab_dir[43] = array3[24]

        # 插入加密结束时间
        ab_dir[44] = (end_encryption >> 24) & 255
        ab_dir[45] = (end_encryption >> 16) & 255
        ab_dir[46] = (end_encryption >> 8) & 255
        ab_dir[47] = end_encryption & 255
        ab_dir[48] = ab_dir[8]
        ab_dir[49] = int(end_encryption / 256 / 256 / 256 / 256) >> 0
        ab_dir[50] = int(end_encryption / 256 / 256 / 256 / 256 / 256) >> 0

        # 插入鍥哄畾鍊?
        ab_dir[51] = (self.pageId >> 24) & 255
        ab_dir[52] = (self.pageId >> 16) & 255
        ab_dir[53] = (self.pageId >> 8) & 255
        ab_dir[54] = self.pageId & 255
        ab_dir[55] = self.pageId
        ab_dir[56] = self.ad
        ab_dir[57] = self.ad & 255
        ab_dir[58] = (self.ad >> 8) & 255
        ab_dir[59] = (self.ad >> 16) & 255
        ab_dir[60] = (self.ad >> 24) & 255

        # 插入娴忚鍣ㄦ寚绾?
        ab_dir[64] = len(self.browser_fp)
        ab_dir[65] = len(self.browser_fp)

        # 获取 ab_dir 涓?sort_index 鐨勫€?
        sorted_values = [ab_dir.get(i, 0) for i in self.sort_index]

        # 灏嗘祻瑙堝櫒鎸囩汗转换涓?ASCII 鐮佸垪琛?
        edge_fp_array = StringProcessor.to_char_array(self.browser_fp)

        # 灏嗘祻瑙堝櫒鎸囩汗闀垮害鐨勪綆 8 浣嶄綔涓哄紓鎴栧€?
        ab_xor = (len(self.browser_fp) & 255) >> 8 & 255

        # 进行寮傛垨璁＄畻
        for index in range(len(self.sort_index_2) - 1):
            if index == 0:
                ab_xor = ab_dir.get(self.sort_index_2[index], 0)
            ab_xor ^= ab_dir.get(self.sort_index_2[index + 1], 0)

        sorted_values.extend(edge_fp_array)
        sorted_values.append(ab_xor)

        abogus_bytes_str = (
            StringProcessor.generate_random_bytes()
            + self.crypto_utility.transform_bytes(sorted_values)
        )

        abogus = self.crypto_utility.abogus_encode(abogus_bytes_str, 0)
        params = "%s&a_bogus=%s" % (params, abogus)
        return (params, abogus, self.user_agent, body)


if __name__ == "__main__":
    # 24/06/16 鏅氱偣寮€婧愯嚜瀹氫箟ua
    # 24/07/08 支持鑷畾涔塽a鍜屾祻瑙堝櫒鎸囩汗
    # 24/11/15 完成1.0.1.19鐗堟湰abogus绠楁硶锛屾嫨鏃ュ紑婧?
    # 25/03/05 淇POST请求参数加密错误锛屼慨琛ョ幆澧?

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
    chrome_fp = BrowserFingerprintGenerator.generate_fingerprint("Edge")
    abogus = ABogus(user_agent=user_agent, fp=chrome_fp)

    # GET
    url = "https://www.douyin.com/aweme/v1/web/aweme/detail/?"
    params = "device_platform=webapp&ad=6383&channel=channel_pc_web&sec_user_d=MS4wLjABAAAArDVBosPJF3eIWVEFp0szuJ-e1V_-rK0ieJeWwpE77E8&max_cursor=0&locate_query=false&show_live_replay_strategy=1&need_time_list=1&time_list_query=0&whale_cut_token=&cut_version=1&count=18&publish_vdeo_strategy_type=2&from_user_page=1&update_version_code=170400&pc_client_type=1&pc_libra_divert=Windows&support_h265=1&support_dash=0&version_code=290100&version_name=29.1.0&cookie_enabled=true&screen_wdth=1920&screen_height=1080&browser_language=zh-CN&browser_platform=Win32&browser_name=Edge&browser_version=131.0.0.0&browser_online=true&engine_name=Blink&engine_version=131.0.0.0&os_name=Windows&os_version=10&cpu_core_num=12&device_memory=8&platform=PC&downlink=10&effective_type=4g&round_trip_time=50"
    body = ""
    print(url + abogus.generate_abogus(params=params, body=body)[0])

    # POST
    url = "https://www.douyin.com/aweme/v2/web/aweme/stats/?"
    params = "device_platform=webapp&ad=6383&channel=channel_pc_web&pc_client_type=1&pc_libra_divert=Windows&update_version_code=170400&support_h265=1&support_dash=0&version_code=170400&version_name=17.4.0&cookie_enabled=true&screen_wdth=1920&screen_height=1080&browser_language=zh-CN&browser_platform=Win32&browser_name=Edge&browser_version=131.0.0.0&browser_online=true&engine_name=Blink&engine_version=131.0.0.0&os_name=Windows&os_version=10&cpu_core_num=12&device_memory=8&platform=PC&downlink=10&effective_type=4g&round_trip_time=50"
    body = "aweme_type=0&item_d=7467485482314763572&play_delta=1&source=0"
    print(url + abogus.generate_abogus(params=params, body=body)[0])

    # # 娴嬭瘯鐢熸垚100涓猘bogus参数 鍜?100涓寚绾规墍闇€时间
    # start = time.time()
    # for _ in range(100):
    #     abogus.generate_abogus(params=params, body=body)
    # end = time.time()
    # print("鐢熸垚100涓猘bogus参数鍜屾寚绾规墍闇€时间:", end - start)  # 鐢熸垚100涓猘bogus参数鍜屾寚绾规墍闇€时间: 2.203000783920288

    # start = time.time()
    # for _ in range(100):
    #     BrowserFingerprintGenerator.generate_fingerprint("Chrome")
    # end = time.time()
    # print("鐢熸垚100涓寚绾规墍闇€时间:", end - start)  # 鐢熸垚100涓寚绾规墍闇€时间: 0.00400090217590332
