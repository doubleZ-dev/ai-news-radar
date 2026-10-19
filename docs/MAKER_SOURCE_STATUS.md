# Maker Radar Source Status

Last live validation: 2026-10-19. A source is marked healthy only after a real
HTTP response can be parsed into the Maker Radar schema. Zero recent items is a
valid healthy result when the upstream feed itself contains entries.

## Integrated and healthy

| Source | Path | Notes |
| --- | --- | --- |
| GitHub Trending | Public HTML | Maker-keyword filtered; observation time is not a repository publication time. |
| Hackaday | Public RSS | 72-hour window. |
| Hacker News | Public Algolia API | Focused maker queries with discussion evidence. |
| 3D Printing Industry | Public RSS | 72-hour window. |
| Reddit Maker Communities | Public combined RSS | Covers Arduino, ESP32, Robotics, 3Dprinting, and DIYElectronics in one request to avoid 429 bursts. RSS has no reliable votes/comments, so heat stays unknown. |
| Product Hunt | Official Atom feed | Reuses the upstream project's timestamp-safe parser and keeps maker-related products only. |
| Hugging Face Daily Papers | Public JSON endpoint | Keeps recent maker-adjacent research and preserves upvotes, comments, code, and project links when present. |
| X · Follow Builders | Public GitHub-generated JSON | Curated X snapshot with original post links and engagement metrics; this is not full-platform X search. |

## Probed but intentionally skipped

| Source | Observed result | Why it is not reported as covered |
| --- | --- | --- |
| YouTube · Stuff Made Here | Alternated between HTTP 200 and 404 | Repeated validation did not prove the public channel feed stable. |
| YouTube · Teaching Tech | Alternated between HTTP 200 and 404 | Repeated validation did not prove the public channel feed stable. |
| YouTube · DIY Machines | Alternated between HTTP 200 and 404 | Repeated validation did not prove the public channel feed stable. |
| arXiv | HTTP 429 | A polite retry/caching strategy has not yet proven stable. |
| Hackster | Candidate feed returned HTTP 404 | No stable official feed has been verified. |
| Printables | Candidate feed/page returned HTTP 403 | No stable public endpoint has been verified. |
| MakerWorld | Direct page returned HTTP 403 | No stable public endpoint has been verified. |
| Bilibili | Public video search returned HTTP 412 | No stable official feed or authenticated path is configured. |
| Xiaohongshu | No local TikHub API key | The existing credentialed adapter cannot run, and no stable unauthenticated endpoint is available. |
| Douyin | No local TikHub API key | The existing credentialed adapter cannot run, and no stable unauthenticated endpoint is available. |
| TikTok | No stable public search/feed | No locally authorized API provider is configured. |
| WeChat Official Accounts | Candidate aggregator returned HTTP 403 | No explicit account/feed allowlist is configured. |

The skipped entries remain in `config/maker-sources.json` with
`enabled: false`. They appear in source health and `info_gaps`, but never
produce fabricated discoveries.
