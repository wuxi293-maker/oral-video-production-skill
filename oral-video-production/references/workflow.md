# 完整制作流程

## 0. 任务输入

开工前确认：

- 脚本链接与章节/标题；只读指定段落。
- 模板编号：TP01 / TP02。
- 配音文件：采样率、声道、时长。
- 特殊要求：标题行数、素材方向、封面、平台、是否需要口播。
- 可用素材：用户链接、官方图、实拍片段、需要检索的关键词。

缺关键材料时先列缺口；不猜数字、日期、人名、事实表述。

## 1. 读脚本、拆句

1. 取脚本标题、正文、发布文案、参考素材。
2. 按语义拆成“句/意群”，每句标注：
   - 句号、预计时长；
   - 关键词/数字/地名/人名；
   - 适合的画面类型（实拍/产品/图表/档案图）；
   - 是否需要素材内重点提示。
3. 删除“资讯版/镜号 1”等无效段。
4. 片内标题只用一个，全片固定；跨片按新脚本替换。

## 2. 音频处理

### 2.1 找气口

```bash
ffmpeg -hide_banner -i input.wav \
  -af "silencedetect=noise=-35dB:d=0.18" -f null - 2>&1 | grep silence
```

记录每段 `silence_start / silence_end`，把停顿压到 0.10–0.16 秒。不要把所有呼吸都切掉，保留自然语气。

### 2.2 压气口 + 提速 + 滤波

按实际气口列表拼接 `atrim` / `concat`，再统一处理：

```bash
ffmpeg -y -i compressed.wav \
  -af "atempo=1.2,highpass=f=52,lowpass=f=14500,alimiter=limit=0.95" \
  -ar 48000 -ac 1 -c:a pcm_s16le voice_cut.wav
```

- `atempo` 保持音高；超过 2.0 时拆成多级。
- 口播清晰优先；不要用降噪把齿音/气声磨平。
- 处理后时长就是全片时间轴。

### 2.3 词级时间戳

用 faster-whisper（small/int8 可先用）或同等工具，输出每个词/字的 `start/end`。ASR 对专有名词、缩写、数字容易误识，字幕按脚本原文校正，时间戳保留。

需要检查的字段：

```json
{"word": "磷酸铁锂", "start": 10.36, "end": 11.76}
```

## 3. 镜头表

每个镜头一行，至少包含：

| 字段 | 说明 |
|---|---|
| shot_id | 唯一 id |
| start / end | 帧号，30fps |
| duration | 秒，按语音/语义 |
| kind | image / video |
| src | 素材路径 |
| content | 画面内容 |
| line | 对应台词 |
| transition | 类型 + 帧数，可空 |
| callout | 重点提示文本/样式/入场 |
| caption | 底部整句字幕 |
| source | 素材来源/授权 |

原则：

- 口播不固定单镜时长；一句可以对应一镜，也可以跨两镜、三镜。
- 资讯按信息点切；不套 3 秒公式。
- 相邻镜头景别、色调、构图要拉开；同一素材不重复。
- 先排“台词—画面”对应，再调时长；不要为了卡点把画面提前/延后太多。

## 4. 素材准备

### 4.1 实拍转 30fps CFR

```bash
ffmpeg -y -i input.mp4 \
  -vf "setpts=PTS/1.0,fps=30" \
  -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p -an output_30fps.mp4
```

- 不做运动插帧；用 `setpts` 对齐源帧，避免周期性快慢帧。
- 25fps 素材可直接 `fps=30`；23.976 素材按实际比例调整 `setpts`。
- 检查快速运动处无鬼影/撕裂；有则换素材。

### 4.2 图片

- 统一长边 ≥ 1600px；模糊图不硬放大。
- 主体完整，不裁头、不裁产品关键部位。
- 需要 Ken Burns 时，缩放范围约 1.03–1.11，不要超过 1.15。

### 4.3 素材来源

每张图/每条视频记录：

```json
{"purpose": "fact", "sourceUrl": "...", "license": "official/news/free"}
```

优先官方、主流媒体、可商用素材；不用带明显水印/角标的截图。

## 5. Remotion 工程

目录：

```text
project/
├── public/
│   ├── audio/voice.wav
│   ├── music/bgm.wav
│   ├── sfx/
│   ├── img/
│   └── video/
├── src/
│   ├── index.ts
│   ├── Root.tsx
│   ├── OralVideo.tsx
│   ├── data.ts
│   └── types.ts
├── out/
└── remotion.config.ts
```

- `Root.tsx` 的 `durationInFrames` 取最后一个镜头 `end`。
- `OralVideo.tsx` 负责版式与图层；`data.ts` 负责镜头/转场/字幕/重点提示。
- 组件骨架见 `references/remotion-patterns.md`。
- 视频用 `OffthreadVideo`；图片用 `Img`。
- 字幕条常驻，只换文字；重点提示单独组件。

## 6. 声音

- 人声：`<Audio src={staticFile("audio/voice.wav")} />`
- BGM：`volume={0.20}`；用抖音热门曲，不用 AI 生成。
- 音效：`Sequence from={节点帧}` + `<Audio volume={...} />`；只挂段落节点，不逐镜添加，密度按片长和段落数决定。
- 混音后检查：人声清晰、BGM 不压字、无爆音/削波。

## 7. 渲染

```bash
npx remotion render src/index.ts OralVideo out/master.mp4 \
  --codec=h264 --pixel-format=yuv420p \
  --video-bitrate=12M --audio-codec=aac --audio-bitrate=192k \
  --concurrency=4
```

- 需要固定帧率时加 `--x264-params "nal-hrd=cbr:force-cfr=1"` 或渲染后 ffmpeg 复核。
- 封面：`npx remotion still src/index.ts OralVideo out/cover.png --frame=0`，再裁 3:4。
- 渲染后进入自检，不直接发链接。

## 8. 自检与交付

1. 运行 `scripts/qc_video.py` 做技术检查。
2. 运行 `scripts/qc_captions.py` 查字幕条空白帧，回看联系表。
3. 按 `references/self-check.md` 做四项人工检查。
4. 不通过 → 修 → 重渲染 → 再检。
5. 通过 → 上传 CDN → 发 mp4 链接 → 用户确认 → 落本地。
6. 本地目录 `日期_脚本名/`；版本 `v1–vN`；封面 3:4。

## 9. 常见返工点

| 现象 | 原因 | 处理 |
|---|---|---|
| 字幕切换闪空 | 逐句挂载/卸载 | 底板常驻，只换文字 |
| 素材与台词错位 | 先排画面后配音 | 先定人声时间轴，再排镜头 |
| 画面发软 | 每个切点都加转场 | 硬切为主，章节点才转 |
| 人物/产品被裁 | 满幅 cover 未检查主体 | 调整 `objectPosition` 或换构图 |
| 字幕被抖音 UI 遮 | 贴底/贴右 | 按安全区上移、右移 |
| 画面抽动 | 运动插帧/可变帧率 | 30fps CFR + `setpts`，不插帧 |
