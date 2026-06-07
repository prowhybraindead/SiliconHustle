import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  User,
  ListTree,
  BadgeDollarSign,
  Cpu,
  Boxes,
  Wrench,
  UserPlus2,
  Repeat,
  Tags,
  Coins,
  TrendingUp,
  ShoppingBag,
  Store,
  Users,
  MessageSquareText,
  FileText,
  ShoppingCart,
  ShieldAlert,
  Settings,
  Star,
} from "lucide-react";

import { useGameStore } from "../store/gameStore";
import { translateUiText, pickUiText } from "../utils/format";

const navItems = [
  { to: "/dashboard", label: "CMD", title: "Command Center", icon: LayoutDashboard },
  { to: "/profiles", label: "SEC", title: "Showroom Security", icon: User },
  { to: "/operations", label: "OPS", title: "Operations Board", icon: ListTree },
  { to: "/progression", label: "UPG", title: "Upgrade Shop", icon: BadgeDollarSign },
  { to: "/catalog", label: "CTL", title: "Product Catalog", icon: Cpu },
  { to: "/inventory", label: "WRH", title: "Warehouse Inventory", icon: Boxes },
  { to: "/refurbish", label: "RFB", title: "Refurbish Bench", icon: Wrench },
  { to: "/staff", label: "STF", title: "Staff Room", icon: UserPlus2 },
  { to: "/resale", label: "RSL", title: "Resale Market", icon: Repeat },
  { to: "/brands", label: "BRD", title: "Brands Vault", icon: Tags },
  { to: "/currency", label: "FX", title: "FX Desk", icon: Coins },
  { to: "/market", label: "MKT", title: "Market Events", icon: TrendingUp },
  { to: "/used-market", label: "USD", title: "Used Market / Trade-in Console", icon: ShoppingBag },
  { to: "/suppliers", label: "SPL", title: "Supplier Desk", icon: Store },
  { to: "/customers", label: "CST", title: "Customers Desk", icon: Users },
  { to: "/customer-chat", label: "CHT", title: "Sales Chat Consultation", icon: MessageSquareText },
  { to: "/quotes", label: "QTE", title: "Build Quotes", icon: FileText },
  { to: "/orders", label: "ORD", title: "Orders & Assemblies", icon: ShoppingCart },
  { to: "/warranty", label: "WRN", title: "Warranty RMA Desk", icon: ShieldAlert },
  { to: "/reviews", label: "REV", title: "Reviews Feed", icon: Star },
  { to: "/settings", label: "SYS", title: "System Settings", icon: Settings },
];

const mobileNavItems = [
  { to: "/dashboard", label: "CMD", icon: LayoutDashboard },
  { to: "/inventory", label: "WRH", icon: Boxes },
  { to: "/customer-chat", label: "CHT", icon: MessageSquareText },
  { to: "/orders", label: "ORD", icon: ShoppingCart },
  { to: "/settings", label: "SYS", icon: Settings },
];

export function Sidebar() {
  const uiLanguage = useGameStore((state) => state.uiLanguage);

  return (
    <>
      <nav className="hidden md:flex fixed left-0 top-12 bottom-0 w-16 flex-col items-center py-panel-gap z-40 bg-surface-container-lowest/90 backdrop-blur-xl border-r border-white/10 transition-all duration-200 ease-in-out select-none">
        <div className="w-full flex flex-col items-center gap-1 mb-4 border-b border-white/10 pb-3 flex-shrink-0">
          <div className="w-8 h-8 rounded bg-surface border border-white/20 flex items-center justify-center overflow-hidden mb-1 relative">
            <span className="font-mono text-xs text-secondary-fixed-dim font-black">OP</span>
          </div>
          <div className="flex flex-col items-center text-center">
            <span className="font-mono text-[9px] text-secondary-fixed-dim">{pickUiText("TRẠM-01", "ST-01", uiLanguage)}</span>
            <span className="text-[7px] text-primary-container/60 font-mono tracking-wider">
              {pickUiText("[TRỰC TUYẾN]", "[ONLINE]", uiLanguage)}
            </span>
          </div>
        </div>

        <div className="flex-1 w-full flex flex-col gap-1 overflow-y-auto console-scrollbar pr-[1px]">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              title={translateUiText(item.title)}
              className={({ isActive }) =>
                `w-full h-12 flex flex-col items-center justify-center gap-0.5 relative transition-all duration-200 ease-in-out ${
                  isActive
                    ? "bg-primary-container/20 border-l-2 border-primary-container text-primary-container font-bold"
                    : "text-outline hover:text-on-surface-variant hover:bg-white/5"
                }`
              }
            >
              <item.icon className="h-[18px] w-[18px] shrink-0" />
              <span className="font-mono text-[8px] uppercase tracking-wider">{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>

      <nav className="md:hidden fixed bottom-0 left-0 right-0 h-14 bg-surface-container-high/90 backdrop-blur-md border-t border-white/10 flex justify-around items-center z-40 select-none pb-safe">
        {mobileNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-0.5 px-3 py-1 text-center flex-1 h-full transition-all ${
                isActive
                  ? "bg-primary-container/10 border-t-2 border-primary-container text-primary-container font-bold"
                  : "text-outline hover:text-on-surface-variant"
              }`
            }
          >
            <item.icon className="h-5 w-5 shrink-0" />
            <span className="font-mono text-[8px] uppercase tracking-wider">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </>
  );
}
