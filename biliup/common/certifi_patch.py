"""
Certifi 证书路径补丁 - 用于 PyInstaller/Nuitka 编译后的 EXE

编译后，certifi 模块无法自动找到证书文件，
此模块在导入时自动设置 SSL_CERT_FILE 环境变量指向打包的证书文件。

注意：此补丁必须在导入任何使用 SSL 的库（如 httpx、requests）之前导入
"""
import os
import sys


def _get_certifi_cert_path():
    """获取打包的 certifi 证书文件路径"""
    # 打包后的路径处理
    if hasattr(sys, 'frozen'):
        # PyInstaller 模式
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
            # 尝试多种可能的路径
            possible_paths = [
                os.path.join(base_path, 'certifi', 'cacert.pem'),
                os.path.join(base_path, 'cacert.pem'),
            ]
            for cert_path in possible_paths:
                if os.path.exists(cert_path):
                    return cert_path
        else:
            # Nuitka standalone - 可执行文件所在目录
            base_path = os.path.dirname(sys.executable)
            possible_paths = [
                os.path.join(base_path, 'certifi', 'cacert.pem'),
                os.path.join(base_path, 'cacert.pem'),
                os.path.join(os.path.dirname(base_path), 'certifi', 'cacert.pem'),
            ]
            for cert_path in possible_paths:
                if os.path.exists(cert_path):
                    return cert_path

    # 开发环境 - 使用正常的 certifi
    try:
        import certifi
        return certifi.where()
    except ImportError:
        pass

    return None


def patch_certifi():
    """设置 SSL_CERT_FILE 环境变量指向正确的证书文件"""
    cert_path = _get_certifi_cert_path()
    if cert_path and os.path.exists(cert_path):
        os.environ['SSL_CERT_FILE'] = cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
        return True
    return False


# 导入时自动执行补丁
patch_certifi()
