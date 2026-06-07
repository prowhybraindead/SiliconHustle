export function formatVnd(value: number | null | undefined): string {
  if (value === null || value === undefined) return "?";
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

const CODE_LABELS: Record<string, string> = {
  ALL: "Tất cả",
  NEW: "Mới",
  USED: "Đã qua sử dụng",
  UNTESTED: "Chưa kiểm tra",
  REFURBISHED: "Đã tân trang",
  DEFECTIVE: "Lỗi",
  READY: "Sẵn sàng",
  ONLINE: "Trực tuyến",
  OFFLINE: "Ngoại tuyến",
  ACTIVE: "Đang hoạt động",
  INACTIVE: "Không hoạt động",
  OPEN: "Mở",
  CLOSED: "Đóng",
  ACCEPTED: "Đã chấp nhận",
  REJECTED: "Đã từ chối",
  RESERVED: "Đã giữ",
  NOT_RESERVED: "Chưa giữ",
  IN_PROGRESS: "Đang xử lý",
  TESTING: "Đang kiểm tra",
  DELIVERED: "Đã giao",
  COMPLETED: "Hoàn tất",
  WAITING_FOR_CUSTOMER: "Đang chờ khách",
  QUOTE_PROPOSED: "Đã gửi báo giá",
  READY_TO_ORDER: "Sẵn sàng đặt hàng",
  CLOSED_WON: "Chốt thành công",
  CLOSED_LOST: "Mất khách",
  CONVERTED_TO_ORDER: "Đã chuyển thành đơn",
  AWAITING_DECISION: "Chờ quyết định",
  DIAGNOSING: "Đang chẩn đoán",
  IN_REVIEW: "Đang xem xét",
  APPROVED: "Đã duyệt",
  RMA_SUBMITTED: "Đã gửi RMA",
  REPAIR: "Sửa chữa",
  REPLACE: "Thay thế",
  REFUND: "Hoàn tiền",
  GOODWILL_CREDIT: "Ưu đãi thiện chí",
  REJECT: "Từ chối",
  REVIEW: "Đánh giá",
  RISK: "Rủi ro",
  FAIL: "Lỗi",
  PASS: "Đạt",
  UNKNOWN: "Không rõ",
  GENERIC: "Chung",
  NO_CATEGORY: "Chưa phân loại",
  NO_ACTION: "Không có hành động",
  NO_NOTES: "Không có ghi chú",
  BEGINNER_MODE: "Chế độ người mới",
  LIVE_FX: "FX trực tiếp",
  FALLBACK_RATE: "Tỷ giá dự phòng",
  SYSTEM: "Hệ thống",
  CUSTOMER: "Khách hàng",
  PLAYER: "Người chơi",
  STAFF: "Nhân sự",
  INVENTORY: "Kho hàng",
  SUPPLIER_NEEDED: "Cần nguồn cung",
  USED_MARKET: "Chợ hàng cũ",
  BRAND: "Thương hiệu",
  FX: "Ngoại hối",
  CMD: "Trung tâm điều khiển",
  PRF: "Hồ sơ bảo mật",
  OPS: "Bảng vận hành",
  UPG: "Cửa hàng nâng cấp",
  CTL: "Danh mục phần cứng",
  WRH: "Kho hàng",
  RFB: "Bàn tân trang",
  STF: "Phòng nhân sự",
  RSL: "Chợ bán lại",
  BRD: "Kho thương hiệu",
  MKT: "Sự kiện thị trường",
  USD: "Chợ hàng cũ",
  SPL: "Quầy nhà cung cấp",
  CST: "Quầy khách hàng",
  CHT: "Chat tư vấn",
  QTE: "Báo giá",
  ORD: "Đơn hàng",
  WRN: "Bảo hành / RMA",
  REV: "Đánh giá",
  SYS: "Cài đặt",
  DAY: "Ngày",
  CASH: "Tiền mặt",
  REP: "Uy tín",
  REQUESTS: "Yêu cầu",
  FUNDS_TELEMETRY: "Tiền khả dụng",
  SHOWROOM_REPUTATION: "Uy tín showroom",
  ACTIVE_RMA_CLAIMS: "Đơn bảo hành đang mở",
  AWAITING_ASSEMBLY: "Chờ lắp ráp",
  DIAGNOSTICS: "Chẩn đoán",
  TESTING_MODULE: "Kiểm tra",
  COMPLETED_DISPATCHED: "Hoàn tất / Đã giao",
  PENDING_PROPOSALS: "Báo giá chờ xử lý",
  REJECTED_EXPIRED: "Đã từ chối / Hết hạn",
  CONVERTED_ORDERS: "Đơn đã chuyển đổi",
  OPEN_CLAIMS: "Đơn đang mở",
  DUE_SOON: "Sắp đến hạn",
  EST_EXPOSURE: "Rủi ro dự kiến",
};

const PHRASE_LABELS: Record<string, string> = {
  "Command Center": "Trung tâm điều khiển",
  "Security Profiles": "Hồ sơ bảo mật",
  "Operations Board": "Bảng vận hành",
  "Upgrade Shop": "Cửa hàng nâng cấp",
  "Product Catalog": "Danh mục phần cứng",
  "Hardware Intelligence Database": "Cơ sở dữ liệu phần cứng",
  "Warehouse Inventory": "Kho hàng",
  "Refurbish Bench": "Bàn tân trang",
  "Staff Room": "Phòng nhân sự",
  "Resale Market": "Chợ bán lại",
  "Brands Vault": "Kho thương hiệu",
  "FX Exchange": "Bàn FX",
  "Market Events": "Sự kiện thị trường",
  "Used Market Bargaining": "Mặc cả hàng cũ",
  "Supplier Desk": "Quầy nhà cung cấp",
  "Customers Desk": "Quầy khách hàng",
  "Sales Chat Consultation": "Chat tư vấn bán hàng",
  "Build Quotes": "Lập báo giá",
  "Orders & Assemblies": "Đơn hàng & lắp ráp",
  "Warranty RMA Desk": "Quầy bảo hành / RMA",
  "Reviews Feed": "Luồng đánh giá",
  "System Settings": "Cài đặt hệ thống",
  "Guided Tutorial": "Tutorial hướng dẫn",
  "Brand Registry": "Sổ đăng ký thương hiệu",
  "Warehouse Manifest": "Phiếu kho",
  "STATION-01 // WAREHOUSE": "TRẠM-01 // KHO HÀNG",
  "STATION-01 // SUPPLIER DESK": "TRẠM-01 // QUẦY NHÀ CUNG CẤP",
  "STATION-03 // ORDER ASSEMBLY BAY": "TRẠM-03 // KHU LẮP RÁP ĐƠN HÀNG",
  "STATION-04 // WORKBENCH": "TRẠM-04 // BÀN TÂN TRANG",
  "STATION-05 // USED MARKET": "TRẠM-05 // CHỢ HÀNG CŨ",
  "STATION-06 // RESALE BOARD": "TRẠM-06 // BẢNG BÁN LẠI",
  "STATION-08 // AFTER-SALES DESK": "TRẠM-08 // QUẦY HẬU MÃI",
  "STATION-09 // PERSONNEL SERVICES": "TRẠM-09 // NHÂN SỰ",
  "STATION-10 // FACILITY BLUEPRINTS": "TRẠM-10 // BẢN THIẾT KẾ CƠ SỞ",
  "STATION-11 // PUBLIC FEEDBACK": "TRẠM-11 // PHẢN HỒI CÔNG KHAI",
  "STATION-12 // MANUFACTURER DIRECTORY": "TRẠM-12 // DANH BẠ NHÀ SẢN XUẤT",
  "STATION-13 // FINANCIAL CONVERSIONS": "TRẠM-13 // QUY ĐỔI TÀI CHÍNH",
  "Used Market / Trade-in Console": "Bàn mua bán hàng cũ / thu đổi",
  "Resale Marketplace Board": "Bảng chợ bán lại",
  "Supplier Procurement Terminal": "Bàn mua hàng nhà cung cấp",
  "Reputation Terminal": "Bàn uy tín",
  "FX Desk": "Bàn FX",
  "Systems Panel": "Bảng hệ thống",
  "No save selected": "Chưa chọn bản lưu",
  "No command center selected": "Chưa chọn trung tâm điều khiển",
  "Open or create a save game from the home screen.": "Mở hoặc tạo một bản lưu từ màn hình chính.",
  "Open or create a showroom save from the home screen.": "Mở hoặc tạo một bản lưu showroom từ màn hình chính.",
  "Open a save before generating customers.": "Mở một bản lưu trước khi tạo khách hàng.",
  "Open a save before managing inventory.": "Mở một bản lưu trước khi quản lý kho.",
  "Open a save before using customer chat.": "Mở một bản lưu trước khi dùng chat khách hàng.",
  "Open a save before handling warranty claims.": "Mở một bản lưu trước khi xử lý bảo hành.",
  "Open a save before reviewing orders.": "Mở một bản lưu trước khi xem đơn hàng.",
  "Open a save before accessing the staff desk.": "Mở một bản lưu trước khi vào quầy nhân sự.",
  "Open a save before using shop upgrades.": "Mở một bản lưu trước khi dùng nâng cấp cửa hàng.",
  "Open a save game before accessing the Refurbish workbench.": "Mở một bản lưu trước khi vào bàn tân trang.",
  "Open a showroom save before building proposals.": "Mở một bản lưu showroom trước khi tạo báo giá.",
  "Open a showroom save before accessing the Resale Marketplace.": "Mở một bản lưu showroom trước khi vào chợ bán lại.",
  "No customer requests": "Chưa có yêu cầu khách hàng",
  "Generate a deterministic sample customer request.": "Tạo một yêu cầu khách hàng mẫu có thể lặp lại.",
  "Empty Query Response": "Không có kết quả phù hợp",
  "No active units matching the query manifest filters.": "Không có thiết bị nào khớp bộ lọc hiện tại.",
  "No orders yet": "Chưa có đơn hàng",
  "Generate and accept a quote to create an accepted order.": "Tạo và chấp nhận một báo giá để sinh đơn hàng.",
  "No Profiles": "Chưa có hồ sơ",
  "Create a profile to enable lock features for your showrooms.": "Tạo hồ sơ để bật tính năng khóa cho showroom.",
  "No contracts found": "Không tìm thấy hợp đồng",
  "Adjust filters or check global events.": "Chỉnh bộ lọc hoặc kiểm tra sự kiện toàn cục.",
  "LOADING BRANDS": "Đang tải thương hiệu",
  "Reading brand master data from database.": "Đang đọc dữ liệu thương hiệu từ cơ sở dữ liệu.",
  "CONNECTION ERROR": "Lỗi kết nối",
  "No manufacturers match the current filter query.": "Không có nhà sản xuất nào khớp bộ lọc hiện tại.",
  "Accessing central repository": "Đang truy cập kho dữ liệu trung tâm",
  "Scraping active hardware databases...": "Đang quét cơ sở dữ liệu phần cứng...",
  "Telemetry connection failed": "Kết nối telemetry thất bại",
  "Relax parameter constraints to broaden query result.": "Nới điều kiện lọc để mở rộng kết quả.",
  "No conversation selected": "Chưa chọn cuộc trò chuyện",
  "Pick a thread from the left or open one from Customers.": "Chọn một luồng ở bên trái hoặc mở từ Khách hàng.",
  "No tutorial save selected": "Chưa chọn bản lưu tutorial",
  "Start the guided tutorial from the home screen.": "Bắt đầu tutorial hướng dẫn từ màn hình chính.",
  "No warranty claims": "Chưa có yêu cầu bảo hành",
  "Open a claim from a delivered order when after-sales issues appear.": "Mở một yêu cầu từ đơn đã giao khi phát sinh hậu mãi.",
  "Access Denied": "Từ chối truy cập",
  "Connect profile to pull invoice pipeline.": "Kết nối hồ sơ để tải luồng hóa đơn.",
  "No active invoices": "Chưa có hóa đơn đang mở",
  "Initialize a procurement contract on the left.": "Khởi tạo hợp đồng mua hàng ở bên trái.",
  "loading module...": "đang tải mô-đun...",
  "Something went wrong while syncing with the backend.": "Đã có lỗi khi đồng bộ với backend.",
};

export function translateUiText(value: string | null | undefined): string {
  if (!value) return "";
  return PHRASE_LABELS[value] ?? CODE_LABELS[value] ?? value;
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
  return CODE_LABELS[value] ?? value.replace(/_/g, " ").toLowerCase().replace(/\b\w/g, (letter: string) => letter.toUpperCase());
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
