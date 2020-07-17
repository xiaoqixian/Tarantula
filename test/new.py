#今天看到Python的一个__new__方法，感觉挺有意思的。
#意思是在类实例化时，__new__比__init__还要提前调用。同时__new__还是一个静态方法

class Klass(object):
    def __init__(self):
        print("__init__")

    def __new__(cls): #cls代表要实例化的类，
        print("__new__")
        return object.__new__(cls)

k = Klass()
