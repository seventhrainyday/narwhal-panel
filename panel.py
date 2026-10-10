#!/usr/bin/env python3
"""独角鲸 (Narwhal Cloud) 控制面板 - 本地服务端.

用法:
    python3 panel.py            # 默认监听 127.0.0.1:8080
    PORT=9000 python3 panel.py  # 自定义端口

然后在浏览器打开 http://127.0.0.1:8080 ，粘贴 API 密钥即可使用。

原理:
  浏览器直接跨域调用 api.fuckip.me 会被 CORS 拦截,
  因此本服务在同源下提供 /api/* 反向代理, 把请求原样转发到
  https://api.fuckip.me/api/v1/* (可通过环境变量 NARWHAL_UPSTREAM 覆盖,
  仅用于本地联调测试)。
"""
import json
import os
import posixpath
import urllib.request
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = os.environ.get("NARWHAL_UPSTREAM", "https://api.fuckip.me/api/v1").rstrip("/")
PORT = int(os.environ.get("PORT", "8080"))
HERE = os.path.dirname(os.path.abspath(__file__))

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade", "host", "content-length",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "NarwhalPanel/1.0"

    def log_message(self, fmt, *args):  # 安静一点, 只打关键日志
        if self.path.startswith("/api/"):
            print(f"[proxy] {self.command} {self.path}")

    def _send(self, code, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._serve_index()
        elif self.path == "/health":
            self._json(200, {"ok": True})
        elif self.path.startswith("/api/"):
            self._proxy()
        else:
            self._json(404, {"code": 404, "msg": "not found"})

    def do_POST(self): self._route()
    def do_PUT(self): self._route()
    def do_PATCH(self): self._route()
    def do_DELETE(self): self._route()

    def _route(self):
        if self.path.startswith("/api/"):
            self._proxy()
        else:
            self._json(404, {"code": 404, "msg": "not found"})

    def _serve_index(self):
        try:
            with open(os.path.join(HERE, "index.html"), "rb") as f:
                data = f.read()
        except FileNotFoundError:
            data = "<h1>index.html 缺失</h1>".encode()
        self._send(200, data, "text/html; charset=utf-8")

    def _proxy(self):
        # /api/<rest> -> UPSTREAM/<rest>
        rest = self.path[len("/api/"):]
        if "?" in rest:
            path_part, qs = rest.split("?", 1)
        else:
            path_part, qs = rest, ""
        # 防路径穿越: 归一化后必须仍在相对路径内
        norm = posixpath.normpath("/" + path_part).lstrip("/")
        if norm.startswith("..") or ".." in norm.split("/"):
            self._json(400, {"code": 400, "msg": "bad path"})
            return
        url = f"{UPSTREAM}/{norm}" + (f"?{qs}" if qs else "")

        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length > 0 else None
        headers = {}
        for k, v in self.headers.items():
            kl = k.lower()
            if kl in HOP_BY_HOP:
                continue
            headers[k] = v  # 透传 Authorization / Content-Type 等

        req = urllib.request.Request(url, data=body, headers=headers, method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                self.send_response(resp.status)
                ctype = resp.headers.get("Content-Type", "application/octet-stream")
                self.send_header("Content-Type", ctype)
                disp = resp.headers.get("Content-Disposition")
                if disp:
                    self.send_header("Content-Disposition", disp)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read() or b""
            # 上游的错误体原样透传 (通常是 {"code":非0,"msg":"..."} 或 401)
            ctype = e.headers.get("Content-Type", "application/json")
            self.send_response(e.code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:  # noqa: BLE001 - 转成 502 给前端统一处理
            self._json(502, {"code": 502, "msg": f"上游请求失败: {e}"})


def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"独角鲸控制面板已启动: http://127.0.0.1:{PORT}")
    print(f"上游 API: {UPSTREAM}/...")
    print("在页面右上角粘贴 API 密钥后即可使用, 按 Ctrl+C 退出。")
    srv.serve_forever()


if __name__ == "__main__":
    main()
