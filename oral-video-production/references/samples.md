# 样片与源工程

## TP01｜蓝图资讯版

| 项目 | 内容 |
|---|---|
| 完整样片 | `/home/user/Doubao/chats/38455869952911874/20261126_01_bauma_green_giant/out/master_v3_final.mp4` |
| 完整样片 CDN | `https://aka.doubaocdn.com/s/xwStY1ws79` |
| 预览 CDN | `https://aka.doubaocdn.com/s/GmGsj9ELU5` |
| 规格 | 34.0s / 1020 帧 / 1080×1920 / 30fps / H.264 11.2Mbps / AAC 193k |
| 结构 | 8 个 visual；5 个音效；4 处 7 帧淡入/淡出；2 个素材内重点提示 |
| 技术 QC | `qc_video.py` PASS；无黑帧；音量 mean -18.0dB / max -4.4dB |
| 源工程 | `/home/user/Doubao/chats/38455869952911874/20261126_01_bauma_green_giant` |
| 主要文件 | `src/NewsVideo.tsx`、`src/data.ts`、`src/Root.tsx` |
| 预览 | `previewCdn`：`https://aka.doubaocdn.com/s/GmGsj9ELU5`（v3 第 30 帧，405×720） |
| 已知差异 | 样例 v3 仍是每镜 7 帧淡入/淡出；新片按偏好改为硬切为主，只在章节/时空跳点加转场。 |

## TP02｜红米口播版

| 项目 | 内容 |
|---|---|
| 完整样片 | `/home/user/Doubao/chats/38456561376081154/ep05/remotion/out/05_一百年_中国从求人变成被求_v2.mp4` |
| 完整样片 CDN | `https://aka.doubaocdn.com/s/YYp26D6jRG` |
| v1 CDN | `https://aka.doubaocdn.com/s/cF4UbGHR17` |
| 规格 | 33.6s / 1008 帧 / 1080×1920 / 30fps / H.264 12.4Mbps / AAC 189k |
| 结构 | 24 镜：12 视频 + 12 图片；9 个转场；12 条素材内重点提示；20 条底部字幕；6 个音效；BGM 增益 0.20 |
| 技术 QC | `qc_video.py` PASS；无黑帧；音量 mean -16.6dB / max -1.7dB |
| 字幕 QC | `qc_captions.py` FAIL：20 段低文字帧（19 个句界 + 末帧）；已知缺陷，新片须改为瞬时换字 |
| 复现 | `python3 scripts/qc_captions.py <v2.mp4> --json-out caption_qc.json --contact-sheet caption_qc.jpg` |
| 源工程 | `/home/user/Doubao/chats/38456561376081154/ep05/remotion` |
| 主要文件 | `src/Ep05.tsx`、`src/Root.tsx` |
| 预览 | `previewCdn`：`https://aka.doubaocdn.com/s/pqeq6n5JgQ`（v2 封面，1080×1440） |
| 已知差异 | 样例 BGM 用 Mixkit《Close Up》临时铺底；正式版按“抖音热门曲、不用 AI”替换。 |

## TP02 v1（保留版）

- 35 镜 / 33.6s；图片与实拍之间基本都做 7 帧交叉淡入，视频→视频硬切。
- 字幕 QC 同样 FAIL：20 段低文字帧，句界空白与 v2 相同；只作镜头/转场对照，不复刻字幕实现。
- 保留在 `ep05/remotion/src/Ep05_v1.tsx` 与 `out/` 旧版；不覆盖、不作为新片模板。

## 使用规则

- 新片先复制对应源工程结构，再替换 `data`/`shots`，不要直接改样片工程。
- 样片只作版式与节奏参考；已知问题不要复刻。
- 每次新片仍按 `references/self-check.md` 重新自检，不能引用样片的 QC 结果。
