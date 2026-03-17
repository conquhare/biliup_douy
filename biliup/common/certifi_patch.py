"""
Certifi 证书路径补丁 - 用于 PyInstaller/Nuitka 编译后的 EXE

编译后，certifi 模块无法自动找到证书文件，
此模块在导入时自动设置 SSL_CERT_FILE 环境变量指向打包的证书文件。

注意：此补丁必须在导入任何使用 SSL 的库（如 httpx、requests）之前导入
"""
import os
import sys


def _is_nuitka_standalone():
    """检测是否在 Nuitka standalone 打包环境下运行"""
    if hasattr(sys, 'frozen'):
        return True
    if hasattr(sys, '_MEIPASS'):
        return True
    if "__compiled__" in globals():
        return True
    executable = sys.executable.lower() if sys.executable else ''
    if executable and not executable.endswith('python.exe') and not executable.endswith('pythonw.exe') and not executable.endswith('python3.exe'):
        if os.path.isfile(sys.executable):
            return True
    if 'certifi' in sys.modules and hasattr(sys.modules['certifi'], '__file__'):
        if sys.modules['certifi'].__file__ == '<certifi_stub>':
            return True
    return False


def _get_certifi_cert_path():
    """获取打包的 certifi 证书文件路径"""
    if _is_nuitka_standalone():
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(sys.executable)
        
        possible_paths = [
            os.path.join(base_path, 'certifi', 'cacert.pem'),
            os.path.join(base_path, 'cacert.pem'),
        ]
        for cert_path in possible_paths:
            if os.path.exists(cert_path):
                return cert_path
        return None

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


patch_certifi()
