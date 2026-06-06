import clsx from "clsx";

type BrandWordmarkSize = "sm" | "md" | "lg" | "xl";

type BrandWordmarkProps = {
  className?: string;
  imgClassName?: string;
  size?: BrandWordmarkSize;
  eager?: boolean;
};

const sizeClasses: Record<BrandWordmarkSize, string> = {
  sm: "h-5",
  md: "h-7",
  lg: "h-10",
  xl: "h-14",
};

export function BrandWordmark({ className, imgClassName, size = "md", eager = false }: BrandWordmarkProps) {
  return (
    <picture className={clsx("inline-flex shrink-0 items-center", className)}>
      <source media="(prefers-color-scheme: dark)" srcSet="/logo/SilHus_W.svg" />
      <source media="(prefers-color-scheme: light)" srcSet="/logo/SilHus_B.svg" />
      <img
        alt="Silicon Hustle"
        className={clsx("block w-auto select-none object-contain", sizeClasses[size], imgClassName)}
        decoding="async"
        loading={eager ? "eager" : "lazy"}
        src="/logo/SilHus_W.svg"
      />
    </picture>
  );
}
