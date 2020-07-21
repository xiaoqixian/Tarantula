# !/usr/bin/env python3
# -*- coding: utf-8 -*-
# > Author     : lunar
# > Email       : lunar_ubuntu@qq.com
# > Create Time: Tue 21 Jul 2020 05:58:38 PM CST

from orm import StringField, IntegerField, TextField, BoolField, FloatField
import logging; logging.basicConfig(format = "%(levelname)-8s[%(filename)s:%(lineno)d] %(message)s", level = logging.INFO)
import time, uuid

# models.py负责将数据库表转化为Python类，从而用Python代码就可以实现数据库操作

# 定义一个创建num个占位符字符串的函数
def create_args_string(num):
    l = ['?' for i in range(num)]
    return ', '.join(l)


# 元类metaclass的__new__方法可以对所有继承了该元类的类在实例化之前对类进行一些操作
# 规定元类必须显式地继承type类，以及必须返回一个type的__new__方法构造的一个东西
# 更具体的东西还得看Python源码
class ModelMetaClass(type):

    # __new__方法接收四个参数
    # cls:继承元类的类
    # name:继承元类的类名
    # bases:该类所有的父类
    # attrs:该类的所有属性和方法，不包括init方法里定义的，因为init方法还没有执行。也
    # 不包括父类中继承的方法和属性
    def __new__(cls, name, bases, attrs):
        if name == "Model": # 显然无意义的这个父类不需要做任何处理
            return type.__new__(cls, name, bases, attrs)
        table_name = attrs.get('__table__', None)
        logging.info('found model: %s , table: %s' % (name, table_name))

        # 接下来的任务就是找到所有的属性，由于具体操作的函数都在父类Model中被定义，所以
        # 这里就只有数据表中实际含有的字段。同时还要在这些字段中找到主键
        fields = []
        mappings = {}
        primary_key = None
        for k,v in attrs.items():
            if isinstance(v, Field):
                mappings[k] = v
                logging.info("found mapping: %s => %s" % (k,v)) # 因为Field中定义了__str__方法， 可以当做字符串输出
                if v.primary_key:
                    if primary_key:
                        raise StandardError("duplicate primary_key: (%s, %s)" % (k, primary_key))
                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise StandardError("primary_key not found")
        for k in mappings.keys():
            attrs.pop(k) # 将所有Field属性从attributes中去除
        non_primary_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings
        attrs['__table__'] = table_name
        attrs['__primary_key__'] = primary_key
        attrs['__fields__'] = non_primary_fields
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primary_key, ', '.join(non_primary_fields), table_name)
        attrs['__insert__'] = 'insert into `%s` (`%s`, %s) values (%s)' % (table_name, primary_key, ', '.join(non_primary_fields), create_args_string(len(non_primary_fields)))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (table_name, ', '.join(list(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields))), primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (table_name, primary_key)

# 接着创建Model类，这个类被所有数据表的类继承。定义了在数据表中要执行的一些基本操作
class Model(dict, metaclass = ModelMetaClass):

    def __init__(self, **kw):
        super().__init__(**kw)

    def __getattr__(self, key):
        try:
            return kw[key]
        except KeyError:
            raise AttributeError("Model object has no attribute %s" % key)

    def __setattr__(self, key, value):
        kw[key] = value

    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if not value:
            field = self.__mappings__[key]
            if field.default:
                value = field.default() if callable(field.default) else field.default
                logging.debug("key %s using default value %s" % (key, value))
                setattr(self, key, value)
        return value

    # classmethod可以在类不实例化时就调用，并且第一个参数是类cls。与staticmethod没有很大的区别
    @classmethod
    async def findAll(cls, where = None, args = None, **kw):
        # 通过where语句进行查找。在原始__select__语句中并没有加where限定
        sql = [cls.__select__]
        if where:
            sql.append("where")
            sql.append(where)
        if not args:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple and len(limit) == 2):
                sql.append('?', '?')
                args.extend(limit) # extend()允许同时接纳多个数
            else:
                raise ValueError("Invalid limit value: %s" % str(limit))
        res = await select(' '.join(sql), args)
        return [cls(**r) for r in res]

    @classmethod
    async def findNumber(cls, selectField, where = None, args = None):
        # 专门查找数字
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)] # _num_存储查出来的数量
        if where:
            sql.append('where')
            sql.append(where)
        res = await select(sql, args, 1)
        if len(res) == 0:
            return None
        logging.info("res of findNumber: %s" % str(res))
        return res[0]['_num_']

    @classmethod
    async def find(cls, pk):
        # 通过主键进行查找
        res = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__),[pk], args)
        if len(res) == 0:
            return None
        return cls(**res[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn("failed to insert record: affected rows: %d" % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn("failed to update record: affected rows: %d" % rows)

    async def delete(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn("faile to delete record: affected rows: %d" % rows)

# uid生成函数
def next_uid():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(name = 'id', column_type = 'varchar(50)', primary_key = True, default = next_uid)
    email = StringField(name = 'email', column_type = 'varchar(50)')
    password = StringField(name = 'password', column_type = 'varchar(50)')
    name = StringField(name = 'name', column_type = 'varchar(50)')
    admin = BoolField(name = 'admin')
    image = StringField(name = 'avatar')
    created_at = FloatField(name = 'create_time', default = time.time)

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(name = 'id', column_type = 'varchar(50)', primary_key = True)
    user_id = StringField(name = 'user_id', column_type = 'varchar(50)')
    user_name = StringField(name = 'user_name')
    user_image = StringField('user_image')
    name = StringField(name = 'name')
    summary = StringField(name = 'summary', column_type = 'varchar(200)')
    content = TextField(name = 'content')
    created_at = FloatField(name = 'create_time', default = time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(name = 'id', primary_key = True)
    user_id = StringField(name = 'user_id', column_type = 'varchar(50)')
    user_name = StringField(name = 'user_name')
    user_image = StringField('user_image')
    content = TextField()
    created_at = FloatField(default = time.time)

