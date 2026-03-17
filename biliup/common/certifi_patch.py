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
    if hasattr(sys, 'frozen'):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
            possible_paths = [
                os.path.join(base_path, 'certifi', 'cacert.pem'),
                os.path.join(base_path, 'cacert.pem'),
            ]
            for cert_path in possible_paths:
                if os.path.exists(cert_path):
                    return cert_path
        else:
            base_path = os.path.dirname(sys.executable)
            possible_paths = [
                os.path.join(base_path, 'certifi', 'cacert.pem'),
                os.path.join(base_path, 'cacert.pem'),
                os.path.join(os.path.dirname(base_path), 'certifi', 'cacert.pem'),
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


def _create_certifi_stub():
    """创建 certifi 模块的 stub，避免导入错误"""
    if not hasattr(sys, 'frozen'):
        return

    import types

    certifi_stub = types.ModuleType('certifi')
    certifi_stub.__file__ = '<certifi_stub>'

    def where():
        return _get_certifi_cert_path() or ''

    def contents():
        cert_path = where()
        if cert_path and os.path.exists(cert_path):
            with open(cert_path, 'r', encoding='ascii') as f:
                return f.read()
        return ''

    certifi_stub.where = where
    certifi_stub.contents = contents

    sys.modules['certifi'] = certifi_stub

    core_stub = types.ModuleType('certifi.core')
    core_stub.where = where
    core_stub.contents = contents
    sys.modules['certifi.core'] = certifi_stub


def patch_certifi():
    """设置 SSL_CERT_FILE 环境变量指向正确的证书文件"""
    cert_path = _get_certifi_cert_path()
    if cert_path and os.path.exists(cert_path):
        os.environ['SSL_CERT_FILE'] = cert_path
        os.environ['REQUESTS_CA_BUNDLE'] = cert_path
        return True
    return False


if hasattr(sys, 'frozen'):
    _create_certifi_stub()

patch_certifi()
