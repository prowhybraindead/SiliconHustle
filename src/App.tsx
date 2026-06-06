import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/AppLayout";
import { BrandsPage } from "./pages/BrandsPage";
import { CatalogPage } from "./pages/CatalogPage";
import { CurrencyPage } from "./pages/CurrencyPage";
import { CustomersPage } from "./pages/CustomersPage";
import { CustomerChatPage } from "./pages/CustomerChatPage";
import { DashboardPage } from "./pages/DashboardPage";
import { HomePage } from "./pages/HomePage";
import { InventoryPage } from "./pages/InventoryPage";
import { MarketPage } from "./pages/MarketPage";
import { OperationsPage } from "./pages/OperationsPage";
import { OrdersPage } from "./pages/OrdersPage";
import { ProgressionPage } from "./pages/ProgressionPage";
import { QuotesPage } from "./pages/QuotesPage";
import { ReviewsPage } from "./pages/ReviewsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SuppliersPage } from "./pages/SuppliersPage";
import { WarrantyPage } from "./pages/WarrantyPage";
import { ProfilesPage } from "./pages/ProfilesPage";
import { UsedMarketPage } from "./pages/UsedMarketPage";
import { RefurbishPage } from "./pages/RefurbishPage";
import { StaffPage } from "./pages/StaffPage";
import { ResalePage } from "./pages/ResalePage";

export default function App() {
  return (
    <Routes>
      <Route element={<HomePage />} path="/" />
      <Route element={<AppLayout />}>
        <Route element={<DashboardPage />} path="/dashboard" />
        <Route element={<OperationsPage />} path="/operations" />
        <Route element={<ProgressionPage />} path="/progression" />
        <Route element={<CatalogPage />} path="/catalog" />
        <Route element={<InventoryPage />} path="/inventory" />
        <Route element={<RefurbishPage />} path="/refurbish" />
        <Route element={<StaffPage />} path="/staff" />
        <Route element={<ResalePage />} path="/resale" />
        <Route element={<MarketPage />} path="/market" />
        <Route element={<BrandsPage />} path="/brands" />
        <Route element={<CurrencyPage />} path="/currency" />
        <Route element={<SuppliersPage />} path="/suppliers" />
        <Route element={<CustomersPage />} path="/customers" />
        <Route element={<CustomerChatPage />} path="/customer-chat" />
        <Route element={<QuotesPage />} path="/quotes" />
        <Route element={<ReviewsPage />} path="/reviews" />
        <Route element={<OrdersPage />} path="/orders" />
        <Route element={<WarrantyPage />} path="/warranty" />
        <Route element={<ProfilesPage />} path="/profiles" />
        <Route element={<UsedMarketPage />} path="/used-market" />
        <Route element={<SettingsPage />} path="/settings" />
      </Route>
      <Route element={<Navigate replace to="/" />} path="*" />
    </Routes>
  );
}
