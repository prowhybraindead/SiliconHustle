import { useNavigate } from "react-router-dom";

import { useAcceptQuote, useQuotes, useReleaseQuote, useReserveQuote } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { QuoteCard } from "../components/QuoteCard";
import { useGameStore } from "../store/gameStore";

import { MetricPill } from "../components/ui/MetricPill";

export function QuotesPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const navigate = useNavigate();
  const quotes = useQuotes(saveId);
  const reserveQuote = useReserveQuote(saveId);
  const releaseQuote = useReleaseQuote(saveId);
  const acceptQuote = useAcceptQuote(saveId);
  const isBusy = reserveQuote.isPending || releaseQuote.isPending || acceptQuote.isPending;

  if (!saveId) return <EmptyState title="No command center selected" body="Open a showroom save before building proposals." />;

  const quotesList = quotes.data ?? [];
  const pendingCount = quotesList.filter((q) => q.quote.status === "DRAFT" || q.quote.status === "PRESENTED").length;
  const rejectedCount = quotesList.filter((q) => q.quote.status === "REJECTED" || q.quote.status === "EXPIRED").length;
  const convertedCount = quotesList.filter((q) => q.quote.status === "CONVERTED_TO_ORDER" || q.quote.status === "ACCEPTED").length;

  return (
    <section className="space-y-4">
      {/* Header telemetry strip */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-2 select-none font-mono">
        <div>
          <span className="text-[10px] text-primary-container tracking-widest uppercase block mb-1">
            STATION_06 // SALES PROPOSALS ARCHIVE
          </span>
          <h1 className="font-sans text-2xl font-black text-on-surface uppercase tracking-tighter">
            Quote Review Ledger
          </h1>
        </div>
      </div>

      {/* Persistent Status Indicators */}
      <div className="grid gap-2 grid-cols-3 select-none">
        <MetricPill label="PENDING PROPOSALS" value={pendingCount} />
        <MetricPill label="REJECTED / EXPIRED" value={rejectedCount} />
        <MetricPill label="CONVERTED ORDERS" value={convertedCount} />
      </div>

      {quotes.isLoading ? <LoadingState /> : null}
      {quotes.isError ? <ErrorState message={(quotes.error as Error).message} /> : null}
      {(reserveQuote.isError || releaseQuote.isError || acceptQuote.isError) && (
        <ErrorState message={((reserveQuote.error || releaseQuote.error || acceptQuote.error) as Error).message} />
      )}
      {quotesList.length === 0 ? (
        <EmptyState
          title="No quotes yet"
          body="Generate a quote from a customer request to start the build loop."
        />
      ) : null}

      <div className="grid gap-4">
        {quotesList.map((detail) => (
          <QuoteCard
            detail={detail}
            isBusy={isBusy}
            key={detail.quote.id}
            onAccept={(quoteId) => acceptQuote.mutate(quoteId)}
            onOpenChat={(conversationId) => navigate(`/customer-chat?conversationId=${conversationId}`)}
            onRelease={(quoteId) => releaseQuote.mutate(quoteId)}
            onReserve={(quoteId) => reserveQuote.mutate(quoteId)}
          />
        ))}
      </div>
    </section>
  );
}
