# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# > Author     : lunar
# > Email       : lunar_ubuntu@qq.com
# > Create Time: Tue 21 Jul 2020 03:17:12 PM CST

# 首先编写一个ORM框架，利用Python对象进行数据库的增删改查。
# 项目用数据库tara中有三个表：users,blogs,comments。相信看名字就知道是用来放什么的。
# 所以相应就要准备三个类，一个类对应一个表，一个类属性对应一列，类方法对应相应的数据库行为。

# 一开始我是这么想的，但是发现每个表进行的增删改查的方法其实都大同小异。所以还是将这些方法作为一个
# 函数写出来。这些函数均接受一个sql语句参数，sql语句进行匹配的参数

import aiomysql

import logging; logging.basicConfig(format = "%(levelname)-8s [%(filename)s:%(lineno)d] %(message)s", level = logging.INFO)

# 创建连接池函数,kw用于存放关于连接数据库的配置参数
async def create_pool(loop, **kw):
    logging.info("create connection pool")
    global __pool
    __pool = await aiomysql.create_pool (
        host = kw.get('host', 'localhost'),
        port = kw.get('port', 3306),
        user = kw['user'],
        password = kw['password'],
        db = kw['db'],
        charset = kw.get('charset', 'utf8'),
        autocommit = kw.get('autocommit', True),
        maxsize = kw.get('maxsize', 10),
        minsize = kw.get('minsize', 5),
        loop = loop
    )

def log_sql(sql):
    logging.info("SQL: %s" % sql)

async def select(sql, args, size = None):
    log_sql(sql)
    global __pool
    with await __pool as conn:
        cur = await conn.cursor(aiomysql.DictCursor)
        # 要将SQL语句中的?换成%s，因为aiomysql使用%s作为占位符
        await conn.execute(sql.replace('?', '%s'), args or ())
        if size:
            res = await cur.fetchmany(size)
        else:
            res = await cur.fetchAll()
        await conn.close()
        logging.info("rows affected: %d", size)
        return res

# 一个execute函数可以适配insert、update、delete三种动作，分别为
# 'insert into table (?,?,?,?) values (?,?,?,?)'
# 'delete from table where `%s`=?'
# 'update table set () where `%s`=?'
async def execute(sql, args, autocommit = True):
    log_sql(sql)
    global __pool
    with await __pool as conn:
        if not autocommit:
            await conn.begin()
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace("?", "%s"), args)
            affected = cur.rowcount
            await cur.close()
            if not autocommit:
                await conn.commit()
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected


# 接下来就是创建field了，每个field对应表中的一列，每一列有名字、数据类型、是否是主键以及默认值是多少
# Field是所有field的父类
class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    # 创建一个方便打印的__str__方法
    def __str__(self):
        return "<%s, %s: %s>" % (self.__class__.__name__, self.column_type, self.name)

# 再看看本项目数据表需要用到的数据类型：varchar、int、text、double、bool
# 所以分别创建以下子类
class StringField(Field):

    def __init__(self, name = None, column_type = "varchar(50)", primary_key = False, default = None):
        super().__init__(name, column_type, primary_key, default)

class BoolField(Field):

    def __init__(self, name = None, default = False):
        super().__init__(name, "boolean", False, default)

class IntegerField(Field):

    def __init__(self, name = None, primary_key = False, default = None):
        super().__init__(name, "bigint", primary_key, default)

class TextField(Field):

    def __init__(self, name = None, default = None):
        super().__init__(name, "text", False, default)

class FloatField(Field):

    def __init__(self, name = None, primary_key = False, default = None):
        super().__init__(name, "real", primary_key, default)


