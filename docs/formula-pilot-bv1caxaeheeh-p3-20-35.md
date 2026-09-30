# 高数第 3 集 20:00–35:00 公式试验记录

- 来源：[宋浩《高等数学》2.0 第 3 集](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3)，视频 ID `BV1CAxaeHEeH_p3`。
- 范围：原视频 20:00–35:00，共 900 秒。视频元数据时长约 65 分 40 秒；截出的 1080p 片段为 900 秒，约 54.7 MiB。
- 方法：本地每秒抽 1 张 960×540 缩略图，共 900 张；每 5 秒取 1 张组成总览图，共查看 180 个时间点，再查看代表性 1080p 画面并对照已有 ASR。画面保存在本机忽略的 `output/BV1CAxaeHEeH_p3/formula_pilot_20_35/`。
- 边界：本试验由助手目视核对，**没有调用项目命令或外部视觉模型 API**；尚未逐帧人工标注 900 张画面，不能据此计算自动识别召回率，也不能宣称零漏检。

## 发现的公式与关键例子

下表按讲解内容合并重复板书，是本次人工检查发现的 **9 组候选**，不是“视频中恰好只有 9 条公式”。“原书”指本地已有的 `output/BV1CAxaeHEeH_p3/book.md`。

| 时间 | 画面和字幕支持的内容 | 本地证据 | 原书 | 判定 |
| --- | --- | --- | --- | --- |
| 20:25 | `f(x)=\frac1x`，随后在 `(0,1)` 与 `(1,2)` 分别讨论有界性 | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_20_25.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1225) | 未收录例子 | 可转写；区间结论需与后续讲解一起呈现 |
| 23:15 | `|f(x)|\le M \iff -M\le f(x)\le M` | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_23_15.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1395) | 已收录 | 可转写 |
| 25:10 | 从上界 `f(x)\le M_1`、下界 `f(x)\ge M_2` 推回有界 | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_25_10.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1510) | 未收录这段推理 | **待核对**：板书没有明确写出如何选取统一的 `M`，不能替讲者补写公式 |
| 27:45 | `I\subset D`、`x_1<x_2`；递增时 `f(x_1)<f(x_2)`，递减时 `f(x_1)>f(x_2)` | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_27_45.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1665) | 已收录 | 可转写 |
| 28:30 | `y=x^2` 在 `(-\infty,0]` 递减、在 `[0,+\infty)` 递增；讲者随后解释零点可属于两段 | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_28_30.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1710) | 未收录例子 | 可转写；端点括号要以画面和后续讲解校准 |
| 30:55 | `y=x^3` 在 `(-\infty,+\infty)` 递增 | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_30_55.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1855) | 未收录例子 | 可转写 |
| 31:45 | `y=\ln x`、`x>0`，用定义域不关于原点对称说明不能判为奇或偶 | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_31_45.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1905) | 未收录例子 | 可转写；结论来自附近口述 |
| 32:30 | 定义域关于原点对称时，`f(-x)=f(x)` 为偶，`f(-x)=-f(x)` 为奇 | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_32_30.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1950) | 已收录 | 可转写 |
| 34:40 | `f(x)=x^2` 但 `D=[-1,2)`；定义域不对称，讲者说该受限函数非奇非偶 | [画面](../output/BV1CAxaeHEeH_p3/formula_pilot_20_35/evidence/frame_34_40.png) · [视频](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=2080) | 未收录例子 | 画面支持函数与定义域；结论由 34:40–34:42 的口述支持 |

20:00 开头仍留着前一段“无界”的板书，不能当作这一段新写的公式。34:50 后开始周期性话题，但完整公式位于所选片段之外。

## 这次试验说明了什么

原书在这一范围只引用了 23:40、27:45、32:30 三张画面；本次查到的 9 组候选中，6 组具体例子或推理没有进入原书。尤其 `(-\infty,0]`、`[0,+\infty)` 与 `D=[-1,2)` 的括号信息在 ASR 中不完整，需要画面校准。ASR 还把“奇偶性”等词识成近音词，因此不能用字幕单独决定公式。

**下一步验收**：一键识别命令在这 15 分钟至少提出上表 9 组候选，保留 25:10 的待核对状态；再人工抽查没有命中的时间段。当前结果只证明视频源获取、分 P 时间对齐和视觉校准路径可行，尚未验证自动候选发现与外部模型的转写准确率。
