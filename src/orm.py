"""
orm.py是本项目的ORM框架，通过Python对象直接操作数据库
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio, logging

import aiomysql

def log(sql, args = ()):
    logging.info('SQL: %s' % sql)

# 通过aiomysql的create_pool函数可以创建一个数据库连接池，保持一定数量的连接
# 防止对数据库频繁地创建连接。
# minsize和maxsize分别表示连接池连接对象的上下限
@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = yield from aiomysql.create_pool(
        host = kw.get('host', 'localhost'),
        port = kw.get('port', 3306),
        user = kw['user'],
        password = kw['password'],
        db = kw['db'], # 要连接的数据库名
        charset = kw.get('charset', 'utf8'),
        autocommit = kw.get('autocommit', True) #True为default值
        maxsize = kw.get('maxsize', 10),
        minsize = kw.get('minsize', 1),
        loop = loop
    )


@asyncio.coroutine
def select(sql, args, size = None):
    log(sql, args)
    global __pool
    with (yield from __pool) as conn:
        #DictCursor:A cursor which returns results as a dictionary
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        # SQL语句的占位符是？，而MYSQL的占位符是%s，select函数在内部自动替换
        # 始终坚持使用带参数的SQL，而不是自己拼接字符串，可以放置SQL注入攻击
        # args中则是真正要填入的数据
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info("rows returned: %s" % len(rs))
        return rs

@asyncio.coroutine
def execute(sql, args, autocommit = True) -> int:
    log(sql)
    with (yield from __pool) as conn:
        if not autocommit:
            # a coroutine to begin transaction
            yield from conn.begin()
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount # 受到影响的行数
            yield from cur.close()
            if not autocommit:
                yield from conn.commit()
        except BaseException as e:
            if not autocommit:
                # Roll back to the current transaction coroutine
                yield from conn.rollback()
            raise
        return affected

def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)

class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):

    def __init__(self, name = None, primary_key = False, default = None, ddl = 'varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name = None, default = None):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name = None, primary_key = False,default = 0):
        super().__init__(name, 'bigint', primary_key, default)

class TextField(Field):

    def __init__(self, name = None, default = None):
        super().__init__(name, 'text', False, default)


# 这个继承了type的ModelMetaclass就非常麻烦了。
# 参考这个：http://c.biancheng.net/view/2293.html
# 通过metaclass将具体的子类的映射信息读取出来
# 参考了那个metaclass的教程就知道，所以继承了Model类的子类包括Model类自己在
# 实例化时都会执行一边ModelMetaClass中的__new__方法。
# 而在这个方法中，可以自动扫描映射关系，并存储到自身的类属性中
class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        # cls代表动态修改的类
        # name代表动态修改的类名
        # bases代表动态修改的类的所有父类
        # attrs代表被动态修改的类的所有属性、方法组成的字典
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        # 在变量赋值时用or，与条件判断中相同
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict()
        fields = []
        primaryKey = None
        for k,v in attrs.items():
            if isinstance(v, Field):
                logging.info('    found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    #找到主键
                    if primaryKey:
                        raise StandardError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise StandardError('primaryKey not found')
        for k in mappings.keys():
            attr.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        # map函数可以根据提供的函数对指定序列做映射
        attrs['__mappings__'] = mappings
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey
        attrs['__fields__'] = fields
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ','.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ','.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

# Model是所有ORM映射的基类
# 由于Model继承了dict类，所以可以像字典那样去调用属性的值。
class Model(dict, metaclass = ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, field.default))
                setattr(self, key, value)
        return value

    #classmethod修饰符对应的函数不需要实例化，不需要self参数，第一个参数是
    #表示自身类的cls参数，可以用来调用类的属性、方法、实例化对象等等。
    @classmethod
    @asyncio.coroutine
    def findAll(cls, where = None, args = None, **kw):
        #' find objects by where clause.'
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = yield from select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    @asyncio.coroutine
    def findNumber(cls, selectField, where = None, args = None):
        #find number by select and where.
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = yield from select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    @asyncio.coroutine
    def find(cls, pk):
        # find object by primary key, pk for primary key
        res = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warn("failed to insert record: affected rows: %s" % rows)

    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warn("failed to update by primary_key: affetcted rows: %s" % rows)

    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__, args)
        if rows != 1:
            logging.warn("failed to delete by primary_key: affected rows: %s" % rows)






