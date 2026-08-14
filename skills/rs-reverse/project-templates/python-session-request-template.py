import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin

import requests


# Copy this template into the target Ruishu project root as main.py before use.
# It expects rs_reverse.js and mod.js to be in BASE_DIR.
BASE_DIR = Path(__file__).resolve().parent

# === Replace these for the target site ===
TARGET_URL = "https://example.com/replace-me"
API_URL = ""  # Optional business API for layered verification.
API_METHOD = "POST"
API_PARAMS = None
API_JSON = None
API_DATA = None

REQUEST_TIMEOUT = 20
NODE_TIMEOUT = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}
API_HEADERS = {}

session = requests.Session()


def extract_challenge_scripts(html):
    """Extract inline $_ts bootstrap and external r='m'/r2mKa runner from the first response."""
    payload_bootstrap = ""
    for script_body in re.findall(r"<script\b[^>]*>([\s\S]*?)</script>", html, flags=re.I):
        if "$_ts.cd" in script_body or "$_ts.nsd" in script_body:
            payload_bootstrap = script_body.strip()
            break

    runner_src = ""
    script_tags = re.findall(r"<script\b[^>]*>", html, flags=re.I)
    for script_tag in script_tags:
        src_match = re.search(r"\bsrc=['\"]([^'\"]+)['\"]", script_tag, flags=re.I)
        if not src_match:
            continue
        src = src_match.group(1)
        if "r='m'" in script_tag or 'r="m"' in script_tag or "r2m" in src or "/fpq" in src:
            runner_src = src
            break

    if not runner_src and len(script_tags) >= 2:
        src_match = re.search(r"\bsrc=['\"]([^'\"]+)['\"]", script_tags[1], flags=re.I)
        if src_match:
            runner_src = src_match.group(1)

    if not payload_bootstrap or not runner_src:
        raise RuntimeError(f"未提取到瑞数内联脚本或外链脚本，响应片段:\n{html[:1000]}")
    return payload_bootstrap, runner_src


def first_request():
    """First hop: keep Set-Cookie S/O/acw_tc in the same requests.Session."""
    response = session.get(TARGET_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    payload_bootstrap, runner_src = extract_challenge_scripts(response.text)
    runner_url = urljoin(response.url or TARGET_URL, runner_src)
    payload_runner = session.get(runner_url, headers=HEADERS, timeout=REQUEST_TIMEOUT).text

    print("first status ->", response.status_code)
    print("first final url ->", response.url)
    print("first cookies ->", session.cookies.get_dict())
    print("runner url ->", runner_url)
    return payload_bootstrap, payload_runner


def replace_placeholder(template, placeholder, payload):
    tokens = (
        f"'{placeholder}';",
        f'"{placeholder}";',
        f"'{placeholder}'",
        f'"{placeholder}"',
    )
    for token in tokens:
        if token in template:
            return template.replace(token, payload)
    raise RuntimeError(f"rs_reverse.js 缺少占位符: {placeholder}")


def build_rs_reverse_runtime(payload_bootstrap, payload_runner):
    template_path = BASE_DIR / "rs_reverse.js"
    template = template_path.read_text(encoding="utf-8")
    js_code = replace_placeholder(template, "challenge_payload_bootstrap", payload_bootstrap)
    js_code = replace_placeholder(js_code, "challenge_payload_runner", payload_runner)

    runtime_path = BASE_DIR / "rs_reverse_runtime.js"
    runtime_path.write_text(js_code, encoding="utf-8")
    return runtime_path


def _to_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def parse_generated_cookie(output):
    path_matches = re.findall(r"([A-Za-z0-9_]+)=([^;\s]+);\s*path=/", output, flags=re.I)
    if path_matches:
        return path_matches[-1]

    ignored_prefixes = ("方法：", "document.", "script.", "div.", "meta.")
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line or line.startswith(ignored_prefixes):
            continue
        for part in reversed(line.split(";")):
            part = part.strip()
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            name, value = name.strip(), value.strip()
            if re.fullmatch(r"[A-Za-z0-9_]+", name) and value:
                return name, value
    raise RuntimeError(f"未从 Node 输出解析到瑞数 Cookie:\n{output[-2000:]}")


def run_node_get_cookie(runtime_path):
    try:
        result = subprocess.run(
            ["node", str(runtime_path)],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=NODE_TIMEOUT,
            check=False,
        )
        output = result.stdout + "\n" + result.stderr
        if result.returncode != 0 and "=" not in output:
            raise RuntimeError(f"Node 执行失败({result.returncode}):\n{output[-2000:]}")
    except subprocess.TimeoutExpired as exc:
        output = _to_text(exc.stdout) + "\n" + _to_text(exc.stderr)
        print("node timeout -> try parsing cookie from partial output")

    name, value = parse_generated_cookie(output)
    return name, value, output


def second_request(payload_bootstrap, payload_runner):
    """Run rs_reverse.js through Node, then update Cookie T/P back to the same session."""
    runtime_path = build_rs_reverse_runtime(payload_bootstrap, payload_runner)
    cookie_name, cookie_value, node_output = run_node_get_cookie(runtime_path)
    session.cookies.update({cookie_name: cookie_value})

    print("generated cookie ->", cookie_name, cookie_value[:32])
    print("session cookies ->", session.cookies.get_dict())
    return cookie_name, cookie_value, node_output


def home_check():
    response = session.get(TARGET_URL, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    print("home check ->", response.status_code, response.url)
    return response


def request_api():
    if not API_URL:
        return None

    method = API_METHOD.upper()
    headers = {**HEADERS, **API_HEADERS}
    kwargs = {"headers": headers, "timeout": REQUEST_TIMEOUT}
    if method == "GET":
        kwargs["params"] = API_PARAMS
    else:
        if API_JSON is not None:
            kwargs["json"] = API_JSON
        elif API_DATA is not None:
            kwargs["data"] = API_DATA
        elif API_PARAMS is not None:
            kwargs["data"] = API_PARAMS

    response = session.request(method, API_URL, **kwargs)
    print("api check ->", response.status_code, response.text[:300])
    return response


def main():
    payload_bootstrap, payload_runner = first_request()
    second_request(payload_bootstrap, payload_runner)
    home_check()
    request_api()


if __name__ == "__main__":
    main()
