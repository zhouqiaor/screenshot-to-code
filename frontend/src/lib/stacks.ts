// Keep in sync with backend (prompts/types.py)
// Order here determines order in dropdown
export enum Stack {
  HTML_TAILWIND = "html_tailwind",
  HTML_CSS = "html_css",
  REACT_TAILWIND = "react_tailwind",
  BOOTSTRAP = "bootstrap",
  VUE_TAILWIND = "vue_tailwind",
  IONIC_TAILWIND = "ionic_tailwind",
  // Native stacks (fork extensions)
  ANDROID_COMPOSE = "android_compose",
  ANDROID_XML = "android_xml",
  A2UI = "a2ui",
  QT_QML = "qt_qml",
  WINDOWS_WPF = "windows_wpf",
  WINUI3 = "winui3",
}

export const STACK_DESCRIPTIONS: {
  [key in Stack]: { components: string[]; inBeta: boolean };
} = {
  html_css: { components: ["HTML", "CSS"], inBeta: false },
  html_tailwind: { components: ["HTML", "Tailwind"], inBeta: false },
  react_tailwind: { components: ["React", "Tailwind"], inBeta: false },
  bootstrap: { components: ["Bootstrap"], inBeta: false },
  vue_tailwind: { components: ["Vue", "Tailwind"], inBeta: true },
  ionic_tailwind: { components: ["Ionic", "Tailwind"], inBeta: true },
  // Native stacks (experimental)
  android_compose: { components: ["Android", "Compose"], inBeta: true },
  android_xml: { components: ["Android", "XML"], inBeta: true },
  a2ui: { components: ["A2UI", "JSONL"], inBeta: true },
  qt_qml: { components: ["Qt", "QML"], inBeta: true },
  windows_wpf: { components: ["WPF", "XAML"], inBeta: true },
  winui3: { components: ["WinUI 3", "XAML"], inBeta: true },
};
