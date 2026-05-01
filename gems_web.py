#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════╗
║  GALAXY FARM · TWO-STEP REWARD SYSTEM v7.0                    ║
║  Dream Cricket 25 - ULTRA Farmer CYBER EDITION                ║
║  Two-Step Method: Unclaim → Claim (Repeat!)                   ║
╚════════════════════════════════════════════════════════════════╝

FULLY RESTORED: All UI Features + Two-Step Reward System
- Success Tracking ✓
- Worker Speed Display ✓
- Mission Logs ✓
- Progress Bars & Stats ✓
- Two-Step Rewards: Unclaim + Claim (10 Gems per cycle)
"""

from flask import Flask, jsonify, request, session
import requests as req
import json, time, base64, math, threading, os, secrets
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

URL_USERDATA = "https://api-prod.dreamgamestudios.in/userdata/graphql"
URL_RECEIPT  = "https://api-prod.dreamgamestudios.in/receiptvalidator/graphql"
ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL", "admin@dc25.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "changeme123")
MAX_WORKERS    = 200

MODES = {
    # ✅ 10 GEMS PER CYCLE (2-step: unclaim + claim) — MAIN METHOD
    "gems10": {
        "label":"💎 10 Gems (2-Step)", "unit":"Gems", "type":"reward_gems10",
        "templateId":128800,
        "currencyTypeId":2, "amount":10,
    },
    # ✅ 4 gems per click (single-step)
    "gems": {
        "label":"💎 4 Gems", "unit":"Gems", "type":"reward_gems",
        "templateId":127900,
        "currencyTypeId":2, "amount":4,
    },
    # ✅ 30 tickets per click
    "tickets": {
        "label":"🎫 Tickets", "unit":"Tickets", "type":"reward_tickets",
        "templateId":124339,"currencyTypeId":23, "amount":30,
    },
    # ✅ 2 elite cards per click
    "elite": {
        "label":"🃏 Elite",  "unit":"Elite",   "type":"reward_elite",
        "templateId":127574,"currencyTypeId":14, "amount":2,
    },
    # ✅ 100 coins per click
    "coins": {
        "label":"🪙 Coins", "unit":"Coins", "type":"reward_coins",
        "templateId":127573,"currencyTypeId":9, "amount":100,
    },
    "legendary": {
        "label":"⭐ Legendary","unit":"Legendary","type":"chain",
        "elite_per_card":10,
        "reward_currencyTypeId":15,"reward_amount":1,
        "cost_currencyTypeId":14,"cost_amount":10,
        "attr_2770":"5.000000","amount":1,
    },
    "champion": {
        "label":"👑 Champion","unit":"Champion","type":"chain",
        "elite_per_card":10,
        "reward_currencyTypeId":16,"reward_amount":1,
        "cost_currencyTypeId":14,"cost_amount":10,
        "attr_2770":"49.000000","amount":1,
    },
}

_ts  = int(time.time())
_tsl = threading.Lock()
slots = {
    "A": {"job": None, "history": [], "lock": threading.Lock()},
    "B": {"job": None, "history": [], "lock": threading.Lock()},
}

SELF_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
def auto_ping():
    while True:
        time.sleep(600)
        try: req.get(f"{SELF_URL}/ping", timeout=10)
        except: pass
threading.Thread(target=auto_ping, daemon=True).start()

def uts():
    global _ts
    with _tsl:
        _ts += 1
        return str(_ts)

# ════════════════════════════════════════════════════════════════
# ✅ TWO-STEP REWARD SYSTEM (10 GEMS)
# ════════════════════════════════════════════════════════════════

# STEP 1: UNCLAIM MUTATION (Reset the attribute)
def build_gems10_unclaim_mutation():
    """
    addUserGameAttribute mutation
    - Reset groupAttributeId 3065 to "2" (unclaim state)
    - Prepares for next claim
    """
    return {
        "query": """mutation addUserGameAttribute($input: [AddUserGameAttributeInput]){
            addUserGameAttribute(input: $input) {
                id groupId parentId groupAttributeId attributeName groupName attributeValue
            }
        }""",
        "variables": {"input": [{
            "templateId": 128800,
            "groupAttributeId": 3065,
            "attributeValue": "2",
            "status": 1,
        }]}
    }

# STEP 2: CLAIM MUTATION (Claim the reward)
def build_gems10_claim_mutation():
    """
    assignUserRewardBulk mutation
    - Claim 10 gems
    - Attributes: 3046="1", 3065="1" (claim state)
    - currencyTypeId: 2 (Gems)
    - currencyAmount: 10
    """
    return {
        "query": """mutation assignUserRewardBulk ($input: [UserRewardInput]) {
            assignUserRewardBulk (input: $input) { responseStatus }
        }""",
        "variables": {"input": [{
            "templateId": 128800,
            "templateAttributes": [
                {"templateId": 0, "groupAttributeId": 3046, "attributeValue": "1"},
                {"templateId": 0, "groupAttributeId": 3065, "attributeValue": "1"},
            ],
            "gameItemRewards": [],
            "currencyRewards": [{
                "currencyTypeId": 2,
                "currencyAmount": 10,
                "giveAwayType": 7,
                "meta": "Reward"
            }]
        }]}
    }

# ════════════════════════════════════════════════════════════════
# SINGLE-STEP REWARD MUTATIONS
# ════════════════════════════════════════════════════════════════

def build_gems_mutation():
    """4 Gems per click (single-step)"""
    return {
        "query": """mutation assignUserRewardBulk ($input: [UserRewardInput]) {
            assignUserRewardBulk (input: $input) { responseStatus }
        }""",
        "variables": {"input": [{
            "templateId": 127900,
            "templateAttributes": [
                {"templateId": 0, "groupAttributeId": 3046, "attributeValue": "0"},
                {"templateId": 0, "groupAttributeId": 3065, "attributeValue": "0"}
            ],
            "gameItemRewards": [],
            "currencyRewards": [{
                "currencyTypeId": 2,
                "currencyAmount": 4,
                "giveAwayType": 7,
                "meta": "Reward"
            }]
        }]}
    }

def build_elite_mutation():
    """2 Elite Cards per click (single-step)"""
    return {
        "query": """mutation assignUserRewardBulk ($input: [UserRewardInput]) {
            assignUserRewardBulk (input: $input) { responseStatus }
        }""",
        "variables": {"input": [{
            "templateId": 127574,
            "templateAttributes": [
                {"templateId": 0, "groupAttributeId": 3277, "attributeValue": "0"},
                {"templateId": 0, "groupAttributeId": 3283, "attributeValue": "0"},
                {"templateId": 0, "groupAttributeId": 3289, "attributeValue": uts()},
                {"templateId": 0, "groupAttributeId": 3290, "attributeValue": "0"}
            ],
            "gameItemRewards": [],
            "currencyRewards": [{
                "currencyTypeId": 14,
                "currencyAmount": 2,
                "giveAwayType": 7,
                "meta": "Reward"
            }]
        }]}
    }

def build_tickets_mutation():
    """30 Tickets per click (single-step)"""
    return {
        "query": """mutation assignUserRewardBulk ($input: [UserRewardInput]) {
            assignUserRewardBulk (input: $input) { responseStatus }
        }""",
        "variables": {"input": [{
            "templateId": 124339,
            "templateAttributes": [
                {"templateId": 0, "groupAttributeId": 3277, "attributeValue": "0"},
                {"templateId": 0, "groupAttributeId": 3283, "attributeValue": "0"},
                {"templateId": 0, "groupAttributeId": 3289, "attributeValue": uts()},
                {"templateId": 0, "groupAttributeId": 3290, "attributeValue": "0"}
            ],
            "gameItemRewards": [],
            "currencyRewards": [{
                "currencyTypeId": 23,
                "currencyAmount": 30,
                "giveAwayType": 11,
                "meta": "Reward"
            }]
        }]}
    }

def build_coins_mutation():
    """100 Coins per click (single-step)"""
    return {
        "query": """mutation assignUserRewardBulk ($input: [UserRewardInput]) {
            assignUserRewardBulk (input: $input) { responseStatus }
        }""",
        "variables": {"input": [{
            "templateId": 127573,
            "templateAttributes": [
                {"templateId": 0, "groupAttributeId": 3277, "attributeValue": "0"},
                {"templateId": 0, "groupAttributeId": 3283, "attributeValue": "0"},
                {"templateId": 0, "groupAttributeId": 3289, "attributeValue": uts()},
                {"templateId": 0, "groupAttributeId": 3290, "attributeValue": "0"}
            ],
            "gameItemRewards": [],
            "currencyRewards": [{
                "currencyTypeId": 9,
                "currencyAmount": 100,
                "giveAwayType": 7,
                "meta": "Reward"
            }]
        }]}
    }

def build_exchange_mutation(mode_key):
    m = MODES[mode_key]
    return {
        "query": """mutation assignStorePurchase ($input: ProductPurchaseAndAssignInput) {
            assignStorePurchase (input: $input) {
                purchaseState purchaseType acknowledgementState consumptionState
                orderId validPurchase kind rewardSuccess
            }
        }""",
        "variables": {"input": {
            "productPurchaseInput": {"packageName":"","productId":"","purchaseToken":"","platform":"","orderId":"","price":0,"currencyCode":"","priceText":""},
            "productInfoInput": {
                "templateAttributeInputs": [
                    {"templateId":104716,"groupAttributeId":2758,"attributeValue":"1"},
                    {"templateId":104716,"groupAttributeId":2764,"attributeValue":"0.000000"},
                    {"templateId":104716,"groupAttributeId":2770,"attributeValue":m["attr_2770"]},
                    {"templateId":104716,"groupAttributeId":2775,"attributeValue":"0.000000"},
                    {"templateId":104716,"groupAttributeId":2780,"attributeValue":"0.000000"},
                    {"templateId":104716,"groupAttributeId":2795,"attributeValue":"946645200000"},
                    {"templateId":104716,"groupAttributeId":2804,"attributeValue":"0"}
                ],
                "gameItemInputs": [], "userOwnedItemInputs": [],
                "currencyInputs": [{"currencyTypeId":m["reward_currencyTypeId"],"currencyAmount":m["reward_amount"]}],
                "storeListingInput": {"storeId":945961900,"storeItemListingId":104716,"bundleId":563354144}
            },
            "currencyDebit": [{"currencyTypeId":m["cost_currencyTypeId"],"currencyAmount":m["cost_amount"]}]
        }}
    }

def get_uid(token):
    try:
        p = token.split('.')[1]; p += '='*(4-len(p)%4)
        return json.loads(base64.b64decode(p)).get('user-info',{}).get('id','unknown')
    except: return 'unknown'

def make_headers(token):
    return {
        "Host":"api-prod.dreamgamestudios.in","Accept":"*/*",
        "Accept-Encoding":"gzip, deflate",
        "Authorization":f"Bearer {token}",
        "Content-Type":"application/json; charset=utf-8",
        "X-SpineSDK":"0.1","gameId":"1","studioId":"1",
        "userId":get_uid(token),"game-env":"BLUE","gameVersion":"1.5.55",
        "secretKey":"6b77f094-45e2-46d0-b6cc-827dcb5f6b85",
        "X-API-VERSION":"1",
        "User-Agent":"ProjectCricketUE4/++UE4+Release-4.27-CL-0 Android/15"
    }

# ════════════════════════════════════════════════════════════════
# EXECUTION LOGIC
# ════════════════════════════════════════════════════════════════

def do_single(hdr, mode_key):
    """Execute a single reward request"""
    m = MODES[mode_key]
    try:
        if m["type"] == "reward_gems10":
            # TWO-STEP METHOD: Unclaim → Claim
            
            # STEP 1: UNCLAIM (Reset attribute)
            r1 = req.post(URL_USERDATA, headers=hdr, json=build_gems10_unclaim_mutation(), timeout=15)
            if r1.status_code != 200:
                return False
            
            d1 = r1.json()
            attrs = d1.get("data", {}).get("addUserGameAttribute")
            
            # Verify unclaim was successful (attributeValue should be "2")
            if not (attrs and len(attrs) > 0 and attrs[0].get("attributeValue") == "2"):
                return False
            
            # STEP 2: CLAIM (Get 10 gems)
            r2 = req.post(URL_USERDATA, headers=hdr, json=build_gems10_claim_mutation(), timeout=15)
            if r2.status_code != 200:
                return False
            
            d2 = r2.json()
            rewards = d2.get("data", {}).get("assignUserRewardBulk")
            
            # Verify claim was successful (responseStatus should be True or "SUCCESS")
            if rewards and len(rewards) > 0:
                status = rewards[0].get("responseStatus")
                return status == True or status == "SUCCESS"
            return False
            
        elif m["type"] == "reward_gems":
            r = req.post(URL_USERDATA, headers=hdr, json=build_gems_mutation(), timeout=15)
            return r.status_code == 200
            
        elif m["type"] == "reward_tickets":
            r = req.post(URL_USERDATA, headers=hdr, json=build_tickets_mutation(), timeout=15)
            return r.status_code == 200
            
        elif m["type"] == "reward_coins":
            r = req.post(URL_USERDATA, headers=hdr, json=build_coins_mutation(), timeout=15)
            return r.status_code == 200
            
        elif m["type"] == "reward_elite" or m["type"] == "chain_elite":
            r = req.post(URL_USERDATA, headers=hdr, json=build_elite_mutation(), timeout=15)
            return r.status_code == 200
            
        else:
            r = req.post(URL_RECEIPT, headers=hdr, json=build_exchange_mutation(mode_key), timeout=15)
            if r.status_code == 200:
                return r.json().get("data",{}).get("assignStorePurchase",{}).get("rewardSuccess") == True
            return False
    except:
        return False

def run_phase(slot, hdr, total, workers, fn, phase_key):
    lk = slots[slot]["lock"]
    batches = math.ceil(total/workers)
    bt = []; phase_done = 0
    for b in range(batches):
        with lk:
            j = slots[slot]["job"]
            if not j or not j["running"]: return phase_done
        sz = min(workers, total - b*workers)
        if sz <= 0: break
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=sz) as ex:
            fs = [ex.submit(fn) for _ in range(sz)]
            results = [f.result() for f in as_completed(fs)]
        t1 = time.time()
        ok = sum(1 for r in results if r); bad = sz - ok; phase_done += ok
        bt.append(t1-t0)
        if len(bt) > 10: bt.pop(0)
        avg = sum(bt)/len(bt); spd = round(workers/avg, 1); eta = (batches-b-1)*avg
        with lk:
            j = slots[slot]["job"]
            if j:
                j[phase_key] = phase_done; j["fail"] += bad
                j["phase_done"] = (b+1)*workers; j["eta"] = eta; j["speed"] = spd
                j["speed_history"].append(spd)
                if len(j["speed_history"]) > 30: j["speed_history"].pop(0)
    return phase_done

def run_job(slot):
    lk = slots[slot]["lock"]
    with lk:
        j = slots[slot]["job"]
        if not j: return
        token = j["token"]; total = j["total"]
        workers = j["workers"]; mode_key = j["mode_key"]
    hdr = make_headers(token)
    m = MODES[mode_key]

    if m["type"] == "chain":
        elite_needed = total * m["elite_per_card"]
        clicks_needed = math.ceil(elite_needed / MODES["elite"]["amount"])
        with lk:
            j = slots[slot]["job"]
            if j:
                j["phase"] = 1; j["phase1_total"] = clicks_needed
                j["phase2_total"] = total; j["phase_done"] = 0
        p1ok_clicks = run_phase(slot, hdr, clicks_needed, workers,
                         lambda: do_single(hdr, "elite_internal"), "phase1_success")
        p1ok_elite = p1ok_clicks * MODES["elite"]["amount"]
        with lk:
            j = slots[slot]["job"]
            if not j or not j["running"]:
                _finish(slot, mode_key, total, workers); return
            j["phase"] = 2; j["phase_done"] = 0
        cards = p1ok_elite // m["elite_per_card"]
        run_phase(slot, hdr, cards, max(1, workers//5),
                  lambda: do_single(hdr, mode_key), "phase2_success")
    else:
        run_phase(slot, hdr, total, workers,
                  lambda: do_single(hdr, mode_key), "success")

    _finish(slot, mode_key, total, workers)

# Elite internal for chain
MODES["elite_internal"] = {
    "label":"🃏 Elite", "unit":"Elite", "type":"chain_elite",
    "templateId":127574,"currencyTypeId":14,"amount":2
}

def _finish(slot, mode_key, total, workers):
    lk = slots[slot]["lock"]
    with lk:
        j = slots[slot]["job"]
        if not j: return
        j["running"] = False; j["done"] = True; j["end_time"] = time.time()
        elapsed = j["end_time"] - j["start_time"]
        m = MODES[mode_key]
        success = j.get("phase2_success",0) if m["type"]=="chain" else j.get("success",0)
        entry = {
            "reward": success * m["amount"], "unit": m["unit"], "label": m["label"],
            "mode_key": mode_key, "success": success, "total": total, "workers": workers,
            "elapsed": round(elapsed,1), "time": datetime.now().strftime("%H:%M:%S"),
            "date": datetime.now().strftime("%d %b")
        }
        slots[slot]["history"].insert(0, entry)
        if len(slots[slot]["history"]) > 5:
            slots[slot]["history"] = slots[slot]["history"][:5]

def is_logged_in(): return session.get("logged_in") == True

def get_slot_status(slot):
    lk = slots[slot]["lock"]
    with lk:
        j = slots[slot]["job"]
        if not j:
            return {"running":False,"done":False}
        return {
            "running": j.get("running",False),
            "done": j.get("done",False),
            "mode": j.get("mode_key",""),
            "total": j.get("total",0),
            "success": j.get("success",0),
            "fail": j.get("fail",0),
            "speed": j.get("speed",0),
            "eta": j.get("eta",0),
            "phase": j.get("phase",0),
            "phase1_total": j.get("phase1_total",0),
            "phase1_success": j.get("phase1_success",0),
            "phase2_total": j.get("phase2_total",0),
            "phase2_success": j.get("phase2_success",0),
            "speed_history": j.get("speed_history",[]),
            "history": slots[slot].get("history",[])
        }

@app.route("/ping", methods=["GET"])
def ping():
    return "pong"

@app.route("/login", methods=["POST"])
def login():
    email = request.json.get("email","")
    pwd = request.json.get("password","")
    if email == ADMIN_EMAIL and pwd == ADMIN_PASSWORD:
        session["logged_in"] = True
        return jsonify({"ok":True})
    return jsonify({"ok":False}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok":True})

@app.route("/start", methods=["POST"])
def start():
    if not is_logged_in(): return jsonify({"error":"not logged in"}), 401
    slot = request.json.get("slot","A")
    if slot not in slots: return jsonify({"error":"invalid slot"}), 400
    lk = slots[slot]["lock"]
    with lk:
        if slots[slot]["job"] and slots[slot]["job"].get("running"):
            return jsonify({"error":"already running"}), 400
        token = request.json.get("token","")
        total = int(request.json.get("total",100))
        workers = int(request.json.get("workers",50))
        mode_key = request.json.get("mode","gems10")
        if mode_key not in MODES: return jsonify({"error":"invalid mode"}), 400
        slots[slot]["job"] = {
            "token":token, "total":total, "workers":workers, "mode_key":mode_key,
            "running":True, "done":False, "start_time":time.time(), "end_time":None,
            "success":0, "fail":0, "phase":0, "phase1_total":0, "phase1_success":0,
            "phase2_total":0, "phase2_success":0, "speed":0, "eta":0, "phase_done":0,
            "speed_history":[]
        }
    threading.Thread(target=run_job, args=(slot,), daemon=True).start()
    return jsonify({"ok":True})

@app.route("/stop", methods=["POST"])
def stop():
    if not is_logged_in(): return jsonify({"error":"not logged in"}), 401
    slot = request.json.get("slot","A")
    if slot not in slots: return jsonify({"error":"invalid slot"}), 400
    lk = slots[slot]["lock"]
    with lk:
        if slots[slot]["job"]: slots[slot]["job"]["running"] = False
    return jsonify({"ok":True})

@app.route("/status", methods=["GET"])
def status():
    if not is_logged_in(): return jsonify({"error":"not logged in"}), 401
    slot = request.args.get("slot","A")
    if slot not in slots: return jsonify({"error":"invalid slot"}), 400
    return jsonify(get_slot_status(slot))

@app.route("/modes", methods=["GET"])
def modes():
    return jsonify({k:{"label":v.get("label",""),"unit":v.get("unit","")} for k,v in MODES.items()})

@app.route("/", methods=["GET"])
def index():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>🌌 GALAXY FARM - CYBER EDITION v7.0</title>
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Courier New',monospace; background:#0a0e27; color:#00ff88; overflow-x:hidden; }
        .container { max-width:1200px; margin:0 auto; padding:20px; }
        h1 { text-align:center; font-size:2.5em; margin:20px 0; text-shadow:0 0 20px #00ff88; }
        .grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin:20px 0; }
        .card { background:#1a1f3a; border:2px solid #00ff88; padding:20px; border-radius:10px; box-shadow:0 0 15px rgba(0,255,136,0.3); }
        .card h2 { margin:10px 0; color:#00ffff; }
        input, select { background:#0a0e27; border:1px solid #00ff88; color:#00ff88; padding:8px; margin:5px 0; width:100%; }
        button { background:#00ff88; color:#0a0e27; border:none; padding:10px 20px; cursor:pointer; font-weight:bold; margin:5px 0; border-radius:5px; }
        button:hover { background:#00ffff; }
        .status { margin:10px 0; padding:10px; background:#0f1428; border-left:3px solid #00ff88; }
        .success { color:#00ff88; }
        .fail { color:#ff0055; }
        .info { color:#00ffff; }
        .progress { width:100%; height:20px; background:#0f1428; border:1px solid #00ff88; margin:10px 0; }
        .progress-bar { height:100%; background:linear-gradient(90deg,#00ff88,#00ffff); width:0%; }
        .history { max-height:300px; overflow-y:auto; }
        .history-item { padding:8px; margin:5px 0; background:#0f1428; border-left:3px solid #00ff88; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🌌 GALAXY FARM · CYBER EDITION v7.0</h1>
        <p style="text-align:center; color:#00ffff; margin-bottom:30px;">Two-Step Reward System: Unclaim → Claim (Repeat!)</p>
        
        <div class="grid">
            <div class="card">
                <h2>Slot A</h2>
                <select id="modeA">
                    <option value="gems10">💎 10 Gems (2-Step)</option>
                    <option value="gems">💎 4 Gems</option>
                    <option value="tickets">🎫 Tickets</option>
                    <option value="coins">🪙 Coins</option>
                    <option value="elite">🃏 Elite</option>
                </select>
                <input type="password" id="tokenA" placeholder="Token">
                <input type="number" id="totalA" value="100" placeholder="Total">
                <input type="number" id="workersA" value="50" placeholder="Workers">
                <button onclick="start('A')">START</button>
                <button onclick="stop('A')" style="background:#ff0055;">STOP</button>
                <div id="statusA"></div>
                <div class="history" id="historyA"></div>
            </div>
            
            <div class="card">
                <h2>Slot B</h2>
                <select id="modeB">
                    <option value="gems10">💎 10 Gems (2-Step)</option>
                    <option value="gems">💎 4 Gems</option>
                    <option value="tickets">🎫 Tickets</option>
                    <option value="coins">🪙 Coins</option>
                    <option value="elite">🃏 Elite</option>
                </select>
                <input type="password" id="tokenB" placeholder="Token">
                <input type="number" id="totalB" value="100" placeholder="Total">
                <input type="number" id="workersB" value="50" placeholder="Workers">
                <button onclick="start('B')">START</button>
                <button onclick="stop('B')" style="background:#ff0055;">STOP</button>
                <div id="statusB"></div>
                <div class="history" id="historyB"></div>
            </div>
        </div>
    </div>

    <script>
        let token = prompt("Enter admin password:") || "";
        
        async function start(slot) {
            const mode = document.getElementById("mode"+slot).value;
            const t = document.getElementById("token"+slot).value;
            const total = document.getElementById("total"+slot).value;
            const workers = document.getElementById("workers"+slot).value;
            
            const res = await fetch("/start", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({slot, mode, token: t, total, workers})
            });
            
            if (res.ok) {
                updateStatus(slot);
                setInterval(() => updateStatus(slot), 1000);
            } else {
                alert("Error starting job");
            }
        }
        
        async function stop(slot) {
            await fetch("/stop", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({slot})
            });
            updateStatus(slot);
        }
        
        async function updateStatus(slot) {
            const res = await fetch("/status?slot="+slot);
            const data = await res.json();
            
            let html = `
                <div class="status">
                    <div class="info">Mode: ${data.mode}</div>
                    <div class="success">Success: ${data.success}/${data.total}</div>
                    <div class="fail">Failed: ${data.fail}</div>
                    <div class="info">Speed: ${data.speed} req/s</div>
                    <div class="info">ETA: ${Math.round(data.eta)}s</div>
                    <div class="progress"><div class="progress-bar" style="width:${(data.success/data.total)*100}%"></div></div>
                </div>
            `;
            
            if (data.history && data.history.length > 0) {
                html += '<div class="history">';
                data.history.forEach(h => {
                    html += `<div class="history-item"><strong>${h.label}</strong>: ${h.reward} ${h.unit} (${h.success}/${h.total}) in ${h.elapsed}s</div>`;
                });
                html += '</div>';
            }
            
            document.getElementById("status"+slot).innerHTML = html;
        }
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
