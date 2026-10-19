<!-- Hero: assets/src/ascii_hero.py (portrait via avatar_ascii.py). Calendar, streaks, snake: assets/src/contributions.py. Plates, button, footer: assets/src/build.py -->

<img src="assets/hero.gif" width="100%" alt="DimaLab. — Software developer. Building tools, engines and experiments. Editorial banner with animated ASCII art drawn entirely in text characters: a liquid structure flows and splits, gathers into one mass and crystallises into an ASCII self-portrait with cyan eyes, holds while a scan line passes, then dissolves back into liquid.">

<a href="https://dima-s-cinematic-journey-new.vercel.app"><img src="assets/portfolio.svg" width="300" alt="Visit portfolio"></a>

Software close to the system — taskbars, render pipelines, mod loaders — built with attention to how it feels to use.

<br>

## 01 — Selected work

| Project | What it does |
| :-- | :-- |
| **StoryModEngine**<br><sub>Kotlin · Java · Forge 1.20.1 · GLSL</sub><br><sub>IN DEVELOPMENT · PRIVATE</sub> | Mod-development engine for Forge 1.20.1: declare content with one annotation, then build quests, dialogue, NPCs and cutscenes with a `.sme` scripting language and in-game editors. The source is private for now; see below. |
| **[FluentFlow](https://github.com/LomakoDima/FluentFlow)**<br><sub>C# · WPF · .NET 10</sub><br><sub>[RELEASED](https://github.com/LomakoDima/FluentFlow/releases)</sub> | Media controller that lives on the Windows 11 taskbar: a live spectrum visualizer from WASAPI loopback, a native-style volume flyout and a settings window with a live preview. The docking geometry is unit-tested. |
| **[BinLet](https://github.com/LomakoDima/BinLet)**<br><sub>C# · WPF · .NET 10</sub><br><sub>[RELEASED](https://github.com/LomakoDima/BinLet/releases)</sub> | Tiny Windows 11 tray utility that puts the native Recycle Bin in the notification area: empty and full icon states, live updates through shell change notifications, and an empty action that always asks first. Ships as one self-contained exe. |
| **[PushLog](https://github.com/LomakoDima/pushlog-bot)**<br><sub>Python · GitHub Actions · Claude API</sub><br><sub>IN USE</sub> | GitHub Action that turns every push into a Telegram devlog post. Claude summarises the commits and a bounded diff, with commit subjects as the fallback. One central action serves all my repositories. |
| **[OculusSMECompat](https://github.com/LomakoDima/OculusSMECompact)**<br><sub>Java · Forge 1.20.1 · Mixin</sub><br><sub>EXPERIMENTAL</sub> | Mixin addon that keeps StoryModEngine's GPU instancing alive under Oculus/Iris shader packs instead of falling back to immediate-mode rendering. |
| **[Lens](https://github.com/LomakoDima/LensMod)**<br><sub>Java · Forge 1.20.1</sub><br><sub>[RELEASED](https://github.com/LomakoDima/LensMod/releases)</sub> | Client-side zoom for Minecraft with smooth animation, scroll-to-zoom and automatic mouse-sensitivity scaling. |
| **[Linqo](https://github.com/LomakoDima/Linqo)**<br><sub>TypeScript · React · TanStack Start · PostgreSQL</sub><br><sub>IN DEVELOPMENT</sub> | No-code builder for personal pages: start from a template, shape it with themes, blocks, music and effects, then publish it under your own username as one shareable link. |

<sub>ALSO&nbsp; — &nbsp;[study-buddy-pro](https://github.com/LomakoDima/study-buddy-pro): a Telegram Mini App that turns PDF, DOCX and PPTX lectures into summaries (React, FastAPI) &nbsp;·&nbsp; [History of Kazakhstan trainer](https://history-of-kazakhstan-trainer-new1.vercel.app): an oral-exam trainer with Claude-assisted essay review</sub>

<br>

## 02 — Currently building

<img src="assets/storymodengine.svg" width="100%" alt="StoryModEngine diagram: in-game editors (VFX, cutscene sequencer, .sme script IDE, replay, recipe, video assets) feed runtime systems (quests, dialogue, NPCs, triggers, shops, cinematics) through the Flow engine, which assemble into one story-driven Minecraft experience.">

**StoryModEngine** is a mod-development engine on Forge 1.20.1. Content is declared, not wired: one `@AutoContent` annotation and the engine infers ids, registries and generated resources. On top of that sit quests, dialogue, NPCs, cutscenes and a `.sme` scripting language, each with its own in-game tooling. The source is private for now.

```text
2026-10-08  script IDE, player model
2026-10-05  replay system + editor
2026-10-01  MP4 video via FFmpeg
2026-09-30  timeline + recipe editor
```

<br>

## 03 — Toolkit

| Area | Tools |
| :-- | :-- |
| **Languages** | Java · Kotlin · C# · Python · TypeScript · GLSL |
| **Desktop & systems** | .NET · WPF · Win32 interop · WASAPI · UI Automation |
| **Game dev & modding** | Minecraft Forge · Mixin · Gradle · glTF / GLB · shaders · Unity · Unreal Engine |
| **Web** | React · Vite · Tailwind CSS · FastAPI · Node.js |
| **Tools & infra** | Git · GitHub Actions · Vercel · SQLite / PostgreSQL · Claude API · Telegram Bot API |

<br>

## 04 — Activity

<picture>
  <source media="(max-width: 600px)" srcset="https://github.com/LomakoDima/LomakoDima/raw/main/assets/activity-mobile.svg">
  <img src="assets/activity.svg" width="100%" alt="GitHub contribution calendar for the last year with current streak, longest streak and busiest day above it. A cyan snake travels the grid and eats the twelve busiest days. Generated daily from the GitHub GraphQL API.">
</picture>

<sub>Real daily counts from GitHub's GraphQL API, re-rendered every day by a workflow in this repository. The snake eats the twelve busiest days, then the grid resets. GitHub's own calendar, just below, remains the record.</sub>

<br>

## 05 — Links

[Portfolio](https://dima-s-cinematic-journey-new.vercel.app) &nbsp;·&nbsp; [GitHub](https://github.com/LomakoDima) &nbsp;·&nbsp; [All repositories](https://github.com/LomakoDima?tab=repositories)

<br>

<img src="assets/footer.svg" width="100%" alt="DimaLab. — tools, engines, experiments. End of file.">
