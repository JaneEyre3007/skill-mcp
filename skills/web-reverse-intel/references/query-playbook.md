# Query Playbook

Use this playbook to expand target names into concrete search queries.

## Core Terms

Chinese terms:

- `JS逆向`, `爬虫逆向`, `参数加密`, `签名参数`, `加密参数`, `接口签名`, `反爬`, `补环境`, `扣代码`, `webpack`, `wasm`, `AST还原`, `混淆还原`, `验证码`, `滑块`, `风控`, `动态cookie`

English terms:

- `reverse engineering`, `web scraping`, `signature`, `sign parameter`, `request signing`, `anti bot`, `challenge`, `token generation`, `headers`, `cookie`, `obfuscation`, `webpack`, `wasm`, `browser environment`, `fingerprint`

## Query Families

Use each family with target aliases, domain fragments, API paths, and parameter names.

- Exact domain: `"{domain}" "sign"`, `"{domain}" "js逆向"`, `"{domain}" "爬虫逆向"`
- Brand alias: `"{brand}" "参数加密"`, `"{brand}" "signature"`, `"{brand}" "anti bot"`
- API path: `"{api_path}"`, `"{api_path}" "sign"`, `"{api_path}" "headers"`
- Parameter/header: `"{param}" "{brand}"`, `"{param}" "逆向"`, `"{param}" "web scraping"`
- JS bundle: `"{bundle_name}"`, `"{bundle_name}" "webpack"`, `"{bundle_name}" "wasm"`
- Vendor marker: `"{vendor}" "{brand}"`, `"{cookie_name}" "{domain}"`, `"{global_name}" "challenge"`
- Code search: `"{domain}" language:JavaScript`, `"{param}" "function"`, `"{api_path}" "requests"`
- Historical: `"{domain}" "2024" "逆向"`, `"{brand}" "old version"`, `"{package_name}" "release"`

## Chinese Site Operators

- `site:52pojie.cn "{brand}" "逆向"`
- `site:kanxue.com "{brand}" "加密"`
- `site:xz.aliyun.com "{param}" "反爬"`
- `site:freebuf.com "{vendor}" "{cookie_name}"`
- `site:anquanke.com "{brand}" "JS逆向"`
- `site:blog.csdn.net "{domain}" "sign"`
- `site:cnblogs.com "{brand}" "爬虫逆向"`
- `site:juejin.cn "{param}" "补环境"`
- `site:zhihu.com "{brand}" "逆向"`
- `site:bilibili.com "{brand}" "JS逆向"`

## International Site Operators

- `site:github.com "{domain}" "{param}"`
- `site:gist.github.com "{param}" "{brand}"`
- `site:gitlab.com "{domain}" "signature"`
- `site:stackoverflow.com "{param}" "web scraping"`
- `site:reddit.com "{brand}" "reverse engineering"`
- `site:medium.com "{brand}" "signature"`
- `site:dev.to "{domain}" "scraping"`
- `site:habr.com "{vendor}" "{cookie_name}"`
- `site:npmjs.com "{brand}"`, `site:pypi.org "{brand}"`

## Query Tactics

- Quote exact strings for parameters, endpoint paths, error strings, cookie names, and JS globals.
- Search both `domain.com` and bare brand/app aliases; many authors omit the domain.
- Remove dots and separators from parameter names when results are thin.
- Translate Chinese target names to pinyin, English names, and app-store names.
- Search old names and acquired-company names when a platform has rebranded.
- Search package registries for brand names plus `sign`, `api`, `spider`, `crawler`, `scraper`, or `sdk`.
- Search issues/discussions as well as code; broken repos often contain useful comments.

## Reporting Queries

Do not dump every low-signal query. Report representative query families and the sources where they produced meaningful hits.
