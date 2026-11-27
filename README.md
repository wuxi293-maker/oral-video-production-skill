# 口播视频制作 Skill

`oral-video-production`：从飞书脚本/配音到竖屏成片的可复用 Skill。包含 TP01 蓝图资讯版、TP02 红米口播版、Remotion 工程骨架、字幕/转场实现、交付前自检脚本与抖音安全区参考。

> 版本：Skill v1.1 · 2026-11-27  
> 模板：TP01 v1.1、TP02 v1.1  
> 仓库：https://github.com/wuxi293-maker/oral-video-production-skill

## 这套 Skill 解决什么

- 口播不固定单镜 3 秒，按脚本语义和语音节奏切。
- 硬切为主，转场只放在章节/时空跳点，不逐切点堆；可用多种样式。
- 素材内重点提示按词级时间轴出现，入场用遮罩/弹入/上滑/模糊。
- 底部整句字幕底板常驻、文字瞬时换字，避免句界闪空；一句可跨镜头。
- BGM 用抖音热门曲、不用 AI 生成，增益约 0.20。
- 制作完成后必须自检：素材—音频对应、素材异常、字幕闪动、抖音字幕和操作安全区。

## 目录

```text
oral-video-production/
├── SKILL.md
├── agents/
│   ├── doubao.yaml
│   └── openai.yaml
├── references/
│   ├── workflow.md
│   ├── tp01-blueprint-news.md
│   ├── tp02-red-cream-oral.md
│   ├── remotion-patterns.md
│   ├── self-check.md
│   ├── samples.md
│   └── audit-2026-11-27.md
├── scripts/
│   ├── qc_video.py
│   └── qc_captions.py
└── assets/
    ├── template-registry.json
    ├── douyin-safe-area-1080x1920.svg
    └── previews/
        └── README.md
```

## 安装

推荐直接把根目录的 `安装提示词.md` 整段发给要安装的 AI 助手。

手动安装：

```bash
git clone https://github.com/wuxi293-maker/oral-video-production-skill.git
cp -a oral-video-production-skill/oral-video-production \
  <workspace>/.user_skills/oral-video-production
```

安装后重新加载技能列表，调用名为 `$oral-video-production`，显示名“口播视频制作”。

## 依赖

- Node 18+、npm/npx、Remotion
- FFmpeg / ffprobe
- Python 3.9+
- 中文字体：Noto Sans CJK SC Black 900（或同字重替代）

## 样片

- TP01 v3 完整样片：https://aka.doubaocdn.com/s/xwStY1ws79
  - 34.0s / 1080×1920 / 30fps / 11.2Mbps，QC PASS
- TP02 v2 完整样片：https://aka.doubaocdn.com/s/YYp26D6jRG
  - 33.6s / 1080×1920 / 30fps，技术 QC PASS；字幕有已知句界空白，只作版式参考
- TP02 v1 保留版：https://aka.doubaocdn.com/s/cF4UbGHR17

预览图不入仓，见 `assets/previews/README.md` 的 CDN 链接。

## 已知边界

- TP02 v1/v2 的 `Subtitle` 每个句界有 1 帧空白，属于旧实现缺陷；新片必须用“底板常驻、文字瞬时换字”。
- TP01 v3 样片仍是每镜 7 帧淡入/淡出，属于旧逻辑；新片按“硬切为主、章节点转场”执行。
- 仓库不保存样片和 JPG 二进制，样片/预览用 CDN；Skill 运行不依赖它们。
