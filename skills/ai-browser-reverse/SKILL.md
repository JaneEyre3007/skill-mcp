---
name: ai-browser-reverse
description: >-
  Firefox Reverse / frx-director / firefox-reverse-ai-mcp browser reverse workflow. Use when the user explicitly wants AI-driven browser reverse engineering through firefox-reverse-ai-mcp, frx-director-mcp, Firefox Reverse, or asks to choose between worker delegation and direct-drive browser engine tools. On activation, ask the user to choose the mode with the question tool unless the mode is already specified. Can coordinate with advanced reverse skills by full handoff or by loading their methodology while Firefox Reverse remains the execution engine. Do not trigger for WeChat miniapp debugging, pure AST deobfuscation, browser hook snippets only, Node/vm environment patching only, compact Python+iv8 scripts, or complete browser-free protocol collector implementation.
argument-hint: "<target URL or task> [mode: delegate|direct]"
---

# AI Browser Reverse

Use this skill to drive `firefox-reverse-ai-mcp`, the MCP bridge for the Firefox Reverse browser's built-in reverse-engineering engine.

The MCP supports two modes:

1. Delegate mode: the strong model acts as director, while a cheap browser-side worker model executes tools through `agent_start` / `agent_send`. This is the default for long, uncertain, or repetitive reverse work because it saves strong-model tokens.
2. Direct-drive mode: the strong model calls Firefox Reverse engine tools itself through `agent_tools` + `agent_call_tool`. This is faster when the strong model has a good method already, but every tool round costs strong-model tokens.

## Trigger Boundary

Use this skill when:

- the user explicitly mentions `firefox-reverse-ai-mcp`, `frx-director-mcp`, `frx-director`, Firefox Reverse, or `agent_call_tool`
- the user wants an AI-controlled browser reverse workflow and asks to choose between worker delegation and direct-drive tools
- the task is Web API sign/token/header/cookie/challenge analysis where Firefox Reverse should be the main browser engine
- the user wants the director loop: read worker conclusions, correct direction, and persist progress in the Firefox Reverse workspace

Do not use this skill when:

- the target is a WeChat miniapp / WMPF / AppService / WebView task -> use `wechat-miniapp-reverse`
- the user only wants a pasteable Console/Snippets hook script -> use `browser-hook-snippets`
- the user provides local browser JS and asks to make it run in Node.js/vm/jsdom -> use `env-patch`
- the user explicitly wants compact `Python + iv8 + requests` delivery -> use `iv8-web-reverse`
- the task is whole-file AST deobfuscation or pass design -> use `ast-deobfuscate`
- upstream evidence is already enough and the goal is a complete browser-free Python collector -> use `web-protocol-recovery`

If the user explicitly calls this skill but the task clearly belongs to a neighboring skill, state the mismatch briefly and hand off to the better skill instead of forcing Firefox Reverse into the workflow.

## Skill Cooperation And Handoff

This skill may coordinate with the advanced reverse skills under `.agents\skills`. Choose one cooperation style before deep tool use.

### Full Handoff

Use a full handoff when Firefox Reverse should not be the main execution engine for the next step. Call the target `skill` tool and follow that skill instead of continuing this workflow.

Full handoff targets:

- `wechat-miniapp-reverse`: WeChat miniapp, WMPF, AppService, WebView, `127.0.0.1:62000`
- `browser-hook-snippets`: user only wants pasteable Console/Snippets hooks
- `ast-deobfuscate`: whole-file AST deobfuscation, string array/control-flow recovery, pass design
- `env-patch`: known browser JS entry must run in Node.js/vm/jsdom/proxy runner
- `iv8-web-reverse`: compact `Python + iv8 + requests` script or iv8 challenge/cookie/suffix replay
- `web-protocol-recovery`: final goal is a complete browser-free Python collector or protocol replay from enough upstream evidence

Full handoff message shape:

```text
这个阶段更适合交给 <skill-name>：原因是 <one sentence>。
我会携带当前证据：目标 URL / 请求样本 / 参数名 / 已知调用栈 / 工作目录。
```

### Methodology Handoff

Use methodology handoff when Firefox Reverse remains the browser engine, but another skill contains better tactics for the target family.

Pattern:

1. Call the relevant `skill` tool to load its method.
2. Extract only the applicable checklist, triage rules, and validation discipline.
3. Return to this skill's selected mode and execute through `firefox-reverse-ai-mcp`.
4. Do not run two browser MCP stacks at the same time unless explicitly needed; prefer Firefox Reverse as the active browser when this skill remains in charge.

Useful methodology sources:

- `camoufox-js-reverse`: Web API sign/token/header/cookie entry tracing, JSVMP triage, browser-environment evidence discipline
- `web-protocol-recovery`: final collector structure, artifact discipline, protocol replay validation, handoff after enough evidence
- `env-patch`: environment patch strategy once a browser JS entry is found and the next goal is local Node/vm reproduction
- `browser-hook-snippets`: quick hook patterns when Direct-drive needs a small page-level observation script
- `ast-deobfuscate`: source cleanup only after dynamic tracing identifies a local bundle worth deobfuscating

Do not blindly merge conflicting instructions. If the loaded skill says to use a different browser stack, translate the method into Firefox Reverse tool names when possible. If translation would weaken the task, use Full Handoff.

### Delegate-Mode Transfer

In Delegate mode, the strong model should not paste huge skill documents into worker guidance. Compress the relevant experience into precise next actions:

```text
按 <skill-name> 的方法论执行，但只做这 3 步：
1. <evidence-producing action using Firefox Reverse tool names>
2. <fixed-input or request comparison>
3. <minimal implementation or blocker report>
回报只包含：证据、结论、下一步。
```

Always call `firefox-reverse-ai-mcp_agent_tools` if the needed Firefox Reverse tool name is uncertain. Mention real tool names in `agent_send` guidance instead of generic browser actions.

### Return Payload

When returning from another skill or switching back into this skill, carry a small evidence packet:

```text
mode: delegate | direct-drive | handoff-return
sourceSkill: <skill-name or none>
targetUrl: <page URL>
apiUrl: <target request URL>
targetFields: <sign/header/cookie/body fields>
workspace: <worker workspace or output path>
evidence: <request ids, samples, traces, scripts, fixed input-output pairs>
nextStep: <one concrete action>
```

If the evidence packet already satisfies `web-protocol-recovery`'s implementation threshold, hand off there for the final browser-free collector instead of continuing browser tracing.

## Mode Selection

At the start of every activation, determine the mode before using Firefox Reverse tools.

If the user already specified a mode, do not ask again:

- Delegate mode signals: `delegate`, `worker`, `assist`, `省 token`, `省钱`, `委派`, `模式一`, `让低模型跑`, `agent_start`, `agent_send`
- Direct-drive mode signals: `direct`, `direct-drive`, `raw`, `直驱`, `亲自调工具`, `模式二`, `agent_call_tool`, `agent_tools`

If the mode is not specified, call the `question` tool immediately so the user can choose with the UI keyboard controls:

```text
question({
  questions: [{
    header: "选择模式",
    question: "这次用哪种 Firefox Reverse 驱动模式？",
    multiple: false,
    options: [
      {
        label: "委派模式",
        description: "推荐用于长任务。强模型只审结论和纠方向，便宜 worker 在浏览器里执行工具，token 成本低。"
      },
      {
        label: "直驱模式",
        description: "强模型亲自调用浏览器引擎工具，速度和控制力更好，但每个工具回合都消耗强模型 token。"
      }
    ]
  }]
})
```

Map the selected labels as follows:

- `委派模式` -> Delegate mode
- `直驱模式` -> Direct-drive mode

If the user cancels or gives a custom answer, infer the closest mode from the answer. If it is still ambiguous, ask one short clarification.

## Shared Preflight

After mode selection, call `firefox-reverse-ai-mcp_frx_status` first.

Read the returned fields and `note` before continuing:

- If `bridgeConnected=false`, run the browser bootstrap flow below before telling the user to start anything manually.
- If Delegate mode and `hasKey=false`, tell the user to configure a cheap worker model key in the Firefox Reverse Agent settings, then stop until it is ready.
- If Direct-drive mode and `hasKey=false`, continue if the bridge is connected because direct-drive does not require the worker model key.
- Prefer fast or standard worker models for Delegate mode, such as `deepseek-v4-flash`, `deepseek-chat`, `qwen-turbo`, or GLM. Avoid reasoning/pro models for long tool loops because they often drift into plain-text planning without using tools.

Do not start browser work before this preflight passes for the selected mode.

### Browser Bootstrap Flow

Use this flow when `frx_status` reports `bridgeConnected=false` or `connect ECONNREFUSED 127.0.0.1:2828`.

The startup flow uses two config files, with browser-side config as the authority:

- Browser connection config: `firefox-reverse-ai-mcp\browser-connection\config.json` inside the Firefox Reverse root directory. This is the primary config to read when it can be located.
- Skill index: `config/browser-root.json` under this skill directory. This is only an index for locating the Firefox Reverse root on later activations, so the browser connection config can be read. It is not the authority when the browser-side config exists.

Use browser-config-first startup. Always run the bootstrap script with no `-RootPath` before asking the user for a path. The script first uses `config/browser-root.json` only to locate `<root>\firefox-reverse-ai-mcp\browser-connection\config.json`; when that browser-side config exists, its `rootPath` wins. Then the script refreshes both config files and starts Firefox Reverse with Marionette.

```text
bash({
  command: "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\\Users\\poppies\\.agents\\skills\\ai-browser-reverse\\scripts\\frx_browser_bootstrap.ps1\"",
  timeout: 30000
})
```

Then call `firefox-reverse-ai-mcp_frx_status` again. If it is ready, continue the selected mode. If the bootstrap output includes `rootSource:"browserConnection"`, mention that `firefox-reverse-ai-mcp\browser-connection\config.json` was used. If it includes `rootSource:"skillIndex"`, mention that the skill index was used only because the browser-side config was not found.

If the bootstrap output says `needRootPath=true`, ask the user for the Firefox Reverse browser root directory with `question`. This should only happen when no browser-side config can be located, configs are invalid, or the configured root does not contain `firefox.exe`. Use the UI custom answer for the path:

```text
question({
  questions: [{
    header: "浏览器路径",
    question: "请输入 Firefox Reverse 浏览器根目录，例如 D:\\develop_software\\FireFox Reverse AI",
    multiple: false,
    options: [
      {
        label: "稍后配置",
        description: "暂不启动浏览器，只返回需要执行的启动命令。"
      }
    ]
  }]
})
```

If the user provides a path, run bootstrap with `-RootPath`. The script validates that `<RootPath>\firefox.exe` exists, saves the path to both `firefox-reverse-ai-mcp\browser-connection\config.json` and `config/browser-root.json`, and then starts Firefox Reverse:

```text
bash({
  command: "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\\Users\\poppies\\.agents\\skills\\ai-browser-reverse\\scripts\\frx_browser_bootstrap.ps1\" -RootPath \"<user browser root>\"",
  timeout: 30000
})
```

After that, call `firefox-reverse-ai-mcp_frx_status` again.

If `frx_status` is still not ready after the script starts Firefox:

- If Firefox is already running without Marionette, ask the user to close all Firefox Reverse windows and rerun the bootstrap.
- If `firefox.exe` was not found, ask for the root folder that directly contains `firefox.exe`.
- If Delegate mode reports `hasKey=false`, the browser is connected but the worker key is missing; do not keep relaunching the browser.

Do not invent a browser path. Only use the saved config or a user-provided path.

## Delegate Mode Workflow

Use Delegate mode for long reverse tasks, broad reconnaissance, repeated capture/compare cycles, and cases where worker token cost matters.

1. Collect the target contract if missing: site URL, target API URL, target parameter or cookie/header name, and expected final output.
2. Optionally call `firefox-reverse-ai-mcp_agent_tools` once to learn the browser-side tool names, then mention those names in worker guidance rather than guessing capabilities.
3. Start the worker with `firefox-reverse-ai-mcp_agent_start` using `assist: true` unless the user explicitly asked for fully automatic mode.
4. Put concrete task framing into `task`: target URL/API, suspected parameter, output goal, constraints, and the first 2-3 actions the worker should perform.
5. Wait with `firefox-reverse-ai-mcp_agent_wait_for_stop`. Use the default long timeout unless the user asked for a short probe. A timeout returning `phase:"running"` means the worker is still grinding, not that the route failed.
6. Read with `firefox-reverse-ai-mcp_agent_read` and inspect `driftHint`, `runlogTail`, `progress.md`, and `ledger.md` before trusting the worker's conclusion.
7. If the worker drifted, got idle-timeout, contradicted its logs, or moved toward a wrong route, call `firefox-reverse-ai-mcp_agent_runlog` if needed, then send a precise correction with `firefox-reverse-ai-mcp_agent_send`.
8. Keep guidance short and operational: specify the exact next steps, require evidence before the next branch, and restrict the report shape.
9. When the route is locked and only mechanical implementation remains, use `firefox-reverse-ai-mcp_agent_set_mode({mode:"auto"})` or send the next round with `assist:false`.
10. If the worker is actively going down a bad route and waiting would waste time, call `firefox-reverse-ai-mcp_agent_stop`, then `agent_send` with corrective guidance. Progress is persisted in the workspace.

Good `agent_send` guidance style:

```text
只做下面 3 步，不要扩展到字节码逆向：
1. 用 signer_trace 抓目标请求的真实签名入参和出参。
2. 用固定输入重复 3 次，确认变化字段和稳定字段。
3. 写一个最小 Node 验证脚本，只比对目标参数。
回报仅包含：抓到的样本表、下一步推荐、阻塞项。
```

Delegate mode completion requires one of these:

- verified signer/cookie/header reproduction with fixed input-output samples
- a runnable local script or clearly identified next skill handoff with artifacts
- a concrete external blocker such as login, CAPTCHA, missing target request, or unavailable browser bridge

## Direct-Drive Mode Workflow

Use Direct-drive mode when the route is clear, the strong model's own reverse methodology matters, or the user wants fast hands-on control of Firefox Reverse engine tools.

1. Call `firefox-reverse-ai-mcp_agent_tools` after `frx_status`. Do not call `agent_call_tool` from memory; tool names and parameters come from this catalog.
2. If any Delegate worker session is currently running, do not direct-drive concurrently. First use `agent_wait_for_stop` or `agent_stop` on the known `tid`.
3. Call exactly one browser tool at a time through `firefox-reverse-ai-mcp_agent_call_tool({name,args,workspaceRoot})`.
4. Treat the result as an envelope: inspect `ok`, `data`, and `error`. Browser-side dispatch validates unknown tools and missing parameters; a tool error is evidence for the next step, not a reason to guess.
5. Pass an explicit `workspaceRoot` when tools write files, run Node, or save traces. Keep all target artifacts under a dedicated workspace directory.
6. Prefer evidence-producing tools first: navigation, network capture, request details, initiator/call stack, signer trace, closure read, page eval, source/code search, JSVMP trace, Web API trace, WASM probe, and offline verification.
7. Use standard-algorithm checks and fixed-input comparisons before deep obfuscation work. Do not reverse JSVMP bytecode unless black-box tracing and environment replay are insufficient.
8. If the direct loop becomes repetitive or broad, ask before switching to Delegate mode. Delegate mode is often cheaper for grinding through source search, capture variants, and implementation polish.

Direct-drive completion requires visible artifacts: captured request IDs or samples, traced function evidence, fixed-input outputs, saved scripts, verification results, or a precise blocker.

## Code Landing Path

When analysis is complete enough to implement the reverse code, land the implementation under an `object` directory in the current terminal working directory.

Do not ask the user for a code path by default. Prepare the landing directory only after one of these is true:

- the target signer/cookie/header logic has fixed input-output samples
- the target request can be replayed manually with known missing pieces
- the worker has produced a recommended implementation route and enough artifacts
- Direct-drive tracing has identified the callable function, required environment, and validation method

Default rule:

- Use the current terminal working directory as the parent.
- Create or reuse `object\` under that directory.
- Treat that `object\` directory as the landing root for this reverse task.
- In the same task, reuse the returned `outputPath`; do not prepare or ask for another landing directory unless the user explicitly changes it.
- Do not persist this as a global or cross-task default. A later task uses that later task's current terminal working directory.

Prepare the landing directory with:

```text
bash({
  command: "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\\Users\\poppies\\.agents\\skills\\ai-browser-reverse\\scripts\\prepare_output_dir.ps1\"",
  timeout: 30000
})
```

If the user explicitly provides a different output path for the current task, honor it with:

```text
bash({
  command: "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\\Users\\poppies\\.agents\\skills\\ai-browser-reverse\\scripts\\prepare_output_dir.ps1\" -OutputPath \"<user output path>\"",
  timeout: 30000
})
```

Use the returned `outputPath` as the root for final deliverables in this task. Put implementation code, tests, replay samples, and a short README there. Keep large raw browser artifacts in `js_reverse_cache\` or `artifacts\` under that root, not in the source root.

Recommended minimal layout:

- `README.md`: target, mode used, how to run, current limitations
- `src\` or `collector\`: final implementation code
- `tests\` or `samples\`: fixed-input validation and replay samples
- `js_reverse_cache\`: captured scripts, sanitized request samples, trace outputs

Implementation rules:

- Write code only after `prepare_output_dir.ps1` returns `ok=true`.
- Use the smallest runnable project shape that fits the target. Do not create a large framework by default.
- Include a local verification command when possible, such as `node ...`, `npm test`, or `python ...`.
- If live replay needs account-bound cookies, Authorization, CAPTCHA, paid data, or state-changing requests, pause for confirmation before running it.
- If Delegate mode was used, transfer the worker's useful artifacts and conclusions into the landing project instead of leaving the user to inspect the worker workspace.

## Switching Modes

The two modes share the same browser tab, hooks, traces, and workspace state.

- Do not run `agent_call_tool` while a Delegate worker turn is running; the MCP will refuse it and the shared state can become confusing.
- To switch Delegate -> Direct-drive, wait for the worker to settle or stop it first.
- To switch Direct-drive -> Delegate, start a fresh `agent_start` with a task that summarizes the direct evidence already gathered.
- If the user changes modes mid-task, preserve the latest `tid`, workspace path, request IDs, and artifact paths in the handoff message.

## Safety And Scope

Pause and ask for confirmation before:

- using account-bound cookies, Authorization headers, paid account data, or private tokens in live requests
- submitting forms, orders, payments, mutations, messages, verifier answers, or anything that changes server state
- increasing from one proof request to pagination, concurrency, or high-volume collection
- printing or saving full raw secrets; prefer masked values, hashes, lengths, and minimal samples

No pause is needed for local static analysis, network metadata inspection, fixed-input offline signer tests, or sanitized sample comparison.

## Final Response

End with the mode used, the current workspace path or `tid` when available, the code landing path when implementation was written, the verified artifacts, and the next practical step. If verification could not run, state the blocker directly.

Keep final answers concise. Do not paste huge logs; summarize the decisive lines and point to saved artifact paths.
