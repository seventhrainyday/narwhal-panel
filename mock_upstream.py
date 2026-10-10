#!/usr/bin/env python3
"""独角鲸 API 模拟上游 —— 仅用于面板联调测试.
按 openapi.yaml 的形状返回假数据, 并把收到的请求记到 requests.log 供核查.
"""
import json, os, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("MOCK_PORT", "18082"))
LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requests.log")

NOW = int(time.time())
VM1 = {"id": "11111111-1111-1111-1111-111111111111", "user_id": "u1", "plan_id": "p1",
       "machine_id": "m1", "remark": "测试小鸡", "status": "running", "type": "kvm",
       "cpu": 2, "ram_mb": 2048, "disk_gb": 30, "bandwidth_mbps": 200,
       "monthly_traffic_gb": 1000, "price_monthly": 5.0, "os_image": "debian-12-x64",
       "os_name": "Debian 12", "credentials": {"username": "root", "password": "********"},
       "ip": "1.2.3.4", "ip_addresses": ["1.2.3.4"], "cpu_pct": 12.5, "ram_used_mb": 512,
       "traffic_in_bytes": 10**9, "traffic_out_bytes": 2*10**9,
       "monthly_traffic_in": 10**9, "monthly_traffic_out": 2*10**9,
       "expires_at": NOW + 20*86400, "auto_renew": True, "tags": ["测试"],
       "listing_id": "", "is_listed": False, "user_email": "test@example.com",
       "machine_name": "测试母机", "machine_region": "US",
       "machine_entry_host": "entry.example.com",
       "machine_os_images": [{"id": "debian-12-x64", "name": "Debian 12"},
                             {"id": "ubuntu-22.04-x64", "name": "Ubuntu 22.04"}],
       "created_at": NOW-86400*30, "updated_at": NOW}
PLAN1 = {"id": "22222222-2222-2222-2222-222222222222", "machine_id": "m1",
         "owner_id": "o1", "name": "测试套餐", "description": "2C2G 月付",
         "cpu": 2, "ram_mb": 2048, "disk_gb": 30, "bandwidth_mbps": 200,
         "monthly_traffic_gb": 1000, "price_monthly": 5.0,
         "max_quantity": 10, "sold_quantity": 3, "allow_full_refund": True, "status": "active",
         "created_at": NOW-86400*60, "updated_at": NOW}
STATE = {
    "vms": [dict(VM1)],
    "listings": [{"id": "33333333-3333-3333-3333-333333333333", "seller_id": "s1",
                  "vm_id": VM1["id"], "price": 4.5, "status": "active",
                  "cpu": 2, "ram_mb": 2048, "disk_gb": 30, "bandwidth_mbps": 200,
                  "region": "US", "expires_at": NOW+20*86400, "created_at": NOW-86400}],
    "portfwds": [{"protocol": "tcp", "host_port": 2222, "guest_port": 22, "description": "ssh"}],
    "ippools": [{"id": "44444444-4444-4444-4444-444444444444", "name": "测试IP池",
                 "ip_type": "ipv4", "price_monthly": 1.5, "total_units": 100, "used_units": 10,
                 "connect_host": "wg.example.com", "connect_port": 51820}],
    "ipres": [{"id": "55555555-5555-5555-5555-555555555555", "user_id": "u1",
               "ip_pool_id": "44444444-4444-4444-4444-444444444444", "vm_id": "",
               "allocated_ip": "5.6.7.8", "allocated_prefix": 32,
               "wg_client_address": "10.9.0.2/32", "wg_client_public_key": "PUBKEY==",
               "status": "active", "expires_at": NOW+25*86400, "auto_renew": False,
               "price_monthly": 1.5, "remark": "测试IP", "created_at": NOW-86400*5}],
    "tickets": [{"id": "66666666-6666-6666-6666-666666666666", "user_id": "u1",
                 "type": "support", "title": "测试工单", "status": "open",
                 "content": "第一条消息内容", "created_at": NOW-3600,
                 "messages": [{"author": "user", "content": "你好, 有问题", "created_at": NOW-3600},
                              {"author": "staff", "content": "收到, 正在处理", "created_at": NOW-1800}]}],
    "machines": [{"id": "m1", "name": "测试母机", "status": "online", "region": "US",
                  "region_zh": "美国", "agent_token": "agent_tok_abc", "description": "mock",
                  "online_vms": 5}],
    "plans": [dict(PLAN1)],
    "promos": [{"id": "77777777-7777-7777-7777-777777777777", "code": "SAVE10",
                "discount_percent": 10, "max_uses": 100, "used_count": 5, "status": "active"}],
    "blocked": [{"user_id": "bad1", "email": "bad@example.com", "reason": "abuse"}],
}
ME = {"id": "u1", "email": "test@example.com", "role": "user",
      "available_balance": 42.5, "escrow_balance": 0, "escrow_locked_value": 0,
      "commission_rate": 0.1, "notify_via": "email", "notify_lang": "zh",
      "tg_chat_id": 0, "has_password": True, "is_banned": False,
      "payment_info": {"text": ""}, "created_at": NOW-86400*100}


def ok(data):
    return 200, {"code": 0, "msg": "ok", "data": data}


class H(BaseHTTPRequestHandler):
    server_version = "MockNarwhal/1.0"
    def log_message(self, *a): pass

    def _rl(self):
        ln = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(ln) if ln else b""
        ct = self.headers.get("Content-Type", "")
        try: body = json.loads(raw) if raw and "json" in ct else (raw[:500].decode("utf8", "replace") if raw else "")
        except Exception: body = "<unparseable>"
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"m": self.command, "p": self.path,
                                "auth": bool(self.headers.get("Authorization")),
                                "body": body}, ensure_ascii=False) + "\n")
        return body

    def _send(self, code, obj=None, ctype="application/json", raw=None):
        data = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data))); self.end_headers()
        self.wfile.write(data)

    def _route(self, body):
        u = urlparse(self.path); p = u.path; q = parse_qs(u.query); m = self.command
        S = STATE
        if not self.headers.get("Authorization"):
            return self._send(401, {"code": 401, "msg": "unauthorized"})
        seg = p.strip("/").split("/")

        def one(lst, key="id"):
            for x in lst:
                if str(x.get(key)) == seg[idx]: return x
            return None

        # ---- user ----
        if p == "/user/me" and m == "GET": return self._send(*ok(ME))
        if p == "/user/me/notify" and m == "PATCH": ME.update(body or {}); return self._send(*ok({}))
        if p == "/user/me/test-notify" and m == "POST": return self._send(*ok({}))
        if p == "/user/me/payment-info" and m == "PATCH": return self._send(*ok({}))
        if p == "/user/me/payment-qr" and m == "POST": return self._send(*ok({"url": "https://cdn.example.com/qr.png"}))
        if p == "/user/me/tg-bind/start" and m == "POST":
            return self._send(*ok({**ME, "tg_bot_url": "https://t.me/mockbot?start=tok123"}))
        if p == "/user/me/tg-bind" and m == "DELETE": ME["tg_chat_id"] = 0; return self._send(*ok({}))
        if p == "/user/password" and m == "POST": return self._send(*ok({}))
        if p == "/user/apikey" and m == "GET": return self._send(*ok("rnm_testkey123"))
        if p == "/user/apikey" and m == "POST": return self._send(*ok("rnm_newkey456"))
        if p == "/user/apikey" and m == "DELETE": return self._send(*ok({}))
        # ---- public ----
        if p == "/announcements" and m == "GET":
            return self._send(*ok({"announcements": [{"id": "a1", "title": "测试公告", "content": "<b>欢迎</b>使用独角鲸"}], "total": 1}))
        if p == "/machines/public" and m == "GET":
            return self._send(*ok([{"id": "m1", "name": "测试母机", "region": "US", "region_zh": "美国",
                                    "city": "Los Angeles", "status": "online", "vm_type": "kvm"}]))
        if len(seg) == 3 and seg[0] == "machines" and seg[2] == "public" and m == "GET":
            return self._send(*ok({**S["machines"][0], "description": "mock 公开详情",
                                    "os_images": [{"id": "debian-12-x64", "name": "Debian 12"}]}))
        if len(seg) == 3 and seg[0] == "machines" and seg[2] == "test-speed" and m == "POST":
            return self._send(*ok({"results": [{"country": c, "avg_ms": 150.0} for c in (body or {}).get("country_codes", [])]}))
        if p == "/tgbot/info" and m == "GET":
            return self._send(*ok({"bot_url": "https://t.me/mockbot", "bot_name": "MockBot"}))
        if p == "/plans" and m == "GET": return self._send(*ok({"plans": S["plans"], "total": len(S["plans"])}))
        if len(seg) == 2 and seg[0] == "plans" and m == "GET":
            idx = 1; pl = one(S["plans"]); return self._send(*ok(pl or {}))
        if p == "/promo-codes/preview" and m == "GET":
            return self._send(*ok({"code": q.get("code", [""])[0], "discount_percent": 10, "final_amount": 4.5}))
        # ---- vms ----
        if p == "/vms" and m == "GET":
            vms = S["vms"]
            sq = (q.get("search") or [""])[0]
            if sq: vms = [v for v in vms if sq in (v.get("remark") or "")]
            return self._send(*ok({"vms": vms, "total": len(vms), "page": 1}))
        if p == "/vms" and m == "POST":
            nv = dict(VM1, id=str(uuid.uuid4()), remark=(body or {}).get("remark") or "新购小鸡",
                      os_image=(body or {}).get("os_image") or "debian-12-x64")
            S["vms"].append(nv); return self._send(*ok(nv))
        if len(seg) == 2 and seg[0] == "vms" and m == "GET":
            idx = 1; v = one(S["vms"]); return self._send(*ok(v or {}))
        if len(seg) == 2 and seg[0] == "vms" and m == "DELETE":
            idx = 1; S["vms"] = [v for v in S["vms"] if v["id"] != seg[1]]; return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "vms" and seg[2] == "refund-preview" and m == "GET":
            return self._send(*ok({"refund_amount": 3.33}))
        if len(seg) == 3 and seg[0] == "vms" and seg[2] in ("renew", "start", "stop", "restart", "push") and m == "POST":
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "vms" and seg[2] == "reset-password" and m == "POST":
            return self._send(*ok({"password": (body or {}).get("new_password") or "RANDOMPW123"}))
        if len(seg) == 3 and seg[0] == "vms" and seg[2] == "reinstall" and m == "POST":
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "vms" and seg[2] == "auto-renew" and m == "PATCH":
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "vms" and seg[2] in ("remark", "tags") and m == "PATCH":
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "vms" and seg[2] == "port-forwards" and m == "GET":
            return self._send(*ok({"rules": S["portfwds"]}))
        if len(seg) == 3 and seg[0] == "vms" and seg[2] == "port-forwards" and m == "POST":
            S["portfwds"].append(body or {}); return self._send(*ok(body or {}))
        if len(seg) == 5 and seg[0] == "vms" and seg[2] == "port-forwards" and m == "DELETE":
            S["portfwds"] = [r for r in S["portfwds"] if not (r["protocol"] == seg[3] and str(r["host_port"]) == seg[4])]
            return self._send(*ok({}))
        # ---- market ----
        if p == "/market/listings" and m == "GET":
            return self._send(*ok({"listings": S["listings"], "total": len(S["listings"])}))
        if p == "/market/listings" and m == "POST":
            nl = {"id": str(uuid.uuid4()), "seller_id": "u1", "vm_id": (body or {}).get("vm_id"),
                  "price": (body or {}).get("price"), "status": "active", "cpu": 2,
                  "ram_mb": 2048, "disk_gb": 30, "bandwidth_mbps": 200, "region": "US",
                  "expires_at": NOW+20*86400, "created_at": NOW}
            S["listings"].append(nl); return self._send(*ok(nl))
        if len(seg) == 3 and seg[0] == "market" and seg[1] == "listings" and m == "GET":
            idx = 2; l = one(S["listings"]); return self._send(*ok(l or {}))
        if len(seg) == 3 and seg[0] == "market" and seg[1] == "listings" and m == "DELETE":
            idx = 2; S["listings"] = [x for x in S["listings"] if x["id"] != seg[2]]; return self._send(*ok({}))
        if len(seg) == 4 and seg[0] == "market" and seg[1] == "listings" and seg[3] == "buy" and m == "POST":
            return self._send(*ok({}))
        if p == "/market/my-listings" and m == "GET":
            return self._send(*ok({"listings": S["listings"], "total": len(S["listings"])}))
        # ---- ip resources ----
        if p == "/ip-resources/pools" and m == "GET": return self._send(*ok(S["ippools"]))
        if p == "/ip-resources" and m == "GET":
            return self._send(*ok({"items": S["ipres"], "total": len(S["ipres"])}))
        if p == "/ip-resources" and m == "POST":
            nr = {"id": str(uuid.uuid4()), "user_id": "u1", "ip_pool_id": (body or {}).get("ip_pool_id"),
                  "vm_id": "", "allocated_ip": "9.9.9.9", "allocated_prefix": 32,
                  "wg_client_address": "10.9.0.9/32", "wg_client_public_key": "NEWKEY==",
                  "status": "active", "expires_at": NOW+30*86400, "auto_renew": bool((body or {}).get("auto_renew")),
                  "price_monthly": 1.5, "remark": "", "created_at": NOW}
            S["ipres"].append(nr); return self._send(*ok(nr))
        if len(seg) == 2 and seg[0] == "ip-resources" and m == "GET":
            idx = 1; r = one(S["ipres"]); return self._send(*ok(r or {}))
        if len(seg) == 3 and seg[0] == "ip-resources" and seg[2] in ("renew", "reset-key") and m == "POST":
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "ip-resources" and seg[2] == "unbind" and m == "POST":
            idx = 1; r = one(S["ipres"])
            if r: r["vm_id"] = ""
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "ip-resources" and seg[2] in ("auto-renew", "remark") and m == "PATCH":
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "ip-resources" and seg[2] == "bind" and m == "POST":
            idx = 1; r = one(S["ipres"])
            if r: r["vm_id"] = (body or {}).get("vm_id", "")
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "ip-resources" and seg[2] == "client-config" and m == "GET":
            cfg = "[Interface]\nPrivateKey = MOCKKEY\nAddress = 10.9.0.2/32\n[Peer]\nPublicKey = SRVKEY\nEndpoint = wg.example.com:51820\n"
            return self._send(200, raw=cfg.encode(), ctype="text/plain")
        # ---- billing ----
        if p == "/billing/transactions" and m == "GET":
            return self._send(*ok({"transactions": [{"id": "t1", "type": "topup", "amount": 10,
                                                     "balance_type": "available", "balance_after": 42.5,
                                                     "note": "stripe", "created_at": NOW-86400}], "total": 1, "page": 1}))
        if p == "/billing/orders" and m == "GET":
            return self._send(*ok({"orders": [{"id": "o1", "type": "purchase", "amount": 5,
                                               "created_at": NOW-86400}], "total": 1, "page": 1}))
        if p == "/payment/records" and m == "GET":
            return self._send(*ok({"records": [{"id": "pr1", "gateway": "stripe", "amount": 10,
                                                "status": "paid", "created_at": NOW-86400}], "total": 1, "page": 1}))
        if len(seg) == 3 and seg[0] == "payment" and seg[1] == "records" and m == "GET":
            return self._send(*ok({"id": seg[2], "gateway": "stripe", "amount": 10, "status": "paid"}))
        if len(seg) == 3 and seg[0] == "payment" and seg[2] == "init" and m == "POST":
            return self._send(*ok({"payment_record_id": str(uuid.uuid4()),
                                    "checkout_url": "https://pay.example.com/mock",
                                    "fee_usd": 0.3, "total_usd": (body or {}).get("amount", 0)+0.3,
                                    "expires_at": NOW+3600}))
        if p == "/withdrawals/info" and m == "GET":
            return self._send(*ok({"available": 5.0, "min_amount": 1, "commission": "10%"}))
        if p == "/withdrawals" and m == "POST":
            return self._send(*ok({"id": str(uuid.uuid4()), "status": "pending"}))
        # ---- tickets ----
        if p == "/tickets" and m == "GET":
            return self._send(*ok({"tickets": S["tickets"], "total": len(S["tickets"])}))
        if p == "/tickets" and m == "POST":
            nt = {"id": str(uuid.uuid4()), "user_id": "u1", "type": "support",
                  "title": (body or {}).get("title"), "content": (body or {}).get("content"),
                  "status": "open", "created_at": NOW, "messages": []}
            S["tickets"].append(nt); return self._send(*ok(nt))
        if len(seg) == 2 and seg[0] == "tickets" and m == "GET":
            idx = 1; t = one(S["tickets"]); return self._send(*ok(t or {}))
        if len(seg) == 3 and seg[0] == "tickets" and seg[2] == "messages" and m == "POST":
            idx = 1; t = one(S["tickets"])
            if t: t.setdefault("messages", []).append({"author": "user", "content": (body or {}).get("content"), "created_at": NOW})
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "tickets" and seg[2] in ("close", "reopen") and m == "PUT":
            idx = 1; t = one(S["tickets"])
            if t: t["status"] = "closed" if seg[2] == "close" else "open"
            return self._send(*ok({}))
        # ---- owner machines ----
        if p == "/machines" and m == "GET": return self._send(*ok({"machines": S["machines"]}))
        if p == "/machines" and m == "POST":
            nm = {"id": "m"+str(uuid.uuid4())[:8], "name": (body or {}).get("name"),
                  "status": "offline", "region": "-", "agent_token": "agent_new_tok",
                  "description": (body or {}).get("description")}
            S["machines"].append(nm); return self._send(*ok(nm))
        if p == "/machines/blocked-users" and m == "GET":
            return self._send(*ok({"items": S["blocked"]}))
        if len(seg) == 3 and seg[0] == "machines" and seg[1] == "blocked-users" and m == "DELETE":
            S["blocked"] = [x for x in S["blocked"] if x["user_id"] != seg[2]]; return self._send(*ok({}))
        if len(seg) == 2 and seg[0] == "machines" and m == "GET":
            idx = 1; mc = one(S["machines"]); return self._send(*ok(mc or {}))
        if len(seg) == 2 and seg[0] == "machines" and m == "PATCH": return self._send(*ok({}))
        if len(seg) == 2 and seg[0] == "machines" and m == "DELETE":
            idx = 1; S["machines"] = [x for x in S["machines"] if x["id"] != seg[1]]; return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "machines" and seg[2] == "rotate-token" and m == "POST":
            return self._send(*ok({"agent_token": "agent_rotated_tok"}))
        if len(seg) == 3 and seg[0] == "machines" and seg[2] == "notify-buyers" and m == "POST":
            return self._send(*ok({}))
        if len(seg) == 3 and seg[0] == "machines" and seg[2] == "vms" and m == "GET":
            return self._send(*ok({"vms": S["vms"], "total": len(S["vms"])}))
        if len(seg) == 3 and seg[0] == "machines" and seg[2] == "plans" and m == "GET":
            return self._send(*ok({"plans": S["plans"], "total": len(S["plans"])}))
        if len(seg) == 3 and seg[0] == "machines" and seg[2] == "plans" and m == "POST":
            np = dict(body or {}, id=str(uuid.uuid4())); S["plans"].append(np); return self._send(*ok(np))
        if len(seg) == 3 and seg[0] == "machines" and seg[2] == "promo-codes" and m == "GET":
            return self._send(*ok({"items": S["promos"], "total": len(S["promos"])}))
        # ---- promo codes ----
        if p == "/promo-codes" and m == "POST":
            np = dict(body or {}, id=str(uuid.uuid4()), used_count=0, status="active")
            S["promos"].append(np); return self._send(*ok(np))
        if len(seg) == 3 and seg[0] == "promo-codes" and seg[2] in ("enable", "disable") and m == "PUT":
            idx = 1; pr = one(S["promos"])
            if pr: pr["status"] = "active" if seg[2] == "enable" else "disabled"
            return self._send(*ok({}))
        if len(seg) == 2 and seg[0] == "promo-codes" and m == "DELETE":
            idx = 1; S["promos"] = [x for x in S["promos"] if x["id"] != seg[1]]; return self._send(*ok({}))
        # ---- misc ----
        if p == "/files/upload" and m == "POST":
            return self._send(*ok({"url": "https://cdn.example.com/f.png"}))
        if len(seg) == 3 and seg[0] == "share" and m == "GET":
            png = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c626001000000ffff03000006000557bfabd0000000049454e44ae426082")
            return self._send(200, raw=png, ctype="image/png")
        if len(seg) == 3 and seg[0] == "plans" and m == "PATCH": return self._send(*ok({}))
        if len(seg) == 2 and seg[0] == "plans" and m == "DELETE":
            idx = 1; S["plans"] = [x for x in S["plans"] if x["id"] != seg[1]]; return self._send(*ok({}))
        return self._send(404, {"code": 404, "msg": f"mock 未实现: {m} {p}"})

    def do_GET(self): self._route(self._rl())
    def do_POST(self): self._route(self._rl())
    def do_PUT(self): self._route(self._rl())
    def do_PATCH(self): self._route(self._rl())
    def do_DELETE(self): self._route(self._rl())


if __name__ == "__main__":
    if os.path.exists(LOG): os.remove(LOG)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    print(f"mock upstream on 127.0.0.1:{PORT}, log -> {LOG}")
    srv.serve_forever()
