import { Zap } from "lucide-react";

import type { InventoryUnit } from "../types/game";
import { formatVnd, labelize } from "../utils/format";
import { BrandLogo } from "./BrandLogo";
import { MetricBar } from "./MetricBar";
import { StatusChip } from "./ui/StatusChip";
import { ConsolePanel } from "./ui/ConsolePanel";
import { ActionButton } from "./ui/ActionButton";

interface InventoryUnitCardProps {
  unit: InventoryUnit;
  onRunTest: (unitId: number, action: string) => void;
  isTesting?: boolean;
}

const tests = [
  ["Basic Check", "basic-check"],
  ["Benchmark", "benchmark"],
  ["Stress Test", "stress-test"],
  ["Full Inspection", "full-inspection"],
] as const;

export function InventoryUnitCard({ unit, onRunTest, isTesting }: InventoryUnitCardProps) {
  // Safe extraction of condition to ensure hidden_condition_json or raw defects are never rendered
  const isNew = unit.condition_type === "NEW";
  const isDefective = unit.status === "DEFECTIVE";

  return (
    <ConsolePanel variant="z-1" className="flex flex-col gap-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-3">
          <BrandLogo brand={unit.product.brand_ref} logoUrl={unit.product.effective_logo_url} name={unit.product.brand} />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="font-semibold text-white font-mono">{unit.product.name}</h3>
              <StatusChip label={unit.product.category} variant="neutral" />
              <StatusChip label={unit.condition_type} variant={isNew ? "success" : "warning"} />
              <StatusChip label={unit.status} variant={isDefective ? "error" : "success"} />
              {unit.ready_for_resale && (
                <StatusChip label="READY FOR RESALE" variant="success" />
              )}
              {unit.refurbish_count > 0 && (
                <StatusChip label={`REFURBISHED (${unit.refurbish_count})`} variant="neutral" />
              )}
            </div>
            <p className="mt-2 text-sm text-slate-400 font-mono">
              {unit.product.brand} / {unit.serial_number ?? "No serial"} / GRADE {labelize(unit.grade)}
            </p>
            <p className="mt-1 text-xs text-slate-500 font-mono">
              COST {formatVnd(unit.purchase_price_vnd)} / LIST {unit.listed_price_vnd ? formatVnd(unit.listed_price_vnd) : "N/A"} / CONFIDENCE {unit.inspection_confidence}%
            </p>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {tests.map(([label, action]) => (
            <ActionButton
              key={action}
              variant="secondary"
              className="!h-9 !w-auto !px-3 font-mono text-[11px]"
              disabled={isTesting}
              onClick={() => onRunTest(unit.id, action)}
            >
              <Zap className="h-3.5 w-3.5 text-primary-container" />
              {label}
            </ActionButton>
          ))}
        </div>
      </div>
      
      {/* Metric telemetry board */}
      <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricBar label="Health" value={unit.health_score} />
        <MetricBar label="Performance" value={unit.performance_score} />
        <MetricBar label="Thermal" value={unit.thermal_score} />
        <MetricBar label="Fan" value={unit.fan_score} />
        <MetricBar label="VRAM" value={unit.vram_score} />
        <MetricBar label="Stability" value={unit.stability_score} />
        <MetricBar label="Warranty Risk" value={unit.warranty_risk} />
        <MetricBar label="Hidden Defect" value={unit.hidden_defect_revealed ? "REVEALED" : "?"} />
      </div>
    </ConsolePanel>
  );
}

