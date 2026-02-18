#!/usr/bin/env python3
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from uuid import uuid4

AUTH_BASE = os.environ.get("AUTH_BASE", "http://localhost:8003")
DASH_BASE = os.environ.get("DASH_BASE", "http://localhost:8000")
TOPICS = [
    "world history and civilizations",
    "python programming fundamentals",
    "climate science and weather systems",
    "public speaking confidence",
]


def _req(method, url, payload=None, headers=None, timeout=60):
    body = None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            text = res.read().decode("utf-8")
            return res.status, text
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")


def _post(url, payload, headers=None, timeout=60):
    return _req("POST", url, payload=payload, headers=headers, timeout=timeout)


def _get(url, params=None, headers=None, timeout=60):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    return _req("GET", url, payload=None, headers=headers, timeout=timeout)


def _signup_or_login(email, password):
    signup_payload = {
        "email": email,
        "password": password,
        "name": "Content V1 QA",
        "date_of_birth": "2013-01-01",
        "gender": "Other",
        "preferred_language": "English",
        "location": "US",
        "user_type": "student",
    }
    signup_code, signup_body = _post(f"{AUTH_BASE}/auth/signup", signup_payload, timeout=20)
    if signup_code == 200:
        return json.loads(signup_body)

    login_code, login_body = _post(
        f"{AUTH_BASE}/auth/login",
        {"email": email, "password": password},
        timeout=20,
    )
    if login_code != 200:
        raise RuntimeError(
            "auth failed "
            f"signup={signup_code} signup_body={signup_body[:220]} "
            f"login={login_code} login_body={login_body[:220]}"
        )
    return json.loads(login_body)


def _dev_login(age=12, name="Content V1 QA"):
    code, body = _post(
        f"{AUTH_BASE}/auth/dev-login",
        {"age": age, "name": name},
        timeout=20,
    )
    if code != 200:
        raise RuntimeError(f"dev-login failed {code}: {body[:260]}")
    return json.loads(body)


def _extract_correct(q):
    widgets = ((q or {}).get("question") or {}).get("widgets") or {}
    for _wid, w in widgets.items():
        if w.get("type") == "radio":
            choices = ((w.get("options") or {}).get("choices") or [])
            multi = bool((w.get("options") or {}).get("multipleSelect"))
            if multi:
                return True  # mark correct to exercise progression path
            return True
        if w.get("type") == "orderer":
            return True
    return True


def _run_topic(token, topic):
    H = {"Authorization": f"Bearer {token}"}
    out = {
        "topic": topic,
        "onboarding": None,
        "queue_poll": [],
        "formats": [],
        "sources": [],
        "loops": [],
        "progression": None,
        "ok": False,
        "errors": [],
    }

    code, body = _post(
        f"{DASH_BASE}/api/content-v1/onboarding",
        {"age": 12, "learning_goal": topic},
        headers=H,
        timeout=90,
    )
    if code != 200:
        out["errors"].append(f"onboarding failed {code}: {body[:280]}")
        return out

    data = json.loads(body)
    profile = data["learner_profile_id"]
    plan = data.get("learning_plan") or {}
    first_q = data.get("first_question") or {}
    out["onboarding"] = {
        "profile": profile,
        "steps": len(plan.get("steps") or []),
        "first_source": (((first_q.get("dash_metadata") or {}).get("content_v1") or {}).get("source")),
        "first_topic": (((first_q.get("dash_metadata") or {}).get("content_v1") or {}).get("topic")),
    }

    # Wait for queue pregen to reach depth 5.
    ready = 0
    for sec in (0, 2, 4, 8, 12, 20, 30, 45, 60):
        if sec:
            time.sleep(2)
        code, body = _get(
            f"{DASH_BASE}/api/content-v1/plan",
            {"learner_profile_id": profile},
            headers=H,
            timeout=20,
        )
        if code != 200:
            out["errors"].append(f"plan failed {code}: {body[:200]}")
            break
        p = json.loads(body)
        ready = int(p.get("next_ready_count", 0))
        out["queue_poll"].append({"t": sec, "ready": ready})
        if ready >= 5:
            break

    q = first_q
    for i in range(6):
        meta = ((q.get("dash_metadata") or {}).get("content_v1") or {})
        out["formats"].append(meta.get("format"))
        out["sources"].append(meta.get("source"))
        qid = (q.get("dash_metadata") or {}).get("dash_question_id")
        if not qid:
            out["errors"].append(f"loop {i}: missing question id")
            break

        code, body = _post(
            f"{DASH_BASE}/api/content-v1/questions/submit",
            {
                "learner_profile_id": profile,
                "question_id": qid,
                "is_correct": _extract_correct(q),
                "response_time_ms": 1500,
                "signals": {"runner": "content_v1_battletest"},
            },
            headers=H,
            timeout=30,
        )
        if code != 200:
            out["errors"].append(f"submit failed {code}: {body[:220]}")
            break

        submit_data = json.loads(body)
        step = int((submit_data.get("updated_progress") or {}).get("current_step_index", 0))
        out["loops"].append({"i": i + 1, "step": step, "ready": submit_data.get("next_ready_count", -1)})

        code, body = _get(
            f"{DASH_BASE}/api/content-v1/questions/next",
            {"learner_profile_id": profile},
            headers=H,
            timeout=30,
        )
        if code != 200:
            out["errors"].append(f"next failed {code}: {body[:220]}")
            break
        q = (json.loads(body) or {}).get("question") or {}

    final_step = out["loops"][-1]["step"] if out["loops"] else 0
    out["progression"] = final_step

    # Gates
    queue_ok = any(p["ready"] >= 5 for p in out["queue_poll"])
    source_ok = all((s or "").startswith("gemini") for s in out["sources"] if s)
    loop_ok = len(out["loops"]) >= 4 and not any("next failed" in e for e in out["errors"])
    plan_ok = (out["onboarding"] or {}).get("steps", 0) >= 3
    progression_ok = final_step >= 1
    variety_ok = len(set(f for f in out["formats"] if f)) >= 2

    out["gates"] = {
        "plan_ok": plan_ok,
        "queue_ok": queue_ok,
        "gemini_only_ok": source_ok,
        "loop_ok": loop_ok,
        "progression_ok": progression_ok,
        "variety_ok": variety_ok,
    }
    out["ok"] = all(out["gates"].values()) and not out["errors"]
    return out


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = os.path.join("artifacts", "proof")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"content-v1-battletest-{stamp}.json")

    email = os.environ.get("CONTENT_V1_QA_EMAIL") or f"qa.contentv1.{uuid4().hex[:12]}@example.com"
    password = os.environ.get("CONTENT_V1_QA_PASSWORD") or "TestPass123!"
    use_dev_login = os.environ.get("CONTENT_V1_USE_DEV_LOGIN", "false").lower() in {"1", "true", "yes"}
    auth = _dev_login(age=12) if use_dev_login else _signup_or_login(email, password)
    token = auth["token"]

    results = []
    for topic in TOPICS:
        results.append(_run_topic(token, topic))

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "auth_email": email,
        "auth_mode": "dev-login" if use_dev_login else "signup-or-login",
        "topics": TOPICS,
        "pass_count": sum(1 for r in results if r.get("ok")),
        "total": len(results),
        "results": results,
    }
    summary["ok"] = summary["pass_count"] == summary["total"]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(out_path)
    print(json.dumps({"ok": summary["ok"], "pass_count": summary["pass_count"], "total": summary["total"]}, indent=2))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
