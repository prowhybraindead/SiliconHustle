export function formatVnd(value: number | null | undefined): string {
  if (value === null || value === undefined) return "?";
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatVndCompact(value: number | null | undefined): string {
  if (value === null || value === undefined) return "?";

  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";

  if (abs >= 1_000_000_000) {
    return `${sign}₫${(abs / 1_000_000_000).toLocaleString("en-US", { maximumFractionDigits: 1 })}B`;
  }

  if (abs >= 1_000_000) {
    return `${sign}₫${(abs / 1_000_000).toLocaleString("en-US", { maximumFractionDigits: 1 })}M`;
  }

  if (abs >= 1_000) {
    return `${sign}₫${(abs / 1_000).toLocaleString("en-US", { maximumFractionDigits: 1 })}K`;
  }

  return `${sign}₫${abs.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

export function labelize(value: string): string {
  return value.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (letter: string) => letter.toUpperCase());
}

export function formatCurrency(value: number | null | undefined, currency: string): string {
  if (value === null || value === undefined) return "?";
  const cur = currency.toUpperCase();
  if (cur === "VND") {
    return formatVnd(value);
  }
  try {
    return new Intl.NumberFormat(getLocaleForCurrency(cur), {
      style: "currency",
      currency: cur,
    }).format(value);
  } catch {
    return `${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${cur}`;
  }
}

export function formatFxRate(rate: number | null | undefined, base: string, quote: string): string {
  if (rate === null || rate === undefined) return "?";
  return `1 ${base} = ${rate.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })} ${quote}`;
}

function getLocaleForCurrency(currency: string): string {
  switch (currency) {
    case "USD": return "en-US";
    case "EUR": return "de-DE";
    case "JPY": return "ja-JP";
    case "CNY": return "zh-CN";
    case "TWD": return "zh-TW";
    case "HKD": return "zh-HK";
    case "KRW": return "ko-KR";
    case "SGD": return "en-SG";
    case "THB": return "th-TH";
    default: return "en-US";
  }
}
