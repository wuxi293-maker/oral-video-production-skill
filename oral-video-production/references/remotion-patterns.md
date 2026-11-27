# Remotion 组件骨架

> 只给结构与实现要点，不复制整段业务代码。所有路径都相对 `public/`，用 `staticFile()` 包一层。

## 1. 数据类型

```ts
export type Shot = {
  id: string;
  kind: "image" | "video";
  src: string;
  start: number;          // 全局帧
  end: number;            // 全局帧，不含
  tone?: "mono" | "paper" | "color";
  objectPosition?: string;
  zoom?: [number, number];
  pan?: [number, number, number, number];
  startFrom?: number;     // 视频从源素材第几帧开始
};

export type TransitionKind =
  | "fade" | "slideLeft" | "slideUp"
  | "wipeLeft" | "wipeUp" | "push" | "blur";

export type Transition = { kind: TransitionKind; frames: number };

export type Callout = {
  start: number;
  end: number;
  kicker: string;
  main: string;
  trail?: string;
  style?: "tag" | "date" | "statement";
  enter?: "mask" | "pop" | "slide" | "blur";
};

export type Caption = { start: number; end: number; text: string };

export type OralVideoProps = {
  titleLines: [string, string];
  shots: Shot[];
  transitions: Record<number, Transition>; // key = 切点帧
  callouts: Callout[];
  captions: Caption[];
  bgm?: string;
  sfx?: { frame: number; src: string; volume: number }[];
};
```

## 2. Root：时长取最后镜头

```tsx
import { Composition } from "remotion";
import { OralVideo } from "./OralVideo";
import data from "./data";
import type { OralVideoProps } from "./types";

const props = data as OralVideoProps;
const lastFrame = Math.max(...props.shots.map((s) => s.end));

export const Root = () => (
  <Composition
    id="OralVideo"
    component={OralVideo}
    durationInFrames={lastFrame}
    fps={30}
    width={1080}
    height={1920}
    defaultProps={props}
  />
);
```

不要写 `shots.length * 90`。

## 3. 镜头层：动态时长 + 转场延长

```tsx
import { AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile } from "remotion";

const ShotLayer = ({ shot }: { shot: Shot }) => (
  <AbsoluteFill style={{ backgroundColor: "#0A0A0A" }}>
    {shot.kind === "video" ? (
      <OffthreadVideo
        src={staticFile(shot.src)}
        startFrom={shot.startFrom ?? 0}
        muted
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: shot.objectPosition ?? "center",
        }}
      />
    ) : (
      <Img
        src={staticFile(shot.src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          objectPosition: shot.objectPosition ?? "center",
        }}
      />
    )}
  </AbsoluteFill>
);
```

渲染时给前一镜延长转场帧，当前镜从切点进入：

```tsx
{shots.map((shot, i) => {
  const next = transitions[shot.end];
  const extra = next?.frames ?? 0;
  return (
    <Sequence
      key={shot.id}
      from={shot.start}
      durationInFrames={shot.end - shot.start + extra}
    >
      <ShotLayer shot={shot} />
    </Sequence>
  );
})}
```

当前镜的入场动画用 `useCurrentFrame()` 的局部帧：

```tsx
const frame = useCurrentFrame();
const t = transitions[shot.start]; // 本镜起点若是切点
const p = t ? Math.min(1, frame / t.frames) : 1;
```

## 4. 转场函数

```tsx
import { interpolate, Easing } from "remotion";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.4, 0, 0.2, 1);

export const enterStyle = (kind: TransitionKind, p: number) => {
  switch (kind) {
    case "fade":
      return { opacity: interpolate(p, [0, 1], [0, 1], clamp) };
    case "slideLeft":
      return {
        opacity: 1,
        transform: `translateX(${interpolate(p, [0, 1], [100, 0], clamp)}%)`,
      };
    case "slideUp":
      return {
        opacity: 1,
        transform: `translateY(${interpolate(p, [0, 1], [100, 0], clamp)}%)`,
      };
    case "wipeLeft":
      return {
        clipPath: `inset(0 ${interpolate(p, [0, 1], [100, 0], clamp)}% 0 0)`,
      };
    case "wipeUp":
      return {
        clipPath: `inset(${interpolate(p, [0, 1], [100, 0], clamp)}% 0 0 0)`,
      };
    case "push":
      return {
        transform: `translateX(${interpolate(p, [0, 1], [100, 0], clamp)}%) scale(${interpolate(p, [0, 1], [1.08, 1], clamp)})`,
      };
    case "blur":
      return {
        opacity: interpolate(p, [0, 0.4, 1], [0, 1, 1], clamp),
        filter: `blur(${interpolate(p, [0, 1], [14, 0], clamp)}px)`,
      };
  }
};
```

- `p` 用 `interpolate(frame, [0, t.frames], [0, 1], {...clamp, easing: ease})`。
- `wipe` 的 `clipPath` 要作用在包住当前镜头的 `AbsoluteFill` 上。
- `slide` 不叠透明度，避免双曝光。
- `push` / `blur` 的缩放不要超过 1.08，防止边缘露黑。

## 5. 标题与卡片

TP02：

```tsx
<AbsoluteFill style={{ backgroundColor: "#C51E24" }}>
  <div style={{ position: "absolute", left: 48, top: 56, width: 984, height: 1808, border: "1.5px solid rgba(255,245,228,.58)" }} />
  <div style={{ position: "absolute", left: 94, top: 112, width: 892, height: 1696, border: "1px solid rgba(255,245,228,.32)" }} />
  <div style={{ position: "absolute", left: 105, top: 262, width: 870, height: 1296, background: "#EDE6DA", borderRadius: 54 }} />
  <div style={{ position: "absolute", left: 120, top: 292, width: 840, height: 840, background: "#050403", borderRadius: "38px 38px 0 0", overflow: "hidden" }}>
    {/* 媒体层 */}
  </div>
  <CaptionBar text={caption} />
  <Title lines={titleLines} />
</AbsoluteFill>
```

TP01：

```tsx
<AbsoluteFill style={{ backgroundColor: "#080B0F" }}>
  <TopScrim />
  <Header />
  <TitleBlock />
  <InfoCard card={card} />
</AbsoluteFill>
```

具体坐标见 `tp01-blueprint-news.md` / `tp02-red-cream-oral.md`。

## 6. 底部字幕：常驻底板

```tsx
const CaptionBar = ({ text }: { text: string }) => (
  <div
    style={{
      position: "absolute",
      left: 120,
      top: 1132,
      width: 840,
      height: 94,
      borderRadius: "0 0 34px 34px",
      background: "linear-gradient(180deg, #E03A3A, #C51E24)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      boxShadow: "0 6px 18px rgba(0,0,0,.18)",
    }}
  >
    <div
      style={{
        width: 780,
        color: "#fff",
        fontFamily: "Noto Sans CJK SC, sans-serif",
        fontSize: 35,
        fontWeight: 700,
        lineHeight: 1.15,
        textAlign: "center",
        whiteSpace: "nowrap",
        overflow: "hidden",
      }}
    >
      {text}
    </div>
  </div>
);
```

主组件里只算当前字幕，**不要条件挂载整条字幕**：

```tsx
const caption = captions.find((c) => frame >= c.start && frame < c.end)?.text ?? "";
```

底部整句字幕**不要做透明度淡出/淡入**：`CaptionBar` 常驻，文字直接换。TP02 样例 v1/v2 的 `Subtitle` 做了 4 帧淡入/3 帧淡出，导致每个句界有 1 帧空白；这是已知缺陷，不要复刻。需要入场动画时，只给素材内重点提示，不给底部整句字幕。

## 7. 素材内重点提示

```tsx
const CalloutLayer = ({ c, frame }: { c: Callout; frame: number }) => {
  if (frame < c.start || frame >= c.end) return null;
  const local = frame - c.start;
  const p = interpolate(local, [0, 10], [0, 1], {
    ...clamp,
    easing: Easing.out(Easing.cubic),
  });

  const enter =
    c.enter === "mask"
      ? { clipPath: `inset(0 ${100 - p * 100}% 0 0)` }
      : c.enter === "pop"
      ? { transform: `scale(${0.92 + p * 0.08})`, opacity: p }
      : c.enter === "slide"
      ? { transform: `translateY(${12 - p * 12}px)`, opacity: p }
      : { filter: `blur(${10 - p * 10}px)`, opacity: p };

  return (
    <div style={{ position: "absolute", left: 38, bottom: 40, ...enter }}>
      <div style={{ fontSize: 20, letterSpacing: 2, color: "#FFE9A8" }}>{c.kicker}</div>
      <div style={{ fontSize: 48, fontWeight: 900, color: "#fff" }}>{c.main}</div>
      {c.trail ? <div style={{ fontSize: 22, color: "rgba(255,255,255,.82)" }}>{c.trail}</div> : null}
    </div>
  );
};
```

- 放在媒体窗容器内（`left 120, top 292, w 840, h 840`），不是全屏绝对坐标。
- 一次只渲染一条：`callouts.filter(c => frame >= c.start && frame < c.end).slice(-1)`。
- 位置按镜头主体避让；不要固定死在一个坐标。
- `statement` 样式可放大到 54–64px，加半透明底板。

## 8. 音频与音效

```tsx
<Audio src={staticFile("audio/voice.wav")} />
<Audio src={staticFile(bgm)} volume={0.2} />
{sfx.map((s, i) => (
  <Sequence key={i} from={s.frame} durationInFrames={30}>
    <Audio src={staticFile(s.src)} volume={s.volume} />
  </Sequence>
))}
```

- BGM 用抖音热门曲，不用 AI 生成。
- 音效只挂段落节点，不逐镜加。
- 人声轨道不要加 `volume` 压缩；需要时在音频处理阶段做。

## 9. 渲染命令

```bash
npx remotion render src/index.ts OralVideo out/master.mp4 \
  --codec=h264 --pixel-format=yuv420p \
  --video-bitrate=12M --audio-codec=aac --audio-bitrate=192k \
  --concurrency=4
```

渲染后先跑 `scripts/qc_video.py`，再做 `references/self-check.md` 的人工检查。
