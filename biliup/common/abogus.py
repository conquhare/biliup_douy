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
    StringProcessor 类用于算ABogus算法三的字符串方法?
    ַ串和 ASCII 码之间的ת、无符号右移运算等?

    类方?

        to_ord_str(s: str) -> str:
            将字符串ת?ASCII 码字符串?

        to_ord_array(s: str) -> List[int]:
            将字符串ת?ASCII 码列表?

        to_char_str(s: List[int]) -> str:
            ?ASCII 码列表转捸ַ串?

        to_char_array(s: str) -> List[int]:
            将字符串ת?ASCII 码列表?

        js_shift_right(val: int, n: int) -> int:
            ʵ JavaScript е无号右移运算?

        generate_random_bytes(length: int = 3) -> str:
            生成组伪随机ַֽ串，用于混淆?

    ʹ示例:
    ```python
        # 将字符串ת?ASCII 码字符串
        ord_str = StringProcessor.to_ord_str("Hello, World!")
        print(ord_str)

        # 将字符串ת?ASCII 码列?
        ord_array = StringProcessor.to_ord_array("Hello, World!")
        print(ord_array)

        # ?ASCII 码列表转捸ַ?
        char_str = StringProcessor.to_char_str(ord_array)
        print(char_str)

        # 将字符串ת?ASCII 码列?
        char_array = StringProcessor.to_char_array("Hello, World!")
        print(char_array)

        # ʵ JavaScript е无号右移运?
        shifted_val = StringProcessor.js_shift_right(10, 2)
        print(shifted_val)

        # 生成组伪随机ַֽ?
        random_bytes = StringProcessor.generate_random_bytes(3)
        print(random_bytes)
    ```
    """

    @staticmethod
    def to_ord_str(s: str) -> str:
        """
        将字符串ת?ASCII 码字符串 (Convert a string to an ASCII code string).

        Args:
            s (str): 输入ַ?(Input string).

        Returns:
            str: ת ASCII 码字符串 (Converted ASCII code string).
        """
        return "".join([chr(i) for i in s])

    @staticmethod
    def to_ord_array(s: str) -> List[int]:
        """
        将字符串ת?ASCII 码列?(Convert a string to a list of ASCII codes).

        Args:
            s (str): 输入ַ?(Input string).

        Returns:
            List[int]: ת ASCII 码列?(Converted list of ASCII codes).
        """
        return [ord(char) for char in s]

    @staticmethod
    def to_char_str(s: List[int]) -> str:
        """
        ?ASCII 码列表转捸ַ?(Convert a list of ASCII codes to a string).

        Args:
            s (str): ASCII 码列?(List of ASCII codes).

        Returns:
            str: תַ?(Converted string).
        """
        return "".join([chr(i) for i in s])

    @staticmethod
    def to_char_array(s: str) -> List[int]:
        """
        将字符串ת?ASCII 码列?(Convert a string to a list of ASCII codes).

        Args:
            s (str): 输入ַ?(Input string).

        Returns:
            List[int]: ת ASCII 码列?(Converted list of ASCII codes).
        """
        return [ord(char) for char in s]

    @staticmethod
    def js_shift_right(val: int, n: int) -> int:
        """
        ʵ JavaScript е无号右移运?(Implement the unsigned right shift operation in JavaScript).

        Args:
            val (int): 输入?(Input value).
            n (int): 右移位数 (Number of bits to shift right).

        Returns:
            int: 右移?(Value after right shift).
        """
        return (val % 0x100000000) >> n

    @staticmethod
    def generate_random_bytes(length: int = 3) -> str:
        """
        生成组伪随机ַֽ串，用于混淆 (Generate a pseudo-random byte string to obfuscate the data).

        Args:
            length (int): 生成的字节序列长?(Length of the byte sequence to generate).

        Returns:
            str: 生成的伪随机ַֽ?(Generated pseudo-random byte string).
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
    CryptoUtility 类用于提供加密和的工具方法， SM3 哈希、添加盐值Base64 ?RC4 等?

    类属?
        salt (str): 盐?(Encryption salt).
        base64_alphabet (List[str]): 臮?Base64 ַ?(Custom Base64 alphabet).

    类方?
        sm3_to_array(input_data: Union[str, List[int]]) -> List[int]:
            计算体的 SM3 哈希值，并将ת为整数数组?

        add_salt(param: str) -> str:
            为字符串添加盐?

        process_param(param: Union[str, List[int]], add_salt: bool) -> Union[str, List[int]]:
            输入，根捜要添加盐值?

        params_to_array(param: Union[str, List[int]], add_salt: bool = True) -> List[int]:
            ȡ输入的哈希数组?

        transform_bytes(bytes_list: List[int]) -> str:
            ֽбм/ܲ，返回理后的字符串?

        base64_encode(input_string: str, selected_alphabet: int = 0) -> str:
            ʹ臮义字符表入字符串 Base64 ?

        abogus_encode(abogus_bytes_str: str, selected_alphabet: int) -> str:
            ַֽ串进行自定义 Base64 ，并添加位移和填充?

        rc4_encrypt(key: bytes, plaintext: str) -> bytes:
            ʹ RC4 算法?

    ʹ示例:
    ```python
        # 计算体的 SM3 哈希?
        sm3_hash = CryptoUtility.sm3_to_array("Hello, World!")
        print(sm3_hash)

        # 为字符串添加盐?
        salted_param = CryptoUtility.add_salt("Hello, World!")
        print(salted_param)

        # ȡ输入的哈希数?
        hash_array = CryptoUtility.params_to_array("Hello, World!")
        print(hash_array)

        # ֽбм/ܲ
        encrypted_str = CryptoUtility.transform_bytes([72, 101, 108, 108, 111, 44, 32, 87, 111, 114, 108, 100, 33])
        print(encrypted_str)

        # ʹ臮义字符表入字符串 Base64 
        base64_str = CryptoUtility.base64_encode("Hello, World!")
        print(base64_str)

        # ַֽ串进行自定义 Base64 ，并添加位移和填?
        abogus_str = CryptoUtility.abogus_encode("Hello, World!", 0)
        print(abogus_str)

        # ʹ RC4 算法
        key = b"key"
        plaintext = "Hello, World!"
        ciphertext = CryptoUtility.rc4_encrypt(key, plaintext)
        print(ciphertext)
    ```
    """

    def __init__(self, salt: str, custom_base64_alphabet: List[str]):
        """
        初?CryptoUtility ?
        Initialize the CryptoUtility class.

        Args:
            salt (str): 盐?(Encryption salt).
            custom_base64_alphabet (List[str]): 臮?Base64 ַ?(Custom Base64 alphabet).
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
        计算体的 SM3 哈希值，并将ת为整数数?(Calculate the SM3 hash value of the request body and convert the result to an array of integers).

        Args:
            input_data (Union[str, List[int]]): 输入 (Input data).

        Returns:
            List[int]: 哈希值的整数数组 (Array of integers representing the hash value).
        """
        # 输入昭符串，则将其为字节数?
        if isinstance(input_data, str):
            input_data_bytes = input_data.encode("utf-8")
        else:
            input_data_bytes = bytes(input_data)  # ?List[int] ת为字节数?

        # 将字节数组转捸适合 sm3.sm3_hash 函数的列表格?
        hex_result = sm3.sm3_hash(func.bytes_to_list(input_data_bytes))

        # 将十兿制字符串ת为十进制整数б
        return [int(hex_result[i : i + 2], 16) for i in range(0, len(hex_result), 2)]

    def add_salt(self, param: str) -> str:
        """
        为字符串添加盐?(Add salt to the string parameter).

        Args:
            param (str): 输入ַ?(Input string).

        Returns:
            str: 添加盐后的字符串 (String with added salt).
        """
        return param + self.salt

    def process_param(
        self, param: Union[str, List[int]], add_salt: bool
    ) -> Union[str, List[int]]:
        """
        输入，根捜要添加盐?(Process input parameter and add salt if needed).

        Args:
            param (Union[str, List[int]]): 输入 (Input parameter).
            add_salt (bool): 昐添加盐?(Whether to add salt).

        Returns:
            Union[str, List[int]]: Ĳ (Processed parameter).
        """
        if isinstance(param, str) and add_salt:
            param = self.add_salt(param)
        return param

    def params_to_array(
        self, param: Union[str, List[int]], add_salt: bool = True
    ) -> List[int]:
        """
        ȡ输入的哈希数?(Get the hash array of the input parameter).

        Args:
            param (Union[str, List[int]]): 输入 (Input parameter).
            add_salt (bool): 昐添加盐?(Whether to add salt).

        Returns:
            List[int]: 哈希数组 (Hash array).
        """
        processed_param = self.process_param(param, add_salt)
        return self.sm3_to_array(processed_param)

    def transform_bytes(self, bytes_list: List[int]) -> str:
        """
        ֽбм/ܲ，返回理后的字符串 (Encrypt/decrypt the input byte list and return the processed string).

        Args:
            bytes_list (List[int]): 输入的字节列?(Input byte list).

        Returns:
            str: ַ?(Processed string).
        """
        # 将字节列表转捸ַַ?
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

            # 交换数组元素
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
        ʹ臮义字符表入字符串 Base64  (Encode the input string using a custom Base64 alphabet).

        Args:
            input_string (str): 输入ַ?(Input string).
            selected_alphabet (int): ѡ的自定义 Base64 ַ表索?(Selected custom Base64 alphabet index).

        Returns:
            str: ַ?(Encoded string).
        """

        # 将输入字符串ת为ASCII码的二进制形?
        binary_string = "".join(["{:08b}".format(ord(char)) for char in input_string])

        # 补全二进制字符串使其长度?的数
        padding_length = (6 - len(binary_string) % 6) % 6
        binary_string += "0" * padding_length

        # 将二进制ַ串分割为6位一?
        base64_indices = [
            int(binary_string[i : i + 6], 2) for i in range(0, len(binary_string), 6)
        ]

        # 根据臮义字符表生成输出ַ?
        output_string = "".join(
            [self.base64_alphabet[selected_alphabet][index] for index in base64_indices]
        )

        # 添加等号塅，使 Base64 淶
        output_string += "=" * (padding_length // 2)

        return output_string

    def abogus_encode(self, abogus_bytes_str: str, selected_alphabet: int) -> str:
        """
        ַֽ串进行自定义 Base64 ，并添加位移和填?(Encode the input byte string using a custom Base64 alphabet, and add shifts and padding).

        Args:
            abogus_bytes_str (str): 输入的字节字符串 (Input byte string).
            selected_alphabet (int): ѡ的自定义 Base64 ַ表索?(Selected custom Base64 alphabet index).

        Returns:
            str: ַ?(Encoded string).
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
        ʹ RC4 算法 (Encrypt data using the RC4 algorithm).

        Args:
            key (bytes): 密钥 (Encryption key).
            plaintext (str): 明文 (Plaintext data).

        Returns:
            bytes: ܺ (Encrypted data).
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
    BrowserFingerprintGenerator 用于生成ģ的浏览器指纹Ϣ，用于在ͬ浏器环境中测试和数捇集?

    类属?
        browsers (Dict[str, Callable[[], str]]): 浏器类型和生成浏器指纹的映射关系?

    方法:
        generate_fingerprint(browser_type="Edge"):
            根据指定的浏览器生成浏器指纹?

        generate_chrome_fingerprint():
            生成 Chrome 浏器指纹?

        generate_firefox_fingerprint():
            生成 Firefox 浏器指纹?

        generate_safari_fingerprint():
            生成 Safari 浏器指纹?

        generate_edge_fingerprint():
            生成 Edge 浏器指纹?

        _generate_fingerprint(platform="Win32"):
            根据给定的参数生成浏览器指纹ַ串?

    ʹ示例:
    ```python
        chrome_fp = BrowserFingerprintGenerator.generate_fingerprint("Chrome")
        print(chrome_fp)
    ```
    """

    @classmethod
    def generate_fingerprint(cls, browser_type: str = "Edge") -> str:
        """
        根据指定的浏览器生成浏器指纹?(Generate a browser fingerprint based on the specified browser type.)

        Args:
            browser_type (str): 浏器类?(Browser type).

        Returns:
            str: 生成的浏览器指纹ַ?(Generated browser fingerprint string).
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
        根据给定的参数生成浏览器指纹ַ串?(Generate a browser fingerprint string based on the given parameters.)

        Args:
            platform (str): 系统平台 (Operating system platform).

        Returns:
            str: 生成的浏览器指纹ַ?(Generated browser fingerprint string).
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
    ABogus 类用于生?ABogus ?

    类属?
        array1 (List[int]): ?(Encrypted request body).
        array2 (List[int]): ?(Encrypted request header).
        array3 (List[int]):  UA (Encrypted User-Agent).
        ad (int): AID ?(AID value).
        pageId (int): 页面 ID (Page ID).
        salt (str): 盐?(Encryption salt).
        options (List[int]): 选项 (Request options).
        ua_key (bytes): UA 密钥 (UA encryption key).
        character (str): 臮?Base64 ַ?(Custom Base64 alphabet).
        character2 (str): 臮?Base64 ַ?(Custom Base64 alphabet).
        character_list (List[str]): 臮?Base64 ַ表列?(List of custom Base64 alphabets).
        crypto_utility (CryptoUtility): ܹ?(Encryption utility).
        user_agent (str): 臮?UA (Custom User-Agent).
        browser_fp (str): 浏器指?(Browser fingerprint).
        sort_index (List[int]): 排序索引 (Sort index).
        sort_index_2 (List[int]): 排序索引 (Sort index).

    ˵?
        options 用于指定的类型，GET ʹ [0, 1, 8]，POST ʹ [0, 1, 14]?4兼8，POST同样叻params，故写?
        (The options parameter is used to specify the type of request. GET requests use [0, 1, 8], and POST requests use [0, 1, 14]. 14 is compatible with 8, and POST can also encode params, so it is hardcoded.)

    方法:
        encode_data(data: str, alphabet_index: int = 0) -> str:
            ʹ指定的字符表对数捿?Base64  (Encode the data using the specified Base64 alphabet).

        generate_abogus(params: str, request: str = "") -> str:
            生成 ABogus  (Generate the ABogus parameter).

    ʹ示例:
    ```python
        # 生成 ABogus ，置空使用默?UA 和浏览器指纹
        abogus = ABogus(user_agent="xxx", fp="xxx")
        abogus_param = abogus.generate_abogus("device_platform=webapp&ad=6383&channel=channel_pc_web&aweme_d=7380308675841297704…省略?)
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
        self.salt = "cus"  # 1.0.1.19 -> ?# dhzx
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
        self.array1 = []  # ?
        self.array2 = []  # ?为空
        self.array3 = []  # UA
        self.options = options  # GET [0, 1, 8] POST [0, 1, 14]
        self.ua_key = b"\x00\x01\x0E"  # uakey

        self.character = (
            "Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe"
        )
        self.character2 = (
            "ckdp1h4ZKsUB80/Mfvw36XIgR25+WQAlEi7NLboqYTOPuzmFjJnryx9HVGDaStCe"
        )
        self.character_list = [self.character, self.character2]  # 臮义base64ַ?

        self.crypto_utility = CryptoUtility(
            self.salt, self.character_list
        )  # ܹ?

        self.user_agent = (
            user_agent
            if user_agent is not None and user_agent != ""
            else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0"
        )  # 臮义ua，为空则主a

        self.browser_fp = (
            fp
            if fp is not None and fp != ""
            else BrowserFingerprintGenerator.generate_fingerprint("Edge")
        )  # 臮义浏览器指纹，为空则生成Edge指纹

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
        ʹ指定的字符表对数捿?Base64  (Encode the data using the specified Base64 alphabet).

        Args:
            data (str): 输入 (Input data).
            alphabet_index (int): 臮义字符表索引 (Custom alphabet index).

        Returns:
            str:  (Encoded data).
        """
        return self.crypto_utility.abogus_encode(data, alphabet_index)

    def generate_abogus(self, params: str, body: str = "") -> tuple:
        """
        生成 abogus  (Generate the ABogus parameter).

        Args:
            params (str):  (Request parameters).
            body (str): 体，GET接口则为?(Request body, empty for GET interfaces).

        Returns:
            tuple: params 生成?abogus  ?ua (ABogus parameter generated by params and ua).
        """
        ab_dir = {
            8: 3,  # 固定
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
            66: 0,  # 固定
            69: 0,  # 固定
            70: 0,  # 固定
            71: 0,  # 固定
        }

        # 始加密时?
        start_encryption = int(time.time() * 1000)

        # params加盐
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

        # ʱ
        end_encryption = int(time.time() * 1000)

        # 始时?
        ab_dir[20] = (start_encryption >> 24) & 255
        ab_dir[21] = (start_encryption >> 16) & 255
        ab_dir[22] = (start_encryption >> 8) & 255
        ab_dir[23] = start_encryption & 255
        ab_dir[24] = int(start_encryption / 256 / 256 / 256 / 256) >> 0
        ab_dir[25] = int(start_encryption / 256 / 256 / 256 / 256 / 256) >> 0

        # 头配?
        ab_dir[26] = (self.options[0] >> 24) & 255
        ab_dir[27] = (self.options[0] >> 16) & 255
        ab_dir[28] = (self.options[0] >> 8) & 255
        ab_dir[29] = self.options[0] & 255

        # 方法
        ab_dir[30] = int(self.options[1] / 256) & 255
        ab_dir[31] = (self.options[1] % 256) & 255
        ab_dir[32] = (self.options[1] >> 24) & 255
        ab_dir[33] = (self.options[1] >> 16) & 255

        # 头加?
        ab_dir[34] = (self.options[2] >> 24) & 255
        ab_dir[35] = (self.options[2] >> 16) & 255
        ab_dir[36] = (self.options[2] >> 8) & 255
        ab_dir[37] = self.options[2] & 255

        # 体加?
        ab_dir[38] = array1[21]
        ab_dir[39] = array1[22]
        # body
        ab_dir[40] = array2[21]
        ab_dir[41] = array2[22]
        # ua
        ab_dir[42] = array3[23]
        ab_dir[43] = array3[24]

        # ܽʱ
        ab_dir[44] = (end_encryption >> 24) & 255
        ab_dir[45] = (end_encryption >> 16) & 255
        ab_dir[46] = (end_encryption >> 8) & 255
        ab_dir[47] = end_encryption & 255
        ab_dir[48] = ab_dir[8]
        ab_dir[49] = int(end_encryption / 256 / 256 / 256 / 256) >> 0
        ab_dir[50] = int(end_encryption / 256 / 256 / 256 / 256 / 256) >> 0

        # 固定?
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

        # 浏器指?
        ab_dir[64] = len(self.browser_fp)
        ab_dir[65] = len(self.browser_fp)

        # ȡ ab_dir ?sort_index 的?
        sorted_values = [ab_dir.get(i, 0) for i in self.sort_index]

        # 将浏览器指纹ת?ASCII 码列?
        edge_fp_array = StringProcessor.to_char_array(self.browser_fp)

        # 将浏览器指纹长度的低 8 位作为异或?
        ab_xor = (len(self.browser_fp) & 255) >> 8 & 255

        # 异或计算
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
    # 24/06/16 晚点源自定义ua
    # 24/07/08 ֧臮义ua和浏览器指纹
    # 24/11/15 1.0.1.19版本abogus算法，择日开?
    # 25/03/05 POSTܴ，修补环?

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

    # # 测试生成100个abogus ?100丌纹所ʱ
    # start = time.time()
    # for _ in range(100):
    #     abogus.generate_abogus(params=params, body=body)
    # end = time.time()
    # print("生成100个abogus和指纹所ʱ:", end - start)  # 生成100个abogus和指纹所ʱ: 2.203000783920288

    # start = time.time()
    # for _ in range(100):
    #     BrowserFingerprintGenerator.generate_fingerprint("Chrome")
    # end = time.time()
    # print("生成100丌纹所ʱ:", end - start)  # 生成100丌纹所ʱ: 0.00400090217590332
