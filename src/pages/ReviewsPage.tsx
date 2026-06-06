import { useState } from "react";
import { Link } from "react-router-dom";
import { RefreshCw, Sparkles, Star } from "lucide-react";

import { useGenerateReview, useReputationSummary, useReviews } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useGameStore } from "../store/gameStore";
import { formatVnd, labelize } from "../utils/format";
import type { CustomerReview, ReviewSentiment, ReviewSourceType } from "../types/game";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

const sourceOptions: Array<{ value: ReviewSourceType | "ALL"; label: string }> = [
  { value: "ALL", label: "All sources" },
  { value: "ORDER_DELIVERY", label: "Order delivery" },
  { value: "RESALE_SALE", label: "Resale sale" },
  { value: "WARRANTY_RMA", label: "Warranty RMA" },
];

const sentimentOptions: Array<{ value: ReviewSentiment | "ALL"; label: string }> = [
  { value: "ALL", label: "All sentiment" },
  { value: "POSITIVE", label: "Positive" },
  { value: "NEUTRAL", label: "Neutral" },
  { value: "NEGATIVE", label: "Negative" },
];

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex items-center gap-0.5 select-none">
      {Array.from({ length: 5 }, (_, index) => (
        <span
          key={index}
          className={`font-mono text-sm ${index < rating ? "text-[#ffba20]" : "text-slate-600"}`}
        >
          ★
        </span>
      ))}
    </div>
  );
}

function ReviewCard({ review }: { review: CustomerReview }) {
  const deltaTone = review.reputation_delta > 0 ? "text-emerald-400" : review.reputation_delta < 0 ? "text-rose-400" : "text-slate-500";
  return (
    <ConsolePanel variant="z-2" className="p-4 space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between border-b border-white/5 pb-2">
        <div className="space-y-1.5">
          <div className="flex flex-wrap items-center gap-1.5 font-mono text-[9px]">
            <StatusChip label={review.source_type} variant="neutral" />
            <StatusChip
              label={review.sentiment}
              variant={
                review.sentiment === "POSITIVE"
                  ? "success"
                  : review.sentiment === "NEGATIVE"
                    ? "error"
                    : "warning"
              }
            />
            {review.persona_type ? <StatusChip label={review.persona_type} variant="neutral" /> : null}
          </div>
          <div>
            <h3 className="font-sans text-sm font-bold text-white uppercase tracking-wider">{review.title}</h3>
            <div className="mt-1.5 flex flex-wrap items-center gap-3">
              <StarRating rating={review.rating} />
              <span className="font-mono text-[9px] text-slate-500 tracking-wider">ID: {review.source_key}</span>
            </div>
          </div>
        </div>
        <div className={`font-mono text-xs font-bold ${deltaTone} shrink-0 uppercase`}>
          {review.reputation_delta >= 0 ? "+" : ""}
          {review.reputation_delta} REP DELTA
        </div>
      </div>

      <p className="font-mono text-xs text-slate-300 leading-relaxed uppercase">{review.body}</p>

      <div className="flex flex-wrap gap-1.5">
        {(review.tags_json ?? []).map((tag) => (
          <span key={tag} className="border border-white/10 bg-slate-900/40 px-2 py-0.5 text-[9px] font-mono text-slate-300">
            [{labelize(tag)}]
          </span>
        ))}
      </div>

      <div className="grid gap-2 text-[10px] font-mono text-slate-400 sm:grid-cols-2 uppercase">
        <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm">
          <span className="block text-slate-500 text-[8px]">SOURCE RECORD</span>
          <span className="mt-0.5 block text-slate-200">{review.source_summary ?? "NO DETAILS"}</span>
        </div>
        <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm">
          <span className="block text-slate-500 text-[8px]">TRANSACTION SNAPSHOT</span>
          <span className="mt-0.5 block text-slate-200">
            {review.final_price_vnd !== null && review.final_price_vnd !== undefined ? formatVnd(review.final_price_vnd) : "NO PRICE DATA"}
            {review.build_quality_score !== null && review.build_quality_score !== undefined ? ` • QUAL: ${review.build_quality_score}/100` : ""}
          </span>
        </div>
      </div>
    </ConsolePanel>
  );
}

export function ReviewsPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const [sourceFilter, setSourceFilter] = useState<ReviewSourceType | "ALL">("ALL");
  const [sentimentFilter, setSentimentFilter] = useState<ReviewSentiment | "ALL">("ALL");
  const summaryQuery = useReputationSummary(saveId);
  const reviewsQuery = useReviews(saveId, {
    sourceType: sourceFilter === "ALL" ? undefined : sourceFilter,
    sentiment: sentimentFilter === "ALL" ? undefined : sentimentFilter,
  });
  const generateMutation = useGenerateReview(saveId);

  if (!saveId) return <EmptyState title="No save selected" body="Open or create a save game from the home screen." />;
  if (summaryQuery.isLoading || reviewsQuery.isLoading) return <LoadingState />;
  if (summaryQuery.isError) return <ErrorState message={(summaryQuery.error as Error).message} />;
  if (reviewsQuery.isError) return <ErrorState message={(reviewsQuery.error as Error).message} />;

  const summary = summaryQuery.data;
  const reviews = reviewsQuery.data ?? [];

  return (
    <section className="space-y-4">
      {/* Header and Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Reputation Terminal" subtitle="STATION-11 // PUBLIC FEEDBACK" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">MONITORING REVIEWS</span> // FILTER ACTIVE: {sourceFilter} / {sentimentFilter}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">REPUTATION SCORE</span>
            <span className="text-emerald-400 font-bold text-xs">{summary?.reputation ?? 0}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">TOTAL REVIEWS</span>
            <span className="text-white font-bold text-xs">{summary?.total_reviews ?? 0}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">AVERAGE RATING</span>
            <span className="text-[#ffba20] font-bold text-xs">{(summary?.average_rating ?? 0).toFixed(2)} ★</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">POSITIVE COUNT</span>
            <span className="text-[#00f2ff] font-bold text-xs">{summary?.positive_reviews ?? 0}</span>
          </div>
        </div>
      </ConsolePanel>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.6fr]">
        {/* Left Column: Stats and Filters */}
        <div className="space-y-4">
          <ConsolePanel variant="z-1" className="p-4 space-y-4">
            <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-2">
              <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Sentiment Summary</h2>
              <Link className="font-mono text-[10px] text-[#00f2ff] uppercase hover:underline" to="/dashboard">
                RETURN TO COMMAND
              </Link>
            </div>
            <div className="grid gap-2 grid-cols-2 font-mono text-[10px] uppercase">
              <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
                <span className="text-emerald-400 text-[8px] block tracking-wider">POSITIVE</span>
                <span className="text-white font-bold text-sm">{summary?.positive_reviews ?? 0}</span>
              </div>
              <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
                <span className="text-[#ffba20] text-[8px] block tracking-wider">NEUTRAL</span>
                <span className="text-white font-bold text-sm">{summary?.neutral_reviews ?? 0}</span>
              </div>
              <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
                <span className="text-rose-400 text-[8px] block tracking-wider">NEGATIVE</span>
                <span className="text-white font-bold text-sm">{summary?.negative_reviews ?? 0}</span>
              </div>
              <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
                <span className="text-slate-500 text-[8px] block tracking-wider">PUBLIC COUNT</span>
                <span className="text-white font-bold text-sm">{reviews.filter((review) => review.is_public).length}</span>
              </div>
            </div>
            <div className="bg-[#0c0e11]/80 border border-white/5 p-3 rounded-none font-mono text-xs text-slate-300 uppercase">
              <span className="text-slate-500 block text-[8px] mb-1">AGGREGATED FEEDBACK METRICS</span>
              {summary?.average_rating !== null && summary?.average_rating !== undefined
                ? `${summary.average_rating.toFixed(2)} AVERAGE SCALE ACROSS ${summary.total_reviews} AUDITS`
                : "NO REVIEW DATA LOGGED YET"}
            </div>
          </ConsolePanel>

          <ConsolePanel variant="z-1" className="p-4 space-y-4">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2">Filter & Query Desk</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5 font-mono text-[10px] uppercase">
                <span className="text-slate-500 text-[8px]">FILTER BY SOURCE</span>
                <select
                  className="w-full h-10 rounded border border-white/10 bg-[#0c0e11] px-3 text-xs text-slate-100 focus:border-[#00f2ff]/50 focus:outline-none"
                  value={sourceFilter}
                  onChange={(event) => setSourceFilter(event.target.value as ReviewSourceType | "ALL")}
                >
                  {sourceOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5 font-mono text-[10px] uppercase">
                <span className="text-slate-500 text-[8px]">FILTER BY SENTIMENT</span>
                <select
                  className="w-full h-10 rounded border border-white/10 bg-[#0c0e11] px-3 text-xs text-slate-100 focus:border-[#00f2ff]/50 focus:outline-none"
                  value={sentimentFilter}
                  onChange={(event) => setSentimentFilter(event.target.value as ReviewSentiment | "ALL")}
                >
                  {sentimentOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <ActionButton
              onClick={() => generateMutation.mutate({ source_type: sourceFilter === "ALL" ? undefined : sourceFilter })}
              disabled={generateMutation.isPending}
            >
              <RefreshCw className={`h-4 w-4 ${generateMutation.isPending ? "animate-spin" : ""}`} />
              {generateMutation.isPending ? "COMPILING RECORD..." : "COMPILE NEW REVIEW"}
            </ActionButton>
          </ConsolePanel>

          <ConsolePanel variant="z-1" className="p-4 space-y-3">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider border-b border-white/5 pb-2">Source Channels Mix</h2>
            <div className="space-y-2">
              {Object.entries(summary?.source_counts ?? {}).map(([source, count]) => (
                <div key={source} className="flex items-center justify-between bg-[#0c0e11] border border-white/5 px-3 py-2 font-mono text-xs">
                  <span className="text-slate-400 uppercase">{labelize(source)}</span>
                  <span className="font-bold text-[#00f2ff]">{count}</span>
                </div>
              ))}
              {Object.keys(summary?.source_counts ?? {}).length === 0 ? (
                <p className="font-mono text-xs text-slate-500 uppercase">No review channels mapped.</p>
              ) : null}
            </div>
          </ConsolePanel>
        </div>

        {/* Right Column: Reviews Queue */}
        <ConsolePanel variant="z-1" className="p-4 space-y-4">
          <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-2">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Reputation Database logs</h2>
            <span className="font-mono text-[10px] text-slate-500 uppercase">{reviews.length} RECORDS SHOWING</span>
          </div>
          {reviews.length === 0 ? (
            <EmptyState
              title="No records found"
              body="Generate or wait for customer reviews from finished transactions."
            />
          ) : (
            <div className="space-y-4 max-h-[700px] overflow-y-auto console-scrollbar pr-1">
              {reviews.map((review) => (
                <ReviewCard key={review.id} review={review} />
              ))}
            </div>
          )}
        </ConsolePanel>
      </div>
    </section>
  );
}
