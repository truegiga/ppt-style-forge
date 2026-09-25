# ppt-style-forge

A WorkBuddy skill that removes the "AI flavor" from your presentations: it forges a personal PPT style library from **real designer templates**, through a human-in-the-loop scoring process that compresses your effort into **two messages per round**.

中文说明见下方 [中文说明](#中文说明)。

## Why

AI-generated PPTs share one recognizable fingerprint: the same blue+gold palette, single font family, uniform card grids, footer page numbers, chips and circled numbers. Audiences subconsciously read "AI-made = cheap" before reading a single word.

**AI flavor is not a style — it is one fixed template shared by everyone.** The cure is not "a better style" but **diversity**: build a pool of styles that differ from each other and from that template, then rotate.

## How it works

```
S0 Check existing assets → S1 Intake quiz (once, closed questions) → S2 Auto forging
  → S3 Batch scoring (human) → S4 Reasons → rules ─not converged─→ back to S3
                                            └converged→ S5 Final confirm (human) → S6 Auto save
```

- **Human touch is compressed to two spots**: scoring samples (one message per round) and confirming the final lineup (one message).
- Round 1 ships **6** sample decks; rounds 2–3 ship **3** each. Converge when a candidate scores ≥4 with no new vetoes; hard cap **3 rounds** (the skill asks before extending).
- Every scoring reason is converted into a hard rule, so the same mistake never appears twice.
- Machine-side vetoes run before anything reaches you: the "blue+gold recolor test", layout-rhythm metrics (skeleton variety, adjacent-page repetition, density CV, visual-gravity drift), grayscale/circle-crop downgrades, and your exclusion list.

## Install

WorkBuddy: import the skill folder (or zip) via the skills manager.

Manual: copy this folder to `~/.workbuddy/skills/ppt-style-forge/` (user scope) or `<workspace>/.workbuddy/skills/ppt-style-forge/` (project scope).

## Requirements

- Python **3.11+** (stdlib only; [Pillow](https://pypi.org/project/Pillow/) optional, needed only for palette extraction)
- A WorkBuddy-compatible agent runtime, or use the scripts standalone

## Usage triggers

Say things like: 「我的 PPT 一眼就像 AI 做的」/「去 AI 味」/「建一个我自己的 PPT 风格库」/「给样张打分」.

## Repository layout

```
SKILL.md                      # main skill instructions (S0–S6 workflow)
references/filling-recipe.md  # python-pptx filling recipe on real-template bases
scripts/ppt_harvest.py        # template harvesting & layout-audit CLI (links/fetch/parse/palette/layout)
```

## License

MIT — see LICENSE.

---

## 中文说明

**这是什么**：一个 WorkBuddy skill，用「真人设计模板底座 + 打分迭代闭环」锻造一套属于你自己的「去 AI 味」PPT 风格库。

**为什么**：AI 生成的 PPT 全都长一个样——同款蓝金配色、单字族、均匀卡片栅格、页脚页码。受众潜意识里「AI 生成 = 廉价」，内容还没读就先折价。AI 味不是一种风格，而是所有人共用的同一套模板；解药是**多样性**，不是找一种「更好的风格」。

**怎么用**：触发词见上。人工只出现在两处——给样张打分（一轮一条消息）、定版确认（一条消息），其余全自动。打分理由会自动转成硬规则，下一轮同类问题不再出现。

**样张工艺**：真人模板底座 + python-pptx 填充（保留设计师原版式细节，只替换内容），附文本溢出、浅字叠浅图、英文残留三项工程检查。

---

Author: Sean Cai
