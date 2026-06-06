import { useMemo, useState } from "react";
import { BadgeCheck, BriefcaseBusiness, RefreshCcw, UserMinus, UserPlus2 } from "lucide-react";

import {
  useAssignStaff,
  useFireStaff,
  useGenerateStaffCandidates,
  useHireStaff,
  useStaff,
  useStaffAssignments,
  useStaffSummary,
} from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { MetricBar } from "../components/MetricBar";
import { useGameStore } from "../store/gameStore";
import { formatVnd, labelize } from "../utils/format";
import type { StaffAssignRequest, StaffCandidate, StaffMember, StaffMemberCreate, StaffRole, StaffTaskType } from "../types/game";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";
import { SectionHeader } from "../components/ui/SectionHeader";

const taskOptions: StaffTaskType[] = [
  "OPERATIONS",
  "CUSTOMER_CONSULT",
  "TEST_BENCH",
  "REFURBISH",
  "RESALE",
  "WARRANTY",
  "PROCUREMENT",
  "MARKET_ANALYSIS",
];

const roleOptions: Array<StaffRole | ""> = [
  "",
  "SALES",
  "MARKETING",
  "TECHNICIAN",
  "REPAIR_SPECIALIST",
  "PROCUREMENT",
  "WARRANTY_SUPPORT",
  "MARKET_ANALYST",
  "OPERATIONS",
];

export function StaffPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const staffQuery = useStaff(saveId);
  const summaryQuery = useStaffSummary(saveId);
  const assignmentsQuery = useStaffAssignments(saveId, 16);
  const generateCandidatesMut = useGenerateStaffCandidates(saveId);
  const hireMut = useHireStaff(saveId);
  const fireMut = useFireStaff(saveId);
  const assignMut = useAssignStaff(saveId);

  const [candidateRole, setCandidateRole] = useState<StaffRole | "">("");
  const [candidateCount, setCandidateCount] = useState(3);
  const [generatedCandidates, setGeneratedCandidates] = useState<StaffCandidate[]>([]);
  const [taskDrafts, setTaskDrafts] = useState<Record<number, StaffTaskType>>({});

  const staff = staffQuery.data ?? [];
  const summary = summaryQuery.data;

  const availableStaff = useMemo(() => staff.filter((member) => member.status === "AVAILABLE"), [staff]);

  const handleGenerateCandidates = async () => {
    try {
      const candidates = await generateCandidatesMut.mutateAsync({
        role: candidateRole || undefined,
        count: candidateCount,
      });
      setGeneratedCandidates(candidates);
    } catch (error) {
      console.error(error);
    }
  };

  const candidateToPayload = (candidate: StaffCandidate): StaffMemberCreate => ({
    name: candidate.name,
    role: candidate.role,
    status: "AVAILABLE",
    level: candidate.level,
    xp: candidate.xp,
    salary_per_day_vnd: candidate.salary_per_day_vnd,
    morale: candidate.morale,
    fatigue: candidate.fatigue,
    traits_json: candidate.traits_json ?? [],
    sales_skill: candidate.sales_skill,
    marketing_skill: candidate.marketing_skill,
    diagnostic_skill: candidate.diagnostic_skill,
    repair_skill: candidate.repair_skill,
    procurement_skill: candidate.procurement_skill,
    support_skill: candidate.support_skill,
    market_skill: candidate.market_skill,
    speed: candidate.speed,
    carefulness: candidate.carefulness,
    hired_on_day: candidate.hired_on_day,
    last_assigned_on_day: candidate.last_assigned_on_day,
    notes: candidate.notes,
  });

  const handleHireCandidate = async (candidate: StaffCandidate) => {
    try {
      await hireMut.mutateAsync(candidateToPayload(candidate));
      setGeneratedCandidates((current) => current.filter((entry) => entry.name !== candidate.name));
    } catch (error) {
      console.error(error);
    }
  };

  const handleFireStaff = async (member: StaffMember) => {
    if (!window.confirm(`Are you sure you want to terminate ${member.name}?`)) return;
    try {
      await fireMut.mutateAsync(member.id);
    } catch (error) {
      console.error(error);
    }
  };

  const handleAssignStaff = async (member: StaffMember) => {
    try {
      const task_type = taskDrafts[member.id] ?? "OPERATIONS";
      const payload: StaffAssignRequest = { task_type };
      await assignMut.mutateAsync({ staffId: member.id, payload });
    } catch (error) {
      console.error(error);
    }
  };

  if (!saveId) {
    return <EmptyState title="No save selected" body="Open a save game before accessing the staff desk." />;
  }

  if (staffQuery.isLoading || summaryQuery.isLoading || assignmentsQuery.isLoading) {
    return <LoadingState />;
  }

  if (staffQuery.isError) return <ErrorState message={(staffQuery.error as Error).message} />;
  if (summaryQuery.isError) return <ErrorState message={(summaryQuery.error as Error).message} />;
  if (assignmentsQuery.isError) return <ErrorState message={(assignmentsQuery.error as Error).message} />;

  return (
    <section className="space-y-4">
      {/* Header and Telemetry */}
      <ConsolePanel variant="z-1" className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <SectionHeader title="Staff Room" subtitle="STATION-09 // PERSONNEL SERVICES" />
          <div className="font-mono text-[10px] text-slate-500 mt-1 uppercase">
            STATUS: <span className="text-[#00f2ff] font-bold">STAFF ON SITE</span> // SYSTEM: ACTIVE
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 font-mono text-[10px] uppercase shrink-0">
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">CREW HEADCOUNT</span>
            <span className="text-white font-bold text-xs">{summary?.staff_count ?? staff.length}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">STAFF AVAILABLE</span>
            <span className="text-[#00f2ff] font-bold text-xs">{summary?.available_staff_count ?? availableStaff.length}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">FATIGUED</span>
            <span className="text-[#ffba20] font-bold text-xs">{staff.filter(s => s.fatigue >= 80).length}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center">
            <span className="text-slate-500 text-[8px] block tracking-wider">DAILY SALARY</span>
            <span className="text-[#00f2ff] font-bold text-xs">{formatVnd(summary?.daily_salary_total_vnd ?? 0)}</span>
          </div>
          <div className="bg-[#0c0e11] border border-white/5 p-2 rounded-sm text-center col-span-2 sm:col-span-1">
            <span className="text-slate-500 text-[8px] block tracking-wider">CANDIDATES</span>
            <span className="text-[#00f2ff] font-bold text-xs">{generatedCandidates.length}</span>
          </div>
        </div>
      </ConsolePanel>

      {/* Main Grid: Crew Health & Candidate Generator */}
      <div className="grid gap-4 xl:grid-cols-[1.1fr_1.1fr]">
        <ConsolePanel variant="z-1" className="p-5 space-y-4">
          <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-2">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Crew Health Monitor</h2>
            <div className="font-mono text-[10px] text-slate-500 uppercase">
              {summary?.strongest_roles?.length ? `Best-fit: ${summary.strongest_roles.map(labelize).join(", ")}` : "No team data yet"}
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <MetricBar label="Average Morale" value={summary?.average_morale ?? null} />
            <MetricBar label="Average Fatigue" value={summary?.average_fatigue ?? null} />
          </div>
          <div className="flex flex-wrap gap-2 pt-2">
            {Object.entries(summary?.role_counts ?? {}).map(([role, count]) => (
              <span key={role} className="border border-white/10 bg-white/[0.03] px-2.5 py-1 text-[10px] text-slate-300 font-mono">
                [{labelize(role)}: {count}]
              </span>
            ))}
          </div>
        </ConsolePanel>

        <ConsolePanel variant="z-1" className="p-5 space-y-4">
          <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Candidate Recruiter Desk</h2>
          <div className="grid gap-2 sm:grid-cols-[1.5fr_1fr_auto]">
            <select
              className="h-10 rounded border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white focus:border-[#00f2ff]/50 focus:outline-none"
              value={candidateRole}
              onChange={(event) => setCandidateRole(event.target.value as StaffRole | "")}
            >
              {roleOptions.map((role) => (
                <option key={role || "ANY"} value={role}>
                  {role ? labelize(role) : "Any role"}
                </option>
              ))}
            </select>
            <select
              className="h-10 rounded border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white focus:border-[#00f2ff]/50 focus:outline-none"
              value={candidateCount}
              onChange={(event) => setCandidateCount(Number(event.target.value))}
            >
              {[1, 2, 3, 4, 5].map((count) => (
                <option key={count} value={count}>
                  {count} Candidate{count > 1 ? "s" : ""}
                </option>
              ))}
            </select>
            <ActionButton
              className="!h-10 !w-auto !px-4"
              onClick={handleGenerateCandidates}
              disabled={generateCandidatesMut.isPending}
            >
              <RefreshCcw className={`h-4 w-4 ${generateCandidatesMut.isPending ? "animate-spin" : ""}`} />
              GENERATE
            </ActionButton>
          </div>

          {generatedCandidates.length === 0 ? (
            <p className="font-mono text-xs text-slate-500 uppercase">Generate a fresh pool to hire from.</p>
          ) : (
            <div className="space-y-3 max-h-[300px] overflow-y-auto console-scrollbar pr-1">
              {generatedCandidates.map((candidate) => (
                <ConsolePanel key={`${candidate.name}-${candidate.role}`} variant="z-2" className="p-4 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/5 pb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-sans text-sm font-bold text-white uppercase tracking-wider">{candidate.name}</h3>
                        <StatusChip label={candidate.role} variant="neutral" />
                      </div>
                      <p className="mt-1 font-mono text-[10px] text-slate-500 uppercase">
                        LEVEL {candidate.level} · SALARY {formatVnd(candidate.salary_per_day_vnd)}/DAY
                      </p>
                    </div>
                    <ActionButton
                      variant="secondary"
                      className="!h-8 !w-auto !px-3 font-mono text-[10px]"
                      onClick={() => handleHireCandidate(candidate)}
                      disabled={hireMut.isPending}
                    >
                      <BadgeCheck className="h-3.5 w-3.5" />
                      HIRE CREW
                    </ActionButton>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <MetricBar label="Morale" value={candidate.morale} />
                    <MetricBar label="Fatigue" value={candidate.fatigue} />
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {(candidate.traits_json ?? []).map((trait) => (
                      <span key={trait} className="border border-[#00f2ff]/20 bg-[#00f2ff]/5 px-2 py-0.5 text-[9px] text-sky-200 font-mono">
                        [{labelize(trait)}]
                      </span>
                    ))}
                  </div>
                  <div className="grid gap-2 grid-cols-2 sm:grid-cols-4">
                    {Object.entries(candidate.preview_effects ?? {}).slice(0, 4).map(([key, value]) => (
                      <div key={key} className="bg-[#0c0e11]/80 border border-white/5 px-2 py-1.5">
                        <span className="block text-[8px] uppercase tracking-wide text-slate-500 font-mono">{labelize(key)}</span>
                        <span className="font-semibold text-white font-mono text-xs">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </ConsolePanel>
              ))}
            </div>
          )}
        </ConsolePanel>
      </div>

      {/* Second Row: Hired Crew & Assignments Log */}
      <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <ConsolePanel variant="z-1" className="p-5 space-y-4">
          <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-2">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Showroom Crew Roster</h2>
            <div className="font-mono text-[10px] text-slate-500 uppercase">{staff.length} TOTAL ON CONTRACT</div>
          </div>
          {staff.length === 0 ? (
            <p className="font-mono text-xs text-slate-500 uppercase">No active staff hired yet. Recruit candidates above.</p>
          ) : (
            <div className="space-y-4 max-h-[600px] overflow-y-auto console-scrollbar pr-1">
              {staff.map((member) => (
                <ConsolePanel key={member.id} variant="z-2" className="p-4 space-y-3">
                  <div className="flex flex-wrap items-start justify-between gap-3 border-b border-white/5 pb-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-sans text-sm font-bold text-white uppercase tracking-wider">{member.name}</h3>
                        <StatusChip
                          label={member.status}
                          variant={member.status === "INACTIVE" ? "error" : member.status === "AVAILABLE" ? "success" : "warning"}
                        />
                      </div>
                      <p className="mt-1 font-mono text-[10px] text-slate-500 uppercase">
                        {labelize(member.role)} · LEVEL {member.level} · {formatVnd(member.salary_per_day_vnd)}/DAY
                      </p>
                    </div>
                    <ActionButton
                      variant="danger"
                      className="!h-8 !w-auto !px-3 font-mono text-[10px]"
                      onClick={() => handleFireStaff(member)}
                      disabled={fireMut.isPending || member.status === "INACTIVE"}
                    >
                      <UserMinus className="h-3.5 w-3.5" />
                      TERMINATE
                    </ActionButton>
                  </div>

                  <div className="grid gap-2 sm:grid-cols-2">
                    <MetricBar label="Morale" value={member.morale} />
                    <MetricBar label="Fatigue" value={member.fatigue} />
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                    {[
                      ["SALES", member.sales_skill],
                      ["REPAIR", member.repair_skill],
                      ["SUPPORT", member.support_skill],
                      ["MARKET", member.market_skill],
                    ].map(([label, value]) => (
                      <div key={label} className="bg-[#0c0e11] border border-white/5 p-2">
                        <div className="font-mono text-[8px] uppercase tracking-wider text-slate-500">{label}</div>
                        <div className="font-mono text-xs font-bold text-[#00f2ff]">{value}</div>
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-wrap gap-1.5">
                    {(member.traits_json ?? []).map((trait) => (
                      <span key={trait} className="border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[9px] text-slate-300 font-mono">
                        [{labelize(trait)}]
                      </span>
                    ))}
                  </div>

                  <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-center pt-2 border-t border-white/5">
                    <select
                      className="h-10 flex-1 rounded border border-white/10 bg-[#0c0e11] px-3 font-mono text-xs text-white focus:border-[#00f2ff]/50 focus:outline-none"
                      value={taskDrafts[member.id] ?? "OPERATIONS"}
                      onChange={(event) =>
                        setTaskDrafts((current) => ({
                          ...current,
                          [member.id]: event.target.value as StaffTaskType,
                        }))
                      }
                    >
                      {taskOptions.map((task) => (
                        <option key={task} value={task}>
                          {labelize(task)}
                        </option>
                      ))}
                    </select>
                    <ActionButton
                      className="!h-10 !w-auto !px-4 sm:flex-initial"
                      onClick={() => handleAssignStaff(member)}
                      disabled={assignMut.isPending || member.status === "INACTIVE"}
                    >
                      <BriefcaseBusiness className="h-4 w-4" />
                      ASSIGN TASK
                    </ActionButton>
                  </div>
                </ConsolePanel>
              ))}
            </div>
          )}
        </ConsolePanel>

        <div className="space-y-4">
          <ConsolePanel variant="z-1" className="p-5">
            <div className="mb-4 flex items-center justify-between gap-3 border-b border-white/5 pb-2">
              <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Assignments Log</h2>
              <div className="font-mono text-[10px] text-slate-500">{assignmentsQuery.data?.length ?? 0} LOGGED</div>
            </div>
            {(assignmentsQuery.data ?? []).length === 0 ? (
              <p className="font-mono text-xs text-slate-500 uppercase">No assignments have been logged yet.</p>
            ) : (
              <div className="space-y-2 max-h-[350px] overflow-y-auto console-scrollbar pr-1">
                {(assignmentsQuery.data ?? []).map((entry) => (
                  <div key={entry.id} className="bg-[#0c0e11] border border-white/5 p-3 rounded-none">
                    <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-1">
                      <div className="font-mono text-xs font-bold text-white">{entry.staff_member?.name ?? `Staff #${entry.staff_member_id}`}</div>
                      <StatusChip label={entry.task_type} variant="neutral" />
                    </div>
                    <p className="mt-2 font-mono text-xs text-[#00f2ff]">{entry.result_summary ?? "No summary provided."}</p>
                    <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 font-mono text-[9px] text-slate-500 uppercase">
                      <span>DAY {entry.assigned_on_day ?? "?"}</span>
                      <span className="text-emerald-400">XP +{entry.xp_gained}</span>
                      <span className="text-amber-400">FATIGUE +{entry.fatigue_gained}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ConsolePanel>

          <ConsolePanel variant="z-1" className="p-5 space-y-3">
            <h2 className="text-xs font-bold font-mono text-white uppercase tracking-wider">Quick Info Desk</h2>
            <div className="space-y-2 font-mono text-xs text-slate-400 uppercase">
              <p className="bg-[#0c0e11]/50 border border-white/5 p-3">
                Hire candidates, assign tasks, and monitor efficiency metrics. Fatigue triggers automatic recovery requirements.
              </p>
              <p className="bg-[#0c0e11]/50 border border-white/5 p-3">
                Refurbish workbench and customer operations panels can assign staff to streamline production rates.
              </p>
            </div>
          </ConsolePanel>
        </div>
      </div>
    </section>
  );
}

