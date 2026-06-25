import { createBrowserRouter, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Tenants from "./pages/Tenants";
import { useAuth } from "./store/auth";

function Protegida({ children }: { children: JSX.Element }) {
  const access = useAuth((s) => s.access);
  return access ? children : <Navigate to="/" replace />;
}

// Panel de super-admin AISLADO: sin alta pública (eso vive en la landing).
export const router = createBrowserRouter([
  { path: "/", element: <Login /> },
  { path: "/tenants", element: <Protegida><Tenants /></Protegida> },
]);
