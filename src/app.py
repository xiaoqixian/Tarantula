# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# > Author     : lunar
# > Email       : lunar_ubuntu@qq.com
# > Create Time: Wed 22 Jul 2020 04:50:29 PM CST

import logging; logging.basicConfig(format = "%(levelname)-8s [%(filename)s: %(lineno)d] %(message)s")

import orm
import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from config import configs

from web_frame import add_routes, add_static

from handlers import cookie2user, COOKIE_NAME

# jinja2是一个用于渲染模板的库。
def init_jinja2(app, **kw):
    logging.info("init jinja2")
    options = dict(
        autoescape = kw.get('autoescape', True),
        block_start_string = kw.get('block_start_string', '{%'),
        block_end_string = kw.get('block_end_string', '%}'),
        variable_start_string = kw.get('variable_start_string', '{{'),
        variable_end_string = kw.get('variable_end_string', '}}'),
        auto_reload = kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info("set jinja2 template path: %s" % path)
    env = Environment(loader = FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env


# 定义三个中间件，将中间件添加到app里面以后。当请求到来时，app会将请求同时传
# 给三个中间价并进行调用。中间件都是装饰器

# logger中间件，负责打印一些日志
async def logger_factory(app, handler):
    async def logger(request):
        logging.info("Request: %s %s" % (request.method, request.path))
        return await handler(request)
    return logger

# 身份检验中间件
async def auth_factory(app, handler):
    async def auth(request):
        logging.info("check user: %s, %s" % (request.method, request.path))
        request.__user__ = None
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = await cookie2user(cookie_str)
            if user:
                logging.info("set current user: %s " % user.email)
                request.__user__ = user
        # 当进入管理页面时需要验证管理员权限
        if request.path.startswith('/manage/'):
            if not request.__user__ or not request.__user__.admin:
                # web.HTTPFound(path)具有重定向的功能
                return web.HTTPFound('/signin')
        return await handler(request)
    return auth

# 消息回复中间件
async def response_factory(app, handler):
    async def response(request):
        logging.info("Response handler")
        res = await handler(request)
        if isinstance(res, web.StreamResponse):
            logging.info("web.StreamResponse")
            return res
        if isinstance(res, bytes):
            resp = web.Response(body = res)
            # application/octet-stream是常见二进制文件如：.bin,.exe,.class文件的Mime类型
            # 更多类型可以见：https://www.cnblogs.com/xiaohi/p/6550133.html
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(res, str):
            logging.info("str")
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body = res.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(res, dict):
            # 在handler函数中将会返回一个字典，第一个键值对就是'__template__': 'template name'
            template = res.get('__template__') # template的文件名
            if not template:
                # 找不到模板的话就直接将结果通过字符串返回，不用渲染
                # json.dumps可以将字典转化为字符串
                resp = web.Response(body = json.dumps(res, ensure_ascii=False, default = lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                res['__user__'] = request.__user__
                resp = web.Response(body = app['__templating__'].get_template(template).reader(**res).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        # default:
        logging.info("response default")
        resp = web.Response(body = str(res).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


# 定义一个过滤器将浮点数形式的时间转化为多久前形式的时间
def datetime_filter(t: float):
    delta = int(time.time() - t) # delta的单位是秒
    if delta < 60:
        return u"1分钟前" # 字符串前面带u表示使用utf-8编码，因为这里带有中文
    if delta < 3600:
        return u"%d分钟前" % (delta//60)
    if delta < 86400: # 一天之内
        return u"%d小时前" % (delta//3600)
    if delta < 604800: # 一周之内
        return u"%d天前" % (delta//86400)
    dt = datetime.fromtimestamp(t)
    return u"%s年%s月%s日" % (dt.year, dt.month, dt.day)

# 定义本项目的程序入口
async def init(loop):
    await orm.create_pool(loop = loop, **configs['db'])
    # 创建web应用
    app = web.Application(loop = loop, middlewares = [
        logger_factory, auth_factory, response_factory
    ])
    init_jinja2(app, filters = dict(datetime = datetime_filter))
    add_routes(app, 'handlers') # 这里决定了存放请求处理函数的文件只能叫handlers.py，并且必须放在同文件夹
    add_static(app)
    srv = await loop.create_server(app.make_handler(), configs['server']['publichost'], configs['server']['port'])
    logging.info('server started at http://%s:%d' % (configs['server']['publichost'], configs['server']['port']))
    return srv

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init(loop))
    loop.run_forever()
