// UI-only stack enum. Order here determines order in the dropdown.
//
// NOTE: This enum is NOT the source of truth for backend generation. The
// backend's canonical Stack Literal lives in `backend/prompts/prompt_types.py`.
// The 6 Native stacks (android_compose / android_xml / a2ui / qt_qml /
// windows_wpf / winui3) are generated & validated by backend scripts
// (generate_5stacks.py, agent/tools/validate_code.py, e2e_*) — NOT through
// this UI. Only `android_compose` is wired into the main UI pipeline; the
// other 5 are intentionally absent here so the dropdown never offers a dead
// option (backend would reject them with "Invalid generated code config").
// See AGENTS.md → "Stack generation paths" before re-adding any Native entry.
export enum Stack {
  HTML_TAILWIND = "html_tailwind",
  HTML_CSS = "html_css",
  REACT_TAILWIND = "react_tailwind",
  BOOTSTRAP = "bootstrap",
  VUE_TAILWIND = "vue_tailwind",
  IONIC_TAILWIND = "ionic_tailwind",
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
};
