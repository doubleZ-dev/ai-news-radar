# Maker Radar Source Status

Last live validation: 2026-10-19. The full run produced 95 candidates from 22
healthy sources, with 11 explicitly skipped and zero runtime failures. A source
is marked healthy only after a real HTTP response can be parsed into the Maker
Radar schema. Zero recent items is a valid healthy result when the upstream feed
itself contains entries.

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
| YouTube · Stuff Made Here | Official channel Atom | Seven-day upload window; zero recent uploads is reported as healthy, not fabricated coverage. |
| YouTube · Teaching Tech | Official channel Atom | Uses upload time and preserves public view counts as heat evidence. |
| YouTube · DIY Machines | Official channel Atom | Uses upload time and preserves public view counts as heat evidence. |
| Arduino Blog | Official RSS | Recent embedded projects, tutorials, and product ideas. |
| Adafruit Blog | Official RSS | Recent electronics, fabrication, and community builds. |
| Raspberry Pi News | Official RSS | Recent Raspberry Pi projects and ecosystem updates. |
| SparkFun News | Official Atom | Uses the feed explicitly advertised by the SparkFun news homepage. |
| Make: Magazine | Official RSS | Broad maker projects, events, and open-hardware signals with a seven-day window. |
| Prusa Blog | Official RSS | Stable 3D-printing materials, process, and product coverage. |
| Bambu Lab Blog | Official RSS | Stable 3D-printing project and ecosystem coverage. |
| CNX Software | Official RSS | Embedded hardware and new-product signals filtered for maker relevance. |
| Seeed Studio Blog | Official RSS | Embedded, sensor, robotics, and maker-project coverage. |
| arXiv Robotics | Official category RSS | Replaces the rate-limited query API; maker-keyword filtered and capped at ten. |
| Hackster | Official projects Atom | Recent community hardware projects with original project links. |

## Probed but intentionally skipped

| Source | Observed result | Why it is not reported as covered |
| --- | --- | --- |
| Printables | Candidate feed/page returned HTTP 403 | No stable public endpoint has been verified. |
| MakerWorld | Direct page returned HTTP 403 | No stable public endpoint has been verified. |
| Bilibili | Public video search returned HTTP 412 | No stable official feed or authenticated path is configured. |
| Xiaohongshu | No local TikHub API key | The existing credentialed adapter cannot run, and no stable unauthenticated endpoint is available. |
| Douyin | No local TikHub API key | The existing credentialed adapter cannot run, and no stable unauthenticated endpoint is available. |
| TikTok | No stable public search/feed | No locally authorized API provider is configured. |
| WeChat Official Accounts | Candidate aggregator returned HTTP 403 | No explicit account/feed allowlist is configured. |
| Crowd Supply | Candidate feeds returned HTTP 404 | The public homepage exposed no RSS/Atom link. |
| Kickstarter · Technology | TLS failure and HTTP 403 challenge | No stable unauthenticated discovery path was verified. |
| Instructables | Candidate feed redirected to login | The response was HTML, not RSS/Atom. |
| Thingiverse | HTTP 404 with inconsistent XML body | Stable API credentials are not configured. |

The skipped entries remain in `config/maker-sources.json` with
`enabled: false`. They appear in source health and `info_gaps`, but never
produce fabricated discoveries.

YouTube's upstream channel endpoint has previously shown intermittent 404s. The
collector performs two small source-specific retries, then reports a real
failure if the feed remains unavailable. It never substitutes stale items or
marks a failed request healthy.
