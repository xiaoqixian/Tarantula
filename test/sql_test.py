#python env:/bin/lib/python3.8
#!------------utf8------------
# > Author     : lunar
# > Mail       : lunar_ubuntu@qq.com
# > Create Time: Sat 18 Jul 2020 03:48:50 PM CST

from ../src import orm
from ../src/models import User, Blog, Comment

def test():
    yield from orm.create_pool(user = 'root', password = 'lunar', database = 'tara')

    u = User(name = 'Test', email = 'test@qq.com', passwd = 'passwd')
    yield from u.save()

for x in test():
    pass
