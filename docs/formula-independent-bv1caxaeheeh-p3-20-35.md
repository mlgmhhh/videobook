# 高数第 3 集 20:00–35:00 独立公式识别实验

- 来源：[原视频第 3 集](https://www.bilibili.com/video/BV1CAxaeHEeH?p=3&t=1200)。输入是该 900 秒视频片段及项目已有的 ASR 字幕；视觉模型未读取先前的人工试验记录。
- 扫描：对 900 张逐秒画面每 5 秒取一张，组成 30 张六宫格；模型提出 86 个候选时间，再逐张查看对应的 1080p 画面和前后 15 秒字幕。原始识别和筛选结果均保留在 `output/BV1CAxaeHEeH_p3/formula_auto_20_35/`。
- 复核：独立运行后，参照[此前人工试验](formula-pilot-bv1caxaeheeh-p3-20-35.md)对比。此前发现的 9 组内容在候选中都有对应画面；这只说明已知组被提出，不能据此计算全片召回率。
- 已知错误：模型首读把 34:45 画面的 `D=[-1,2)` 写成 `D=[-1,2]`。原画面与再次独立识别均支持右端圆括号。20:05 是片段开始前留下的板书，不应当作新内容；25:10 的板书未给出统一上界 `M` 的具体取法。
- 本地交付：`output/BV1CAxaeHEeH_p3/formula_auto_20_35/` 下的 `book.reviewed.md`、`book.reviewed.html`、`formulas.reviewed.tex`；自动原稿 `book.md/html` 保留，用于检查模型原始输出。`output/` 被 Git 忽略，不随源码发布。
- 分享版：`output/BV1CAxaeHEeH_p3/formula_auto_20_35/share/` 内有约 1 MB 的单文件 HTML（10 张画面已内嵌）和 5 页 PDF。HTML 可点图放大并跳转原视频，公式排版依赖在线 MathJax；PDF 可离线阅读，但为图片式页面，不支持文本选择。`output/` 被 Git 忽略，分享时直接发送这两个文件。
- 验证：审校版有 10 张有效图片、10 个原视频时间链接、39 处 MathJax 公式；Chrome 中无公式错误和横向溢出。项目测试 25 项通过。每 5 秒抽帧仍可能漏掉短暂出现的公式。
