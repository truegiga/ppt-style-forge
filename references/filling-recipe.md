# 样张填充工艺（真人模板底座 + python-pptx）

这是 S2 产出样张的核心工艺：**打开真人设计的模板原件，删掉多余页，把用户内容替换进占位符**。骨架与版式细节全部保留设计师原作，这是「去 AI 味」效果最好的路线——只换配色往往无效（骨架没换，只是把同一个模板染成另一个颜色）。

## 底座筛选

1. 跑 `layout` 六项体检（达标线见 SKILL.md）。
2. 结构干净度：渐变蒙版少、无页脚 N/M、无圆角卡片栅格堆砌。
3. 版式多样性：页数 ≥15，章节页/数据页/图文页齐全。
4. `slidescarnival` 原件通常无 docProps/Application 元数据，填充保存后天然干净——优先选这类。

## 填充四步（python-pptx）

### 1. 删页

```python
from pptx.oxml.ns import qn
el = sldIdLst 里目标页的 <p:sldId>
rId = el.get(qn('r:id'))
prs.part.drop_rel(rId)          # 必须做，否则残留 rels
sldIdLst.remove(el)             # 两步缺一不可，只 remove 会留下悬空引用
```

### 2. 整包换色（可选，仅当骨架已过换色测试）

zip 级重写：把 `srgbClr val` / `lastClr` 的十六进制映射替换，**slides + layouts + masters + theme 全部 XML 都要处理**；替换后必须 grep 验证残留为 0。

### 3. 填文本

- 逐 shape → paragraph → run；写 run[0]、清空其余 run，保住原格式。
- 规则表 `(页, 占位前缀, 新文本)` 用**队列式消费**：同名占位符（如 Name×4）逐个顶上，不能用 used-set 去重（会只消费一次，其余留白）。
- 中文 run 必须设东亚字体——python-pptx 无 ea API：

```python
from pptx.oxml.ns import qn
rPr.append(rPr.makeelement(qn('a:ea'), {'typeface': 'Microsoft YaHei'}))
```

- 克隆扩页：底座页数不够时 deepcopy spTree + rels 重映射；`get_or_add` 同 target 返回既有 rId，图片自动复用；克隆后逐页核图片数。重排页序时，**规则队列的顺序必须与页序同步改**（改了 ORDER 忘改 RULES 会张冠李戴）。

### 4. 元数据

author / last_modified_by 写用户真名或品牌名；不含生成工具痕迹。

## 工程检查（三项全过才交付）

1. **文本溢出**：填充文本比原占位符长时可能超出文本框折行。判据：**填充文本不得比原占位符更长**（变短 = 安全，原位即原设计）。中文比英文占宽大，同字数也可能溢。超了就缩字号/精简文案/调框宽。
2. **浅色字叠浅色图**：底座自带的白字版式，填充后文字延伸到图片浅色区域就隐身。白字只允许出现在确定有深色蒙版或深色底的区域。
3. **英文残留全扫**：填完后全文扫 `[A-Za-z]{3,}`，凡漏改的英文占位段落一律补规则重跑（同一前缀多处占位时规则表容易写漏）。

## 验收

- 跑 `layout` 六项对比底座原版（底座原版节奏是设计师给的，指标略偏时可校准达标线，如实记录）。
- 与参照物对比（如有旧版）：字体重复率、字号分布余弦、骨架近似度、密度节奏——量化确认「细节换了」而非「细节没了」。
