# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# > Author     : lunar
# > Email       : lunar_ubuntu@qq.com
# > Create Time: Tue 21 Jul 2020 11:10:11 PM CST

# 接下来需要实现一个web框架，

# inspect库可以用于查看函数的属性
# functools库用于在制作装饰器时保存函数的元数据
import asyncio, inspect, functools, os
import aiohttp as web
from apis import APIError
from urllib import parse
import logging; logging.basicConfig(format = "%(levelname)-8s[%(filename)s:%(linemo)d] %(message)s", level = logging.INFO)

# 首先实现两个装饰器:get和post
# 这两个装饰器用于为函数装饰一点__method__和__route__的属性
# 由于是带参数的装饰器，所以需要定义三层函数
def get(path):
    # define a decorator @get('/path')
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

# 这两个装饰器在所有的handler中几乎都要用到


# inspect.signature函数，可以接收一个函数参数，返回一个具有函数信息的inspect.signature类。这个类具有一个parameters属性，其中就是函数
# 的参数信息。最主要的就是参数的默认值和参数的位置。
# 所谓位置，即参数到底是可以只传值还是必须要带上参数名。Python规定所有只传值的参数必须放在带参数名的参数前面。所以参数分为：
# POSITIONAL_OR_KEYWORD:位于最前面的一些参数，可以只传值也可以带上参数名传值
# KEYWORD_ONLY:必须要带上参数名，通常是位于可选参数后面。因为Python不允许将带有默认值的参数放在无默认值的参数前面
# VAR_POSITIONAL:只传值的可选参数，Python会将这些参数收集在一个列表里面
# VAR_KEYWORD:传参数名和值的可选参数，Python会将这些参数收集在一个字典里面

# 为此写出一系列判断handler传参要求的函数

# 获得所有必须传入的参数名字,没有默认值的键值传入的参数
def get_required_args(func) -> tuple:
    sig = inspect.signature(func).parameters
    res = []
    for k, v in sig.items():
        if v.kind == inspect.Parameter.KEYWORD_ONLY and v.default == inspect.Parameter.empty:
            res.append(k)
    return tuple(res)

# 得到所有键值传入的参数
def get_kw_args(func) -> tuple:
    sig = inspect.signature(func).parameters
    res = []
    for k, v in sig.items():
        if v.kind == inspect.Parameter.KEYWORD_ONLY:
            res.append(k)
    return tuple(res)

# 是否具有**kw参数
def has_var_kw_args(func) -> bool:
    params = inspect.signature(func).parameters
    for k,v in params.items():
        if v.kind == inspect.Parameter.VAR_KEYWORD:
            return True

# 是否具有名为request的参数,要求request参数之后没有POSITIONAL_OR_KEYWORD的参数
def has_request_args(func):
    params = inspect.signature(func).parameters
    res = False
    for k, v in params.items():
        if k == 'request':
            res = True
            continue
        if res and (v.kind != inspect.Parameter.VAR_POSITIONAL and v.kind != inspect.Parameter.VAR_KEYWORD and v.kind != inspect.Parameter.KEYWORD_ONLY):
            raise ValueError('request Parameter must be the last named parameter in function: %s%s' % (func.__name__, str(params)))
    return res


# python http request介绍
# request属性：
# 1. path:表示提交请求页面完整地址的字符串，不包括域名，如"/music/bands/the_beatles/"。
# 2. method:表示提交请求使用的HTTP方法。(GET、POST)
# 3. GET:一个类字典对象，包含所有的HTTP的GET参数的信息。
# 4. POST:一个类字典对象，包含所有的HTTP的POST参数的信息。注意： POST 并不 包含文件上传信息。
# 5. REQUEST:为了方便而创建，这是一个类字典对象，先搜索 POST ，再搜索 GET 。强烈建议使用 GET 和 POST，而不是 REQUEST 。
# 6. COOKIES:一个标准的Python字典，包含所有cookie。键和值都是字符串。
# 7. FILES:一个类字典对象，包含所有上传的文件。 FILES 的键来自 <input type="file" name="" /> 中的 name。 FILES 的值是一个标准的Python字典，包含以下三个键： filename ：字符串，表示上传文件的文件名。content-type ：上传文件的内容类型。content ：上传文件的原始内容。注意 FILES 只在请求的方法是 POST，并且提交的 <form> 包含enctype="multipart/form-data"时才包含数据。否则， FILES 只是一个空的类字典对象。

# 封装一个请求处理类，但是只有一个__init__和__call__方法
# 众所周知，__call__可以使得类实例像函数一样调用。所以这实际就是好用一点的
# 函数而已。


class RequestHandler:

    def __init__(self, app, func):
        self.app = app
        self.func = func
        self.required_kw_args = get_required_args(func)
        self.has_var_kw_args = has_var_kw_args(func)
        self.named_kw_args = get_kw_args(func)
        if len(self.named_kw_args) == 0:
            self.has_named_kw_args = False
        else:
            self.has_named_kw_args = True
        self.has_request_args = has_request_args(func)

    async def __call__(self,request):
        # 接下来考虑一个request应该如何处理
        # 首先考虑post请求，post请求主要有四种形式：
        # application/x-www-form-urlencoded:浏览器的原声form表单，最常见的一种。
        # multipart/form-data:在使用表单上传文件时，必须让form的enctyped等于这个值。
        # application/json:这种格式的表单，其消息主体是序列化的json字符串。
        # text/xml
        kw = None
        # 接收所有键值传入的参数
        if self.has_var_kw_args or self.has_named_kw_args or self.required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing Content-Type')
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = await request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('json body must be dictionary')
                    logging.info("application/json: %s" % params)
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % (request.content_type))
            if request.method == 'GET':
                qs = request.query_string
                logging.info("query_string of GET method: %s" % qs)
                if qs:
                    kw = dict()
                    for k,v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if not kw:
            kw = dict(**request.match_info)
            logging.info("request.match_info: %s" % str(kw))
        else:
            # 如果没有**kw参数，并且有KEYWORD_ONLY的参数
            if not self.has_var_kw_args and self.named_kw_args:
                copy = dict()
                for name in self.named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warn("Duplicate arg name in named arg and kw args: %s" % k)
                kw[k] = v
        if self.has_request_args:
            for name in self.required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest("missing argument: %s" % name)
        logging.info("call with args: %s" % str(kw))
        try:
            res = await self.func(**kw)
            return res
        except APIError as e:
            return dict(error = e.error, data = e.data, message = e.message)


# 为APP添加静态文件路径
def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

# 添加路径函数
def add_route(app, handler):
    method = getattr(handler, '__method__', None)
    path = getattr(handler, '__route__', None)
    if not path or not method:
        raise ValueError("@get or @post not defined in %s" % str(handler))
    if not asyncio.iscoroutinefunction(handler) and not inspect.isgeneratorfunction(handler):
        handler = asyncio.coroutine(handler)
    logging.info("add route %s => %s(%s)" % (path, handler.__name__, ', '.join(inspect.signature(handler).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, handler))

# 从其它文件导入handler并添加到app中
def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        # __import__可以用于动态导入模块，不需要在头部就导入
        module = __import__(module_name, globals(), locals())
    else:
        # 只导入文件中某个模块
        name = module_name[n+1:]
        module = getattr(__import__(module_name[:n], globals(), locals(),[name]), name)
    # dir()函数可以返回一个模块所有属性的列表
    for attr_name in dir(module):
        if attr_name.startswith('_'):
            # 不要私有模块
            continue
        attr = getattr(module, attr_name)
        # 只要函数
        if callable(attr):
            method = getattr(attr, '__method__', None)
            route = getattr(attr, '__route__', None)
            if method and route:
                logging.info("add route: %s " % (route))
                add_route(app, attr)

