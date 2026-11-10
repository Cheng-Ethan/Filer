#!/usr/bin/env python3
"""Force-download HTTP server with Basic Auth.

- Directory listing offers actions per entry: 目录点名称即可进入并支持删除；文件可 打开/下载/预览(.md)/删除。
- 打开/点名称：目录进入子目录，文件在内联视图呈现（带 返回/下载/删除 工具栏），.html 全窗口打开不带工具栏。
- 页面顶部保留最近进入的 5 个目录快捷入口。
- 底部命令行可执行真实 shell 命令（在当前浏览目录中运行），输出占半屏并可折叠为一行；`cd 目录` 可直接切换浏览位置。
- Forced-download types (.json/.js/.mjs/.css/.map/.txt/.csv): 通过「下载」按钮强制下载。
- 上传: each directory view has an upload button that saves files into the current directory.
- All requests require HTTP Basic Auth.
"""

import argparse
import functools
import os
from http.server import ThreadingHTTPServer

from dls.handler import ForceDownloadHandler


def main():
    parser = argparse.ArgumentParser(description='Auth download HTTP file server')
    parser.add_argument('--port', type=int, default=9000)
    parser.add_argument('--dir', default='.', help='Directory to serve')
    parser.add_argument('--bind', default='127.0.0.1',
                        help='监听地址（默认仅本机 127.0.0.1 可访问；'
                             '暴露到网络请置于 HTTPS 反向代理之后）')
    parser.add_argument('--user',
                        help="格式 username:password（Basic Auth）；"
                             "也可用环境变量 DL_AUTH，--user 优先")
    args = parser.parse_args()

    auth = args.user if args.user is not None else os.environ.get('DL_AUTH')
    if auth is None:
        parser.error("--user must be 'username:password', both non-empty "
                     "(or set DL_AUTH)")
    user, _, password = auth.partition(':')
    if not user or not password:
        parser.error("--user must be 'username:password', both non-empty")

    os.chdir(args.dir)
    handler = functools.partial(
        ForceDownloadHandler, user=user, password=password)
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    print(f'Serving {args.dir} on {args.bind}:{args.port} (auth: {user}:****)')
    if args.bind == '0.0.0.0':
        print('WARNING: listening on all interfaces. Basic Auth is clear-text — use HTTPS.')
    server.serve_forever()


if __name__ == '__main__':
    main()