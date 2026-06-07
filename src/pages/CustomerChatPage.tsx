import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  useAssignConversationStaff,
  useCloseConversation,
  useConversationMessages,
  useCreateConversationForRequest,
  useCustomerConversations,
  useCustomerRequests,
  useMarkConversationReadyToOrder,
  useQuickReplyConversation,
  useQuotes,
  useSendConversationMessage,
  useSendQuoteToConversation,
  useStaff,
} from "../api/hooks";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useGameStore } from "../store/gameStore";
import { labelize } from "../utils/format";
import { tutorialHighlight, tutorialTooltip } from "../utils/tutorial";
import type { CustomerConversation, CustomerConversationMessage, ConversationActionType, UiLanguage } from "../types/game";

import { ConsolePanel } from "../components/ui/ConsolePanel";
import { StatusChip } from "../components/ui/StatusChip";
import { ActionButton } from "../components/ui/ActionButton";

const QUICK_ACTIONS: { action: ConversationActionType; label: string; variant: "primary" | "secondary" | "danger" }[] = [
  { action: "ASK_BUDGET", label: "Hỏi ngân sách", variant: "secondary" },
  { action: "ASK_USE_CASE", label: "Hỏi mục đích", variant: "secondary" },
  { action: "ASK_USED_PARTS", label: "Hỏi linh kiện cũ", variant: "secondary" },
  { action: "RECOMMEND_VALUE_BUILD", label: "Gợi ý tối ưu", variant: "secondary" },
  { action: "RECOMMEND_ALL_NEW_BUILD", label: "Gợi ý toàn đồ mới", variant: "secondary" },
  { action: "EXPLAIN_WARRANTY_RISK", label: "Giải thích bảo hành", variant: "secondary" },
  { action: "GENERATE_QUOTE", label: "Tạo báo giá", variant: "primary" },
];

function getLocalizedQuickActions(language: UiLanguage) {
  if (language === "en") {
    return [
      { action: "ASK_BUDGET", label: "Ask budget", variant: "secondary" },
      { action: "ASK_USE_CASE", label: "Ask use case", variant: "secondary" },
      { action: "ASK_USED_PARTS", label: "Ask used parts", variant: "secondary" },
      { action: "RECOMMEND_VALUE_BUILD", label: "Suggest value build", variant: "secondary" },
      { action: "RECOMMEND_ALL_NEW_BUILD", label: "Suggest all-new build", variant: "secondary" },
      { action: "EXPLAIN_WARRANTY_RISK", label: "Explain warranty", variant: "secondary" },
      { action: "GENERATE_QUOTE", label: "Generate quote", variant: "primary" },
    ] as const;
  }

  return [
    { action: "ASK_BUDGET", label: "Hỏi ngân sách", variant: "secondary" },
    { action: "ASK_USE_CASE", label: "Hỏi mục đích", variant: "secondary" },
    { action: "ASK_USED_PARTS", label: "Hỏi linh kiện cũ", variant: "secondary" },
    { action: "RECOMMEND_VALUE_BUILD", label: "Gợi ý tối ưu", variant: "secondary" },
    { action: "RECOMMEND_ALL_NEW_BUILD", label: "Gợi ý toàn đồ mới", variant: "secondary" },
    { action: "EXPLAIN_WARRANTY_RISK", label: "Giải thích bảo hành", variant: "secondary" },
    { action: "GENERATE_QUOTE", label: "Tạo báo giá", variant: "primary" },
  ] as const;
}

export function CustomerChatPage() {
  const saveId = useGameStore((state) => state.selectedSaveId);
  const uiLanguage = useGameStore((state) => state.uiLanguage);
  const tutorialMode = useGameStore((state) => state.tutorialMode);
  const tutorialStep = useGameStore((state) => state.tutorialStep);
  const [searchParams, setSearchParams] = useSearchParams();
  
  const conversationsQuery = useCustomerConversations(saveId);
  const requestsQuery = useCustomerRequests(saveId);
  const quotesQuery = useQuotes(saveId);
  const staffQuery = useStaff(saveId);
  const createConversation = useCreateConversationForRequest(saveId);
  const sendMessage = useSendConversationMessage(saveId);
  const quickReply = useQuickReplyConversation(saveId);
  const assignStaff = useAssignConversationStaff(saveId);
  const sendQuote = useSendQuoteToConversation(saveId);
  const readyToOrder = useMarkConversationReadyToOrder(saveId);
  const closeConversation = useCloseConversation(saveId);
  
  const [draft, setDraft] = useState("");
  const [selectedQuoteId, setSelectedQuoteId] = useState<number | null>(null);
  const quickActions = useMemo(() => getLocalizedQuickActions(uiLanguage), [uiLanguage]);
  const chatCopy = useMemo(
    () =>
      uiLanguage === "en"
        ? {
            noSaveTitle: "No save selected",
            noSaveBody: "Open a save before using customer chat.",
            quickActionTitle: "QUICK ACTIONS",
            placeholder: "Type a message for the customer...",
            send: "SEND MESSAGE",
            ready: "READY TO ORDER",
            closeWon: "CLOSE - WON",
            closeLost: "CLOSE - LOST",
            staffTitle: "STAFF ASSIGNMENT",
            staffPlaceholder: "Assign a staff member...",
            sendProposal: "SEND QUOTE",
            emptyConversationTitle: "No conversation selected",
            emptyConversationBody: "Pick a thread from the left or open one from Customers.",
          }
        : {
            noSaveTitle: "Chưa chọn bản lưu",
            noSaveBody: "Mở một bản lưu trước khi dùng chat khách hàng.",
            quickActionTitle: "TÁC VỤ NHANH",
            placeholder: "Nhập nội dung tư vấn cho khách...",
            send: "GỬI TIN NHẮN",
            ready: "SẴN SÀNG ĐẶT HÀNG",
            closeWon: "ĐÓNG - THẮNG",
            closeLost: "ĐÓNG - THUA",
            staffTitle: "PHÂN CÔNG NHÂN SỰ",
            staffPlaceholder: "Phân công nhân sự...",
            sendProposal: "GỬI BÁO GIÁ",
            emptyConversationTitle: "Chưa chọn cuộc trò chuyện",
            emptyConversationBody: "Chọn một luồng ở bên trái hoặc mở từ Khách hàng.",
          },
    [uiLanguage],
  );

  const selectedConversationId = searchParams.get("conversationId") ? Number(searchParams.get("conversationId")) : null;
  const conversations = conversationsQuery.data ?? [];
  const selectedConversation = conversations.find((conversation) => conversation.id === selectedConversationId) ?? conversations[0] ?? null;
  const conversationMessagesQuery = useConversationMessages(saveId, selectedConversation?.id ?? null);
  const request = selectedConversation?.customer_request ?? requestsQuery.data?.find((item) => item.id === selectedConversation?.customer_request_id) ?? null;
  
  const filteredQuotes = useMemo(() => {
    if (!request) return quotesQuery.data ?? [];
    return (quotesQuery.data ?? []).filter((detail) => detail.quote.customer_request_id === request.id);
  }, [quotesQuery.data, request]);

  useEffect(() => {
    if (!selectedConversation && conversations.length > 0) {
      setSearchParams({ conversationId: String(conversations[0].id) }, { replace: true });
    }
  }, [conversations, selectedConversation, setSearchParams]);

  useEffect(() => {
    if (!selectedConversationId && selectedConversation) {
      setSearchParams({ conversationId: String(selectedConversation.id) }, { replace: true });
    }
  }, [selectedConversation, selectedConversationId, setSearchParams]);

  useEffect(() => {
    if (filteredQuotes.length > 0 && !filteredQuotes.some((detail) => detail.quote.id === selectedQuoteId)) {
      setSelectedQuoteId(filteredQuotes[0].quote.id);
    }
  }, [filteredQuotes, selectedQuoteId]);

  if (!saveId) {
    return <EmptyState title={chatCopy.noSaveTitle} body={chatCopy.noSaveBody} />;
  }

  if (conversationsQuery.isLoading || requestsQuery.isLoading || quotesQuery.isLoading || staffQuery.isLoading) {
    return <LoadingState />;
  }

  if (conversationsQuery.isError || requestsQuery.isError || quotesQuery.isError || staffQuery.isError) {
    return (
      <ErrorState
        message={String(
          (conversationsQuery.error || requestsQuery.error || quotesQuery.error || staffQuery.error || new Error("Unable to load customer chat")).message,
        )}
      />
    );
  }

  async function openConversationForRequest(requestId: number) {
    const response = await createConversation.mutateAsync(requestId);
    setSearchParams({ conversationId: String(response.conversation.id) });
  }

  async function handleSendMessage() {
    if (!selectedConversation || !draft.trim()) return;
    await sendMessage.mutateAsync({ conversationId: selectedConversation.id, body: draft.trim() });
    setDraft("");
  }

  async function handleQuickReply(actionType: ConversationActionType) {
    if (!selectedConversation) return;
    await quickReply.mutateAsync({ conversationId: selectedConversation.id, actionType });
  }

  async function handleAssignStaff(staffId: number) {
    if (!selectedConversation) return;
    await assignStaff.mutateAsync({ conversationId: selectedConversation.id, staffId });
  }

  async function handleSendQuote() {
    if (!selectedConversation || !selectedQuoteId) return;
    await sendQuote.mutateAsync({ conversationId: selectedConversation.id, quoteId: selectedQuoteId });
  }

  async function handleReadyToOrder() {
    if (!selectedConversation) return;
    await readyToOrder.mutateAsync(selectedConversation.id);
  }

  async function handleClose(won: boolean) {
    if (!selectedConversation) return;
    await closeConversation.mutateAsync({ conversationId: selectedConversation.id, won });
  }

  function getStatusVariant(status: string): "success" | "warning" | "error" | "neutral" {
    switch (status) {
      case "READY_TO_ORDER":
      case "CLOSED_WON":
        return "success";
      case "QUOTE_PROPOSED":
      case "WAITING_FOR_CUSTOMER":
        return "warning";
      case "CLOSED_LOST":
        return "error";
      default:
        return "neutral";
    }
  }

  return (
    <section className="space-y-4">
      {/* Header section */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 mb-2 select-none">
        <div>
          <span className="font-mono text-[10px] text-primary-container tracking-widest uppercase block mb-1">
            STATION_05 // CUSTOMER CONSULTATION DESK
          </span>
          <h1 className="font-sans text-2xl font-black text-on-surface uppercase tracking-tighter">
            Operational Comms Terminal
          </h1>
        </div>
        <div className="flex items-center gap-3">
          {selectedConversation && (
            <div className="flex items-center gap-2 font-mono text-[10px]">
              <span className="bg-[#090b0e] border border-white/10 px-2 py-1 text-on-surface font-bold">
                {uiLanguage === "en" ? "ENG" : "VIE"}
              </span>
              <StatusChip label={selectedConversation.status} variant={getStatusVariant(selectedConversation.status)} />
              <StatusChip label={selectedConversation.stage} variant="neutral" />
              <span className="bg-[#090b0e] border border-white/10 px-2 py-1 text-on-surface font-bold">
                FIT CHANCE: {selectedConversation.conversion_probability ?? 0}%
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[280px_1fr]">
        {/* Left Side: Threads & Incoming Requests list */}
        <aside className="space-y-4 select-none">
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
            <div className="flex justify-between items-center border-b border-white/10 pb-2">
              <span className="text-[10px] text-outline uppercase">LUỒNG TRAO ĐỔI ĐANG MỞ</span>
              <span className="text-[9px] text-primary-container">[{conversations.length} OPEN]</span>
            </div>
            <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1 console-scrollbar">
              {conversations.length === 0 ? (
                <p className="text-outline/40 italic font-mono text-center p-4">CHƯA CÓ LUỒNG TRAO ĐỔI NÀO</p>
              ) : (
                conversations.map((conversation) => (
                  <button
                    key={conversation.id}
                    className={`w-full rounded-none border text-left p-2.5 transition duration-150 cursor-pointer flex flex-col font-mono text-[11px] ${
                      conversation.id === selectedConversation?.id
                        ? "border-primary-container bg-primary-container/10 text-primary-container"
                        : "border-white/10 bg-[#090b0e] hover:border-white/20 text-outline hover:text-on-surface"
                    }`}
                    onClick={() => setSearchParams({ conversationId: String(conversation.id) })}
                    type="button"
                  >
                    <div className="flex items-center justify-between gap-2 border-b border-white/5 pb-1 mb-1">
                      <span className="font-bold text-on-surface truncate">
                        {conversation.title ?? conversation.customer?.name ?? "COMM_LINK"}
                      </span>
                      <span className="text-[8px] border border-current/20 px-1 bg-current/5">
                        {conversation.stage}
                      </span>
                    </div>
                    <div className="flex justify-between items-center text-[10px]">
                      <span>{conversation.customer?.name ?? "Customer"}</span>
                      <span>FIT: {conversation.conversion_probability ?? 0}%</span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </ConsolePanel>

          {/* Incoming request files */}
          <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
            <div className="border-b border-white/10 pb-2">
              <span className="text-[10px] text-outline uppercase">HỒ SƠ KHÁCH GHÉ CỬA HÀNG</span>
            </div>
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1 console-scrollbar">
              {(requestsQuery.data ?? []).slice(0, 5).map((requestItem) => (
                <div key={requestItem.id} className="border border-white/10 bg-[#090b0e] p-2.5 flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2 border-b border-white/5 pb-1">
                    <span className="font-bold text-on-surface truncate">{requestItem.customer.name}</span>
                    <StatusChip
                      label={requestItem.conversation_status ?? "NO CHAT"}
                      variant={requestItem.conversation_status ? "success" : "neutral"}
                    />
                  </div>
                  <div className="text-[10px] text-outline leading-tight">{requestItem.use_case}</div>
                  <ActionButton
                    className="h-7 text-[9px]"
                    variant={requestItem.conversation_id ? "secondary" : "primary"}
                    disabled={createConversation.isPending}
                    onClick={() => openConversationForRequest(requestItem.id)}
                    title={tutorialTooltip(tutorialMode && tutorialStep >= 3, "Open or create chat")}
                  >
                    {requestItem.conversation_id ? "MỞ LIÊN KẾT CHAT" : "TẠO LIÊN KẾT"}
                  </ActionButton>
                </div>
              ))}
            </div>
          </ConsolePanel>
        </aside>

        {/* Center Panel (Transcripts & Quick Replies) + Right Panel (Dossiers) */}
        <div className="space-y-4">
          {selectedConversation ? (
            <div className="grid gap-4 xl:grid-cols-[1.4fr_1fr]">
              {/* Center Panel (Transcript, Replies and inputs) */}
              <div className="space-y-4">
                <ConsolePanel
                  variant="z-2-active"
                  className={`flex flex-col h-[650px] ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}
                >
                  <div className="flex justify-between items-center border-b border-white/10 pb-2 mb-3 select-none">
                    <span className="font-mono text-[10px] uppercase text-outline">BIÊN BẢN TRAO ĐỔI</span>
                    <span className="font-mono text-[9px] text-[#00f2ff]">
                      [{(conversationMessagesQuery.data ?? selectedConversation.messages ?? []).length} LOG ENTRIES]
                    </span>
                  </div>

                  {/* Message bubbles log scroll area */}
                  <div className="flex-1 overflow-y-auto pr-2 space-y-4 console-scrollbar mb-4 flex flex-col justify-start">
                    {(conversationMessagesQuery.data ?? selectedConversation.messages ?? []).map((message) => (
                      <MessageBubble key={message.id} message={message} />
                    ))}
                  </div>

                  {/* Actions area */}
                  <div className="border-t border-white/10 pt-3 space-y-3">
                    {/* Quick reply game action verbs */}
                    <div className={tutorialHighlight(tutorialMode && tutorialStep >= 3)}>
                      <div className="mb-2 font-mono text-[9px] uppercase tracking-wider text-outline select-none">
                        {chatCopy.quickActionTitle}
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {quickActions.map((item) => (
                          <button
                            key={item.action}
                            className={`h-7 px-2 font-mono text-[9px] tracking-wider border cursor-pointer select-none transition disabled:opacity-50 ${
                              item.variant === "primary"
                                ? "bg-primary-container text-on-primary-fixed border-primary-container font-bold"
                                : "bg-transparent text-outline border-white/10 hover:text-on-surface hover:bg-white/5"
                            }`}
                            disabled={quickReply.isPending}
                            onClick={() => handleQuickReply(item.action)}
                            type="button"
                            title={tutorialTooltip(tutorialMode && tutorialStep >= 3, item.label)}
                          >
                            {item.label.toUpperCase()}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Chat Text Input field */}
                    <div className={tutorialHighlight(tutorialMode && tutorialStep >= 3)}>
                      <textarea
                        className={`h-16 border border-white/10 bg-[#080a0d] p-2 font-mono text-[11px] text-on-surface outline-none focus:border-primary-container ${tutorialHighlight(
                          tutorialMode && tutorialStep >= 3,
                        )}`}
                        onKeyDown={(event) => {
                          if (event.key !== "Enter" || event.shiftKey) return;
                          event.preventDefault();
                          void handleSendMessage();
                        }}
                        onChange={(event) => setDraft(event.target.value)}
                        placeholder={chatCopy.placeholder}
                        value={draft}
                      />
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        <ActionButton
                          variant="primary"
                          className={`h-8 text-[10px] ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}
                          disabled={sendMessage.isPending || draft.trim().length === 0}
                          onClick={() => handleSendMessage()}
                          title={tutorialTooltip(tutorialMode && tutorialStep >= 3, "Gửi tin nhắn")}
                        >
                          {chatCopy.send}
                        </ActionButton>
                        <ActionButton
                          variant="secondary"
                          className={`h-8 text-[10px] ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}
                          disabled={readyToOrder.isPending}
                          onClick={() => handleReadyToOrder()}
                          title={tutorialTooltip(tutorialMode && tutorialStep >= 3, "Đánh dấu sẵn sàng")}
                        >
                          {chatCopy.ready}
                        </ActionButton>
                        <ActionButton
                          variant="secondary"
                          className={`h-8 text-[10px] ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}
                          disabled={closeConversation.isPending}
                          onClick={() => handleClose(true)}
                          title={tutorialTooltip(tutorialMode && tutorialStep >= 3, "Đóng và thắng")}
                        >
                          {chatCopy.closeWon}
                        </ActionButton>
                        <ActionButton
                          variant="danger"
                          className={`h-8 text-[10px] ${tutorialHighlight(tutorialMode && tutorialStep >= 3)}`}
                          disabled={closeConversation.isPending}
                          onClick={() => handleClose(false)}
                          title={tutorialTooltip(tutorialMode && tutorialStep >= 3, "Đóng và thua")}
                        >
                          {chatCopy.closeLost}
                        </ActionButton>
                      </div>
                    </div>
                  </div>
                </ConsolePanel>
              </div>

              {/* Right Panel: Dossiers and assignment controls */}
              <div className="space-y-4">
                {/* Dossier info */}
                <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
                  <div className="border-b border-white/10 pb-2 select-none">
                    <span className="text-[10px] text-outline uppercase">HỒ SƠ KHÁCH HÀNG</span>
                  </div>
                  <div className="space-y-1.5">
                    <div className="flex justify-between bg-[#080a0d] border border-white/5 p-2 items-center">
                      <span className="text-[9px] text-outline">CHÂN DUNG</span>
                      <span className="font-bold text-[#00f2ff] uppercase">{selectedConversation.persona_type ?? "GENERIC"}</span>
                    </div>
                    <div className="flex justify-between bg-[#080a0d] border border-white/5 p-2 items-center">
                      <span className="text-[9px] text-outline">TÂM TRẠNG</span>
                      <span className="font-bold text-on-surface uppercase">{selectedConversation.customer_mood ?? "neutral"}</span>
                    </div>
                    <div className="flex justify-between bg-[#080a0d] border border-white/5 p-2 items-center">
                      <span className="text-[9px] text-outline">LINH KIỆN CŨ</span>
                      <span className="font-bold text-on-surface">
                        {selectedConversation.accepts_used_parts === null
                          ? "UNKNOWN"
                          : selectedConversation.accepts_used_parts
                          ? "ACCEPTED"
                          : "REJECTED"}
                      </span>
                    </div>
                    <div className="flex justify-between bg-[#080a0d] border border-white/5 p-2 items-center">
                      <span className="text-[9px] text-outline">NGÂN SÁCH TỐI ĐA</span>
                      <span className="font-bold text-emerald-400">
                        ₫{Number(selectedConversation.detected_budget_vnd ?? request?.budget_vnd ?? 0).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex flex-col bg-[#080a0d] border border-white/5 p-2">
                      <span className="text-[9px] text-outline">PHÂN TÍCH MỤC ĐÍCH</span>
                      <span className="text-[10px] text-on-surface mt-1 leading-snug">
                        {selectedConversation.detected_use_case ?? request?.use_case ?? "N/A"}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1 pt-2">
                    {selectedConversation.customer_request?.priority_tags_json?.slice(0, 4).map((tag) => (
                      <span key={tag} className="border border-white/10 bg-white/[0.03] px-1.5 py-0.5 text-[9px] text-outline">
                        [{tag.toUpperCase()}]
                      </span>
                    ))}
                  </div>
                </ConsolePanel>

                {/* Intent preference logs */}
                <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px] select-none">
                  <div className="border-b border-white/10 pb-2">
                    <span className="text-[10px] text-outline uppercase">NHẬT KÝ PHÂN TÍCH Ý ĐỊNH</span>
                  </div>
                  <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1 console-scrollbar">
                    {intentEntries(selectedConversation.detected_preferences_json).length === 0 ? (
                      <div className="text-[9px] text-outline/40 italic p-2 text-center">ĐANG CHỜ TRÍCH XUẤT SỞ THÍCH</div>
                    ) : (
                      intentEntries(selectedConversation.detected_preferences_json).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between gap-3 bg-[#080a0d] border border-white/5 px-2.5 py-1.5">
                          <span className="text-[9px] uppercase text-outline/70">{labelize(key)}</span>
                          <span className="font-bold text-on-surface truncate max-w-[100px]">{stringifyValue(value)}</span>
                        </div>
                      ))
                    )}
                  </div>
                </ConsolePanel>

                {/* Staff assigner */}
                <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
                  <div className="border-b border-white/10 pb-2 select-none">
                    <span className="text-[10px] text-outline uppercase">{chatCopy.staffTitle}</span>
                  </div>
                  <div className="space-y-2">
                    <select
                      className="h-9 w-full border border-white/10 bg-[#0c0f13] px-2 font-mono text-[10px] text-on-surface outline-none focus:border-primary-container"
                      onChange={(event) => {
                        if (!event.target.value) return;
                        handleAssignStaff(Number(event.target.value));
                      }}
                      value={selectedConversation.assigned_staff_id ?? ""}
                    >
                      <option value="">{chatCopy.staffPlaceholder}</option>
                      {(staffQuery.data ?? []).map((staff) => (
                        <option key={staff.id} value={staff.id}>
                          {staff.name} - {staff.role}
                        </option>
                      ))}
                    </select>
                    {selectedConversation.assigned_staff_id && (
                      <div className="text-[9px] text-[#00f2ff] border border-[#00f2ff]/20 bg-[#00f2ff]/5 p-1.5 text-center uppercase font-bold tracking-wider">
                        STAFF ASSISTED // ID: OP-{selectedConversation.assigned_staff_id}
                      </div>
                    )}
                  </div>
                </ConsolePanel>

                {/* Quote Attachments selector and sender */}
                <ConsolePanel variant="z-1" className="space-y-3 font-mono text-[11px]">
                  <div className="border-b border-white/10 pb-2 select-none">
                    <span className="text-[10px] text-outline uppercase">ĐÍNH KÈM BÁO GIÁ</span>
                  </div>
                  {filteredQuotes.length === 0 ? (
                    <p className="text-[9px] text-outline/50 italic text-center p-3 bg-[#080a0d] border border-white/5">
                      NO QUOTES PRODUCED FOR REQUEST
                    </p>
                  ) : (
                    <div className="space-y-2">
                      <select
                        className="h-9 w-full border border-white/10 bg-[#0c0f13] px-2 font-mono text-[10px] text-on-surface outline-none focus:border-primary-container"
                        onChange={(event) => setSelectedQuoteId(Number(event.target.value))}
                        value={selectedQuoteId ?? ""}
                      >
                        {filteredQuotes.map((detail) => (
                          <option key={detail.quote.id} value={detail.quote.id}>
                            #{detail.quote.id} {detail.quote.title}
                          </option>
                        ))}
                      </select>
                      <div className="grid gap-2">
                        {filteredQuotes
                          .filter((detail) => detail.quote.id === selectedQuoteId)
                          .map((detail) => (
                            <div key={detail.quote.id} className="border border-white/5 bg-[#080a0d] p-2 text-[10px] space-y-1">
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-bold text-on-surface truncate">{detail.quote.title}</span>
                                <span className="font-mono text-[8px] text-[#00f2ff] border border-[#00f2ff]/20 px-1 bg-[#00f2ff]/5">
                                  {detail.quote.status}
                                </span>
                              </div>
                              <p className="text-[9px] text-outline leading-tight">{detail.quote.summary}</p>
                              <div className="flex justify-between items-center border-t border-white/5 pt-1 mt-1 font-mono">
                                <span className="text-[9px] text-outline">PRICE:</span>
                                <span className="font-bold text-emerald-400">₫{detail.quote.quoted_price_vnd.toLocaleString()}</span>
                              </div>
                            </div>
                          ))}
                      </div>
                      <ActionButton
                        className="h-9 text-[10px]"
                        variant="primary"
                        disabled={sendQuote.isPending || !selectedQuoteId}
                        onClick={() => handleSendQuote()}
                      >
                        {chatCopy.sendProposal}
                      </ActionButton>
                    </div>
                  )}
                </ConsolePanel>
              </div>
            </div>
          ) : (
            <EmptyState title={chatCopy.emptyConversationTitle} body={chatCopy.emptyConversationBody} />
          )}
        </div>
      </div>
    </section>
  );
}

function MessageBubble({ message }: { message: CustomerConversationMessage }) {
  const uiLanguage = useGameStore((state) => state.uiLanguage);
  const isCustomer = message.sender_type === "CUSTOMER";
  const isPlayer = message.sender_type === "PLAYER";
  const isStaff = message.sender_type === "STAFF";
  const isSystem =
    message.sender_type === "SYSTEM" ||
    message.message_type === "SYSTEM_NOTE" ||
    message.message_type === "ACTION_EVENT";

  const quoteId = message.metadata_json ? (message.metadata_json.quote_id as number | undefined) : undefined;
  const quotedPrice = message.metadata_json ? (message.metadata_json.quoted_price_vnd as number | undefined) : undefined;

  if (isSystem) {
    return (
      <div className="font-mono text-[10px] text-outline/45 italic leading-relaxed py-1 border-b border-white/[0.02] select-none">
        [{uiLanguage === "en" ? "SYSTEM" : "HỆ THỐNG"}] {message.body}
      </div>
    );
  }

  let bubbleStyle = "";
  let labelStyle = "";
  let senderName = "";

  if (isCustomer) {
    bubbleStyle = "bg-white border border-white/20 text-slate-900 self-start p-3 mr-8";
    labelStyle = "text-rose-600 font-bold";
    senderName = uiLanguage === "en" ? `[CLIENT // ${message.sender_label ?? "WALK-IN"}]` : `[KHÁCH // ${message.sender_label ?? "VÃNG LAI"}]`;
  } else if (isPlayer) {
    bubbleStyle = "bg-primary-container/10 border border-primary-container/40 text-on-surface self-end p-3 ml-8";
    labelStyle = "text-[#00f2ff] font-bold";
    senderName = uiLanguage === "en" ? `[PLAYER // COMMANDER]` : `[BẠN // ĐIỀU PHỐI]`;
  } else if (isStaff) {
    bubbleStyle = "bg-[#74f5ff]/10 border border-[#74f5ff]/30 text-on-surface self-end p-3 ml-8";
    labelStyle = "text-[#74f5ff] font-bold";
    senderName = uiLanguage === "en" ? `[STAFF // ${message.sender_label ?? "OPERATOR"}]` : `[NHÂN SỰ // ${message.sender_label ?? "HỖ TRỢ"}]`;
  } else {
    bubbleStyle = "bg-surface-container-low border border-white/10 text-on-surface p-3";
    labelStyle = "text-outline font-bold";
    senderName = `[${message.sender_label ?? message.sender_type}]`;
  }

  return (
    <div className="flex flex-col gap-1 w-full font-mono text-[11px]">
      <div className={`flex items-center justify-between ${isCustomer ? "self-start" : "self-end"} select-none mb-0.5`}>
        <span className={labelStyle}>{senderName}</span>
        <span className="text-[9px] text-outline/40 ml-2">{labelize(message.message_type)}</span>
      </div>
      <div className={`${bubbleStyle} relative`}>
        <p className="leading-relaxed whitespace-pre-wrap">{message.body}</p>

        {quoteId && (
          <div className="mt-2.5 pt-2.5 border-t border-dashed border-current/20 font-mono text-[10px] space-y-1 bg-black/5 p-2 text-left">
            <span className="font-bold uppercase block text-[9px] tracking-wider">
              [{uiLanguage === "en" ? "QUOTE ATTACHMENT" : "BÁO GIÁ ĐÍNH KÈM"} #{quoteId}]
            </span>
            <div>{uiLanguage === "en" ? "Est. Fit Score" : "Điểm phù hợp"}: <span className="font-bold">{String(message.metadata_json?.customer_fit_score ?? "?")}</span></div>
            <div>{uiLanguage === "en" ? "Acceptance Chance" : "Khả năng chốt"}: <span className="font-bold">{String(message.metadata_json?.quote_acceptance_chance ?? "?")}%</span></div>
            {quotedPrice && (
              <div className="text-emerald-500 font-bold">{uiLanguage === "en" ? "Price" : "Giá"}: ₫{Number(quotedPrice).toLocaleString()}</div>
            )}
          </div>
        )}

        {message.metadata_json && !quoteId && Object.keys(message.metadata_json).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 pt-1 border-t border-current/10 select-none">
            {Object.entries(message.metadata_json).slice(0, 4).map(([key, value]) => (
              <span key={key} className="bg-black/10 px-1 py-0.5 text-[9px]">
                {labelize(key)}: {stringifyValue(value)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) return "n/a";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => stringifyValue(item)).join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function intentEntries(value: Record<string, unknown> | null | undefined): Array<[string, unknown]> {
  if (!value) return [];
  return Object.entries(value).filter(([, entry]) => entry !== null && entry !== undefined);
}
