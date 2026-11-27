# TP01｜蓝图资讯版

> 编号 TP01 · 模板版本 v1.1 · 状态 active  
> 深色工程蓝图底 + 黄绿强调 + 底部纸张信息卡。

## 1. 适用

- 产业资讯、展会/发布会、公告、数据与截图证据。
- 9–60 秒中短资讯片，无口播或弱口播。
- 需要“现场简报感/工程档案感”的内容。

不适合：长口播、人物故事、情绪铺垫、复杂一屏多图。

## 2. 画布

| 项目 | 规格 |
|---|---|
| 画布 | 1080×1920 |
| 帧率 | 30fps |
| 码率 | 目标 12Mbps |
| 音频 | AAC 192k |
| 封面 | 3:4，1080×1440 |

## 3. 版式坐标

| 模块 | 位置 / 尺寸 |
|---|---|
| 顶部压暗 | 高 660px，深色到透明渐变 |
| 左上编号块 | `left 56, top 52`，42×30，黄底黑字 |
| 左上栏目 | 字号 23，字重 800，字距 2.6 |
| 左上辅助标签 | 字号 18，黄色，字距 2.2 |
| 右上日期 | 字号 17，右对齐 |
| 标题竖条 | `left 54, top 254`，8×292，黄色 |
| 标题区 | `left 86, top 240`，宽 914，字号 79，行高 1.12，字重 900 |
| 标题下横线 | `left 88, top 542`，146×4，黄色 |
| 底部信息卡 | 左右 56，`bottom 300`（即 `top 1282`），高 338，圆角 26 |
| 信息卡顶条 | 高 7px，黄色 |
| 时间轴 | 卡片内顶部，5 段等分 |
| 来源列 | 宽 238，来源名 27px，细节 17px |
| 主结论 | 38–44px，字重 900，行高 1.13 |
| 正文 | 25px，行高 1.32，字重 500 |
| 数据 | 48–66px，字重 900，单位 22px |

## 4. 色彩与字体

| 角色 | 色值 |
|---|---|
| 墨色 | `#0B0F14` |
| 纸张 | `#F2EEE3` |
| 主黄 | `#FFC400` |
| 辅助绿 | `#B7E34C` |
| 钢灰 | `#7C8794` |
| 深底 | `#080B0F` |

- 中文：`Noto Sans CJK SC` / `Source Han Sans SC`，标题 900。
- 英文/时间码：`DejaVu Sans Mono` / `Noto Sans Mono`。
- 标题白色，关键词可用黄/绿；信息卡深色字，重点数字用黄或深黄。

## 5. 镜头与节奏

- 不套固定 3 秒；按信息点、证据切换和卡点切，单镜可 1.8–8 秒。
- 样例工程 34.0 秒 / 1020 帧，8 个 visual，约 5 / 4 / 3 / 8 / 8 / 1.8 / 2 / 2.2 秒。
- 结尾卡约 2.2 秒。
- 新片默认硬切；样例 v3 仍是每镜 7 帧淡入/淡出，属于旧逻辑，不要照抄。
- 连续同质镜头不必都加转场；章节/时空跳点再上。

## 6. 信息层

- 片内标题固定；跨片按新脚本替换。
- 底部信息卡按 `cardIndex` 切换，一张卡对应一组镜头。
- 卡片字段：序号/栏目、主结论、正文、数据、单位、数据标签、来源、来源细节。
- 来源列常驻。
- 顶部 chrome 的编号、栏目、日期按项目替换，不保留样例品牌。

## 7. 声音

- BGM 用抖音热门曲，不用 AI 生成；增益约 0.20。
- 音效只在段落起点、数据卡、结尾等关键节点；不逐镜加，不硬套密度。
- 无口播时 BGM 可略高；有弱口播时人声清晰优先。

## 8. 数据结构

```ts
type Card = {
  index: number;
  kicker: string;
  headline: string;
  body: string;
  stat: string;
  statUnit: string;
  statLabel: string;
  source: string;
  sourceDetail: string;
};

type Visual = {
  id: string;
  start: number;
  duration: number;
  kind: "image" | "product" | "video" | "end";
  src?: string;
  cardIndex: number;
  position?: string;
  productWidth?: number;
  productTop?: number;
  ghost?: string;
  ghostX?: number;
  startFrom?: number;
  brightness?: number;
  zoomOut?: boolean;
};
```

`cardStartFrames` 控制信息卡切换；`END_START` 控制结尾卡起点。

## 9. 抖音注意

- v3 已把底部信息卡放到 `bottom 300`，避免被抖音底部 UI 遮挡；关键结论/数据仍建议放上半区。
- 右侧 120px 不放关键数据/来源；顶部 120px 不放关键标题。

## 10. 样片与源工程

- 完整样片：`out/master_v3_final.mp4`，34.0 秒 / 1020 帧 / 1080×1920 / 30fps / 11.2Mbps，QC PASS；CDN `https://aka.doubaocdn.com/s/xwStY1ws79`。
- 预览帧：`previewCdn`：`https://aka.doubaocdn.com/s/GmGsj9ELU5`（v3 第 30 帧；405×720）。
- 源工程：`20261126_01_bauma_green_giant`，主要文件 `src/NewsVideo.tsx`、`src/data.ts`、`src/Root.tsx`。
- 样例 v3 仍保留每镜 7 帧淡入/淡出（旧版逻辑）；按你的偏好，新片改为硬切为主，只在章节/时空跳点用 7–12 帧 fade/wipe/push，不逐切点加。
