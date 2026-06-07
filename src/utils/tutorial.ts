export function tutorialHighlight(active: boolean) {
  return active
    ? "ring-1 ring-primary-container/60 shadow-[0_0_0_1px_rgba(0,242,255,0.12),0_0_20px_rgba(0,242,255,0.18)]"
    : "ring-1 ring-transparent";
}

export function tutorialPulse(active: boolean) {
  return active ? "animate-pulse" : "";
}

export function tutorialTooltip(active: boolean, text: string) {
  return active ? text : undefined;
}
