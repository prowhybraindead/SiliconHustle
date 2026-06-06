import { useNavigate } from "react-router-dom";

import { useDeliverOrder, useOpenWarrantyClaim, useOrders, useRunOrderBuildTest, useStartOrderBuild } from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { OrderCard } from "../components/OrderCard";
import { useGameStore } from "../store/gameStore";

import { MetricPill } from "../components/ui/MetricPill";

export function OrdersPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const navigate = useNavigate();
  const orders = useOrders(saveId);
  const startBuild = useStartOrderBuild(saveId);
  const runBuildTest = useRunOrderBuildTest(saveId);
  const deliverOrder = useDeliverOrder(saveId);
  const openWarranty = useOpenWarrantyClaim(saveId);
  const isBusy = startBuild.isPending || runBuildTest.isPending || deliverOrder.isPending || openWarranty.isPending;

  if (!saveId) return <EmptyState title="No save selected" body="Open a save before reviewing orders." />;

  const ordersList = orders.data ?? [];
  const acceptedCount = ordersList.filter((o) => o.status === "ACCEPTED").length;
  const buildCount = ordersList.filter((o) => o.status === "IN_PROGRESS").length;
  const testingCount = ordersList.filter((o) => o.status === "TESTING").length;
  const deliveredCount = ordersList.filter((o) => o.status === "DELIVERED").length;

  return (
    <section className="space-y-4">
      {/* Header section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-2 select-none font-mono">
        <div>
          <span className="text-[10px] text-primary-container tracking-widest uppercase block mb-1">
            STATION_03 // ORDER ASSEMBLY BAY
          </span>
          <h1 className="font-sans text-2xl font-black text-on-surface uppercase tracking-tighter">
            Fulfillment Queue
          </h1>
        </div>
      </div>

      {/* Persistent Status Telemetry */}
      <div className="grid gap-2 grid-cols-2 lg:grid-cols-4 select-none">
        <MetricPill label="AWAITING ASSEMBLY" value={acceptedCount} />
        <MetricPill label="IN PROGRESS" value={buildCount} />
        <MetricPill label="DIAGNOSTICS / TESTING" value={testingCount} />
        <MetricPill label="COMPLETED / DISPATCHED" value={deliveredCount} />
      </div>

      {orders.isLoading ? <LoadingState /> : null}
      {orders.isError ? <ErrorState message={(orders.error as Error).message} /> : null}
      {(startBuild.isError || runBuildTest.isError || deliverOrder.isError || openWarranty.isError) && (
        <ErrorState message={((startBuild.error || runBuildTest.error || deliverOrder.error || openWarranty.error) as Error).message} />
      )}
      {ordersList.length === 0 ? (
        <EmptyState title="No orders yet" body="Generate and accept a quote to create an accepted order." />
      ) : null}

      <div className="grid gap-4">
        {ordersList.map((order) => (
          <OrderCard
            isBusy={isBusy}
            key={order.id}
            onDeliver={(orderId) => deliverOrder.mutate({ orderId })}
            onOpenWarranty={(payload) => openWarranty.mutate(payload, { onSuccess: () => navigate("/warranty") })}
            onRunBuildTest={(orderId) => runBuildTest.mutate(orderId)}
            onStartBuild={(orderId) => startBuild.mutate(orderId)}
            order={order}
            saveId={saveId}
          />
        ))}
      </div>
    </section>
  );
}
