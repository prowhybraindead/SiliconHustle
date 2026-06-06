interface ErrorStateProps {
  message?: string;
}

export function ErrorState({ message = "Something went wrong while syncing with the backend." }: ErrorStateProps) {
  return <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">{message}</div>;
}
