import { Route, Routes } from "react-router-dom";

import { AdminGate } from "./components/AdminGate";
import { AdminDashboard } from "./pages/AdminDashboard";
import { DemoPage } from "./pages/DemoPage";
import { Display } from "./pages/Display";
import { Drawing } from "./pages/Drawing";
import { Home } from "./pages/Home";
import { Pickup } from "./pages/Pickup";
import { PrizeManagement } from "./pages/PrizeManagement";
import { Reports } from "./pages/Reports";
import { Sales } from "./pages/Sales";
import { Setup } from "./pages/Setup";
import { Unclaimed } from "./pages/Unclaimed";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/sales" element={<Sales />} />
      <Route path="/drawing" element={<Drawing />} />
      <Route path="/display" element={<Display />} />
      <Route path="/pickup" element={<Pickup />} />
      <Route path="/unclaimed" element={<Unclaimed />} />
      <Route
        path="/admin"
        element={
          <AdminGate>
            <AdminDashboard />
          </AdminGate>
        }
      />
      <Route
        path="/admin/prizes"
        element={
          <AdminGate>
            <PrizeManagement />
          </AdminGate>
        }
      />
      <Route
        path="/admin/reports"
        element={
          <AdminGate>
            <Reports />
          </AdminGate>
        }
      />
      <Route
        path="/admin/setup"
        element={
          <AdminGate>
            <Setup />
          </AdminGate>
        }
      />
      <Route
        path="/admin/demo"
        element={
          <AdminGate>
            <DemoPage />
          </AdminGate>
        }
      />
    </Routes>
  );
}
