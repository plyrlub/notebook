// 自定义 Mermaid 配置：放大图内文字，提升可读性
// 由 build_prepare.py 拷贝到 docs/javascripts/mermaid.mjs，并在 mkdocs.yml extra_javascript 引用
// 官方定制入口：https://squidfunk.github.io/mkdocs-material/reference/diagrams/#customization
import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';

mermaid.initialize({
  startOnLoad: false,
  securityLevel: "loose",
  // 顶层 fontSize 放大所有图文本（默认 16 偏小）
  fontSize: 20,
  themeVariables: {
    fontSize: "20px",
    // 流程图节点文字
    nodeTextColor: "#111111",
    primaryTextColor: "#111111",
    // 线条标签
    edgeLabelBackground: "#ffffff",
  },
  flowchart: {
    htmlLabels: true,
    nodeSpacing: 40,
    rankSpacing: 40,
    padding: 12,
  },
  sequence: {
    messageFontSize: "20px",
    noteFontSize: "20px",
    actorFontSize: "20px",
  },
  class: {
    fontSize: 20,
  },
  state: {
    fontSize: 20,
  },
  er: {
    fontSize: 20,
  },
});

// 必须挂到 window，Material for MkDocs 才能识别并使用这个实例
window.mermaid = mermaid;
