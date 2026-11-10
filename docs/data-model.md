# 数据文件

所有数据都在 `data/` 下，一个文档一个 JSON 文件：`data/<collection>/<doc_id>.json`。`build_bundle.py` 把它们合并成 `data/bundle.json` 给页面用（`explore` 只保留最近 120 次运行，其余全量）。

`RUN` 是本次采集的新加坡时间戳（`YYYY-MM-DDTHHMM`，如 `2026-11-10T1112`），`AT` 是对应的 UTC ISO 时间；同一次运行写出的所有文档这两个字段相同，并都带 `origin`（出发地代码）和 `currency`。价格都是该币种、1 人往返经济舱的整数。

## `explore/<RUN>_<YYYY-MM>.json` 和 `explore/<RUN>_europe.json`

Google Travel Explore 的结果，一次运行每个月份一个文档，欧洲另有一个。

```json
{"run": "2026-11-10T1112", "at": "2026-11-10T03:12:34Z",
 "month": "2027-01", "label": "1-week trip in January", "source": "serpapi-explore",
 "rows": [["Kuala Lumpur", "Jan 7 – 13, 2027", 121, "Nonstop", "1 hr 5 min", "AirAsia", "2027-01-07", "2027-01-13", "KUL"]]}
```

`rows` 每行：`[城市名, 日期文本, 价格, 中转, 时长, 航司, 出发日, 返程日, 目的地机场代码]`。欧洲文档的 `month` 为 `"next-6-months"`，并多一个 `"region": "Europe"`，页面和 `alerts.py` 靠它区分。

## `grid/<RUN>_<DEST>.json`

固定日期航线（`settings.json` 的 `fixedRoute`）的 Google Flights 报价；没配置就没有这个集合。

```json
{"run": "…", "at": "…", "dest": "CAN", "window": "CNY 2027 (Feb 6)",
 "insight": "Prices are currently typical (typical SGD 330–590)", "source": "serpapi-flights",
 "cells": [["Feb 6", "Feb 11", 423]], "priceHistory": [[1762000000, 430]]}
```

`cells` 每项 `[出发日文本, 返程日文本, 价格]`；页面按网格渲染，多个 cells 也支持。`priceHistory` 来自 SerpApi 的 `price_insights.price_history`，可能为 `null`。

## `compare/<RUN>.json`

本次运行各目的地的最低价汇总：`collect.py` 的 `DEST` 表里最便宜的 9 个目的地，加固定航线。`alerts.py` 的规则 (a)(b)(c) 以它为输入，页面的「现在最值得入手」也从这里取日期。

```json
{"run": "…", "at": "…", "source": "serpapi",
 "items": [{"code": "KUL", "city": "Kuala Lumpur", "out": "2027-01-07", "back": "2027-01-13",
            "google": 121, "trip": null, "agoda": null, "tripAlert": null}]}
```

`trip / agoda / tripAlert` 是预留字段（曾经对比过 Trip.com / Agoda），当前恒为 `null`；页面和规则都会取 `google / trip / agoda` 的最小非空值，所以接入其他数据源时填上即可。

## `alerts/<RUN>_<CODE>.json`

`alerts.py` 写出的提醒。页面列最近 15 条；去重时取每个 code 最近一条的 `price`。

```json
{"at": "…", "run": "…", "code": "MNL", "price": 190, "src": "Google",
 "text": "马尼拉 2/8→2/16 往返 SGD 190（Google），低于心理价位 210，创历史新低"}
```

## `runs/<RUN>.json`

每次运行一条，页面用它显示「最近采集」。

```json
{"run": "…", "at": "…", "status": "ok | partial", "sources": ["google(serpapi)"],
 "note": "4 months + Europe 43 cities + CAN via SerpApi; Trip/Agoda not collected"}
```

`status` 为 `partial` 时 `note` 列出跳过的步骤（如 `explore 2027-03 empty`、`CAN flights failed`）。

## `settings.json`（仓库根目录）

字段说明见 README「改出发地和其他设置」。`build_bundle.py` 会把整个文件放进 `bundle.json` 的 `settings` 字段，页面据此显示出发地、币种、固定航线版块和每行的心理价位。
