# Search Sources

Use this file as a source map. Pick sources based on the target language, domain, protection clues, and whether the user needs current code or historical context.

## Priority Order

1. Search engines: broad discovery across indexed blogs, forums, mirrors, and old posts.
2. Code search: repositories, gists, package registries, and copied snippets.
3. Reverse/security communities: targeted discussions, tooling notes, and case studies.
4. Developer/blog platforms: writeups, tutorials, and repost trails.
5. Archive and cache sources: deleted posts, old bundles, old package versions, and stale repos.
6. Video/social sources: conference talks, Bilibili/YouTube walkthroughs, X/Twitter threads, and Telegram/Discord/Reddit references when available.

## Source Weight Guide

Use these weights as a starting point, then adjust with directness, freshness, and technical evidence:

| Source Class | Weight | Best Use |
| --- | ---: | --- |
| Current target code, live bundle, official SDK, commit history | 10 | Confirm exact implementation shape. |
| GitHub/GitLab repository with issues, commits, tests, or traces | 9 | Find code, forks, breakage reports, and updated implementations. |
| Reverse/security forum thread with packet screenshots or call stacks | 8 | Learn hands-on analysis details and corrections. |
| Security blog or detailed technical writeup | 7 | Understand derivation and terminology. |
| Maintained package registry project | 7 | Locate reusable clients and version history. |
| Developer blog tutorial with code | 5 | Expand vocabulary and collect old implementation clues. |
| Video/social walkthrough | 4 | Discover leads, then verify elsewhere. |
| Search summary, SEO repost, uncited snippet | 2 | Use only for weak clue expansion. |

## Domestic Chinese Sources

- General search: Baidu, Sogou, 360 Search, Bing China, Google when available.
- Code/search: GitHub, Gitee, GitCode, CSDN Code, Sourcegraph, grep.app.
- Reverse/security forums: 吾爱破解, 看雪论坛, 先知社区, FreeBuf, 安全客, T00ls, 合天网安实验室, 奇安信攻防社区.
- Blog/dev platforms: CSDN, 博客园, 掘金, 知乎, 腾讯云开发者社区, 阿里云开发者社区, SegmentFault, 简书.
- Video/course hints: Bilibili, YouTube, 小红书/抖音 only for pointer discovery, then verify elsewhere.
- Package mirrors: npm, PyPI, Maven, crates.io, NuGet, Go package index, plus Chinese mirrors when search engines surface them.

## International Sources

- General search: Google, Bing, DuckDuckGo, Brave Search, Yandex.
- Code search: GitHub Code Search, GitHub issues/discussions, GitHub Gist, GitLab, Bitbucket, Sourcegraph, grep.app, searchcode.
- Developer communities: Stack Overflow, Stack Exchange Security, Reddit communities for reverse engineering, web scraping, and browser automation.
- Security research: Habr, Medium, DEV.to, HackerNoon, personal blogs, conference slides, vendor blogs, bug-bounty writeups.
- Package registries: npm, PyPI, Maven Central, crates.io, RubyGems, NuGet, Go package index.
- Archives: Wayback Machine, archive.today, cached search results, old package versions, old GitHub commits/tags/releases.

## Source Selection Heuristics

- For Chinese commercial websites, start with Chinese search engines, CSDN, 博客园, 掘金, 吾爱破解, 看雪, 先知, FreeBuf, 安全客, GitHub, and Gitee.
- For global SaaS or ecommerce sites, start with Google/Bing, GitHub, GitLab, Sourcegraph, Reddit, Stack Overflow, Medium, and package registries.
- For named protection vendors, search both the vendor name and observable markers such as cookie names, JS globals, challenge paths, and error strings.
- For mobile-app targets, include app package names, APK filenames, SDK names, and repository searches for decompiled strings.
- For WASM or heavy obfuscation, search exact JS/WASM filenames, exported function names, magic constants, and stack traces.

## Evidence Quality

- Strong evidence: exact domain/API/parameter match, runnable code, packet screenshots, HAR snippets, stack traces, or comments from multiple independent authors.
- Medium evidence: same app family, same vendor/protection, or same library with similar parameter names.
- Weak evidence: reposts without attribution, old snippets with no target proof, short SEO posts, or content that hides the key function behind paid downloads.

## Coverage Notes

- Some high-signal forums require login, reputation, invitation, or paid access. Record them as blind spots instead of pretending they were searched.
- Search results differ by region, language, account state, and date. Prefer multiple engines for important targets.
- GitHub forks and mirrored posts are often copies. Trace back to the earliest commit or original author before trusting code.
