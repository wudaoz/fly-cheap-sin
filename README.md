# 飞哪儿便宜（新加坡出发）

我自己用的实例：新加坡（SIN）出发、SGD 计价，每天 08:40 新加坡时间由 GitHub Actions 采一次 Google Flights 价格，另外盯着 2027 春节 2/6 → 2/11 的广州往返。页面在 GitHub Pages 上，手机浏览器打开就能看。

代码和通用模板仓库 [fly-cheap](https://github.com/<你的用户名>/fly-cheap) 完全一样，只有 `settings.json` 不同（出发地、固定航线、心理价位）。设置项说明、提醒规则、数据格式都看模板仓库的 README。

部署：仓库 Secrets 里加 `SERPAPI_KEY`；Settings → Pages → Source 选 GitHub Actions；Actions → collect → Run workflow 跑第一次。

每天 7 次 SerpApi 请求（5 个月份 + 欧洲 + 广州），一个月约 210 次，在免费 250 次额度内——所以这个 key 不能再同时给另一套实例用。
