import { translateUiText } from "../utils/format";

export function LoadingState() {
  return <div className="panel rounded-lg p-6 font-mono text-sm text-tech-blue">{translateUiText("loading module...")}</div>;
}
