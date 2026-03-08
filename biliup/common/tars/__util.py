#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Tencent is pleased to support the open source community by making Tars available.
#
# Copyright (C) 2016THL A29 Limited, a Tencent company. All rights reserved.
#
# Licensed under the BSD 3-Clause License (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# https://opensource.org/licenses/BSD-3-Clause
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#


import hashlib
import sys
from threading import Lock
from xml.etree import cElementTree as ET

from .exception import TarsException


class util:
    @staticmethod
    def printHex(buff):
        count = 0
        for c in buff:
            sys.stdout.write("0X%02X " % ord(c))
            count += 1
            if count % 16 == 0:
                sys.stdout.write("\n")
        sys.stdout.write("\n")
        sys.stdout.flush()

    @staticmethod
    def mapclass(ktype, vtype):
        class mapklass(dict):
            def size(self): return len(self)
        setattr(mapklass, '__tars_index__', 8)
        setattr(mapklass, '__tars_class__', "map<" +
                ktype.__tars_class__ + "," + vtype.__tars_class__ + ">")
        setattr(mapklass, 'ktype', ktype)
        setattr(mapklass, 'vtype', vtype)
        return mapklass

    @staticmethod
    def vectorclass(vtype):
        class klass(list):
            def size(self): return len(self)
        setattr(klass, '__tars_index__', 9)
        setattr(klass, '__tars_class__', "list<" + vtype.__tars_class__ + ">")
        setattr(klass, 'vtype', vtype)
        return klass

    class boolean:
        __tars_index__ = 999
        __tars_class__ = "bool"

    class int8:
        __tars_index__ = 0
        __tars_class__ = "char"

    class uint8:
        __tars_index__ = 1
        __tars_class__ = "short"

    class int16:
        __tars_index__ = 1
        __tars_class__ = "short"

    class uint16:
        __tars_index__ = 2
        __tars_class__ = "int32"

    class int32:
        __tars_index__ = 2
        __tars_class__ = "int32"

    class uint32:
        __tars_index__ = 3
        __tars_class__ = "int64"

    class int64:
        __tars_index__ = 3
        __tars_class__ = "int64"

    class float:
        __tars_index__ = 4
        __tars_class__ = "float"

    class double:
        __tars_index__ = 5
        __tars_class__ = "double"

    class bytes:
        __tars_index__ = 13
        __tars_class__ = "list<char>"

    class string:
        __tars_index__ = 67
        __tars_class__ = "string"

    class struct:
        __tars_index__ = 1011


def xml2dict(node, dic={}):
    '''
    @brief: 灏唜ml解析鏍戣浆鎴愬瓧鍏?
    @param node: 鏍戠殑鏍硅妭鐐?
    @type node: cElementTree.Element
    @param dic: 存储信息鐨勫瓧鍏?
    @type dic: dict
    @return: 转换濂界殑瀛楀吀
    @rtype: dict
    '''
    dic[node.tag] = ndic = {}
    [xml2dict(child, ndic) for child in node.getchildren() if child != node]
    ndic.update([list(map(str.strip, exp.split('=')[:2]))
                 for exp in node.text.splitlines() if '=' in exp])
    return dic


def configParse(filename):
    '''
    @brief: 解析tars配置文件
    @param filename: 文件鍚?
    @type filename: str
    @return: 解析出来鐨勯厤缃俊鎭?
    @rtype: dict
    '''
    tree = ET.parse(filename)
    return xml2dict(tree.getroot())


class NewLock(object):
    def __init__(self):
        self.__count = 0
        self.__lock = Lock()
        self.__lockForCount = Lock()
        pass

    def newAcquire(self):
        self.__lockForCount.acquire()
        self.__count += 1
        if self.__count == 1:
            self.__lock.acquire()
        self.__lockForCount.release()
        pass

    def newRelease(self):
        self.__lockForCount.acquire()
        self.__count -= 1
        if self.__count == 0:
            self.__lock.release()
        self.__lockForCount.release()


class LockGuard(object):
    def __init__(self, newLock):
        self.__newLock = newLock
        self.__newLock.newAcquire()

    def __del__(self):
        self.__newLock.newRelease()


class ConsistentHashNew(object):
    def __init__(self, nodes=None, nodeNumber=3):
        """
        :param nodes:           服务器的节点的pstr列表
        :param n_number:        涓€涓妭鐐瑰搴旂殑铏氭嫙节点数量
        :return:
        """
        self.__nodes = nodes
        self.__nodeNumber = nodeNumber  # 姣忎竴涓妭鐐瑰搴斿灏戜釜铏氭嫙节点锛岃繖閲岄粯璁ゆ槸3涓?
        self.__nodeDict = dict()  # 鐢ㄤ簬璁板綍铏氭嫙节点鐨刪ash鍊间笌服务鍣╡pstr鐨勫搴斿叧绯?
        self.__sortListForKey = []  # 鐢ㄤ簬瀛樻斁鎵€鏈夌殑铏氭嫙节点鐨刪ash鍊硷紝杩欓噷闇€瑕佷繚鎸佹帓搴忥紝浠ユ壘鍑哄搴旂殑服务鍣?
        if nodes:
            for node in nodes:
                self.addNode(node)

    @property
    def nodes(self):
        return self.__nodes

    @nodes.setter
    def nodes(self, value):
        self.__nodes = value

    def addNode(self, node):
        """
        娣诲姞node锛岄鍏堣鏍规嵁铏氭嫙节点鐨勬暟鐩紝创建鎵€鏈夌殑铏氭嫙节点锛屽苟灏嗗叾涓庡搴旂殑node瀵瑰簲璧锋潵
        褰撶劧杩橀渶瑕佸皢铏氭嫙节点鐨刪ash鍊兼斁鍒版帓搴忕殑閲岄潰
        杩欓噷鍦ㄦ坊鍔犱簡节点涔嬪悗锛岄渶瑕佷繚鎸佽櫄鎷熻妭鐐筯ash鍊肩殑椤哄簭
        :param node:
        :return:
        """
        for i in range(self.__nodeNumber):
            nodeStr = "%s%s" % (node, i)
            key = self.__genKey(nodeStr)
            self.__nodeDict[key] = node
            self.__sortListForKey.append(key)
        self.__sortListForKey.sort()

    def removeNode(self, node):
        """
        杩欓噷涓€涓妭鐐圭殑閫€鍑猴紝闇€瑕佸皢杩欎釜节点鐨勬墍鏈夌殑铏氭嫙节点閮藉垹闄?
        :param node:
        :return:
        """
        for i in range(self.__nodeNumber):
            nodeStr = "%s%s" % (node, i)
            key = self.__genKey(nodeStr)
            del self.__nodeDict[key]
            self.__sortListForKey.remove(key)

    def getNode(self, key):
        """
        返回杩欎釜字符涓插簲璇ュ搴旂殑node锛岃繖閲屽厛姹傚嚭字符涓茬殑hash鍊硷紝鐒跺悗鎵惧埌绗竴涓皬浜庣瓑浜庣殑铏氭嫙节点锛岀劧鍚庤繑鍥瀗ode
        如果hash鍊煎ぇ浜庢墍鏈夌殑节点锛岄偅涔堢敤绗竴涓櫄鎷熻妭鐐?
        :param : hashNum or keyStr
        :return:
        """
        keyStr = ''
        if isinstance(key, int):
            keyStr = "the keyStr is %d" % key
        elif isinstance(key, type('a')):
            keyStr = key
        else:
            raise TarsException("the hash code has wrong type")
        if self.__sortListForKey:
            key = self.__genKey(keyStr)
            for keyItem in self.__sortListForKey:
                if key <= keyItem:
                    return self.__nodeDict[keyItem]
            return self.__nodeDict[self.__sortListForKey[0]]
        else:
            return None

    def __genKey(self, keyStr):
        """
        閫氳繃key锛岃繑鍥炲綋鍓峩ey鐨刪ash鍊硷紝杩欓噷閲囩敤md5
        :param key:
        :return:
        """
        md5Str = hashlib.md5(keyStr).hexdigest()
        return int(md5Str, 16)
