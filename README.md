
### **Tarantula**

> Tarantula is actually a spider species that appears in Friends

本项目将是我的第一个Python web(python3.x)项目，全程参照廖雪峰的[Python教程](https://www.liaoxuefeng.com/wiki/1016959663602400/1018138223191520)。

是一个非常简单的博客项目，没有应用任何web框架。从根本上了解一个web APP是运作的。

#### 前置知识

1. Python基础知识肯定是必须的

2. 装饰器与协程异步编程

   本项目大量运用这两个知识点，所以这两个知识点必须事先了解清楚。

3. 运用到的Python库

   aiomysql、aiohttp、asyncio等，都属于异步编程库

#### 项目结构

整个项目的目录结构为：
```bash
Tarantula/               <-- 根目录
|
+- backup/               <-- 备份目录
|
+- conf/                 <-- 配置文件
|
+- dist/                 <-- 打包目录
|
+- www/                  <-- Web目录，存放.py文件
|  |
|  +- static/            <-- 存放静态文件
|  |
|  +- templates/         <-- 存放模板文件
|
+-

```

#### [项目原理](introduction.md)
