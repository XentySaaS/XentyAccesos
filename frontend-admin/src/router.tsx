import { createBrowserRouter, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Tenants from "./pages/Tenants";
import TenantDetalle from "./pages/TenantDetalle";
import Planes from "./pages/Planes";
import Seguridad from "./pages/Seguridad";
import Comunicaciones from "./pages/Comunicaciones";
import { useAuth } from "./store/auth";

function Protegida({ children }: { children: JSX.Element }) {
  const access = useAuth((s) => s.access);
  return access ? children : <Navigate to="/" replace />;
}

// Panel de super-admin AISLADO: sin alta pública (eso vive en la landing).
export const router = createBrowserRouter([
  { path: "/", element: <Login /> },
  {
    element: (
      <Protegida>
        <Layout />
      </Protegida>
    ),
    children: [
      { path: "/dashboard", element: <Dashboard /> },
      { path: "/tenants", element: <Tenants /> },
      { path: "/tenants/:id", element: <TenantDetalle /> },
      { path: "/planes", element: <Planes /> },
      { path: "/comunicaciones", element: <Comunicaciones /> },
      { path: "/seguridad", element: <Seguridad /> },
    ],
  },
]);
