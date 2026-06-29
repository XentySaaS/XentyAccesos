import { createBrowserRouter, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Documentos from "./pages/Documentos";
import Empleados from "./pages/Empleados";
import Login from "./pages/Login";
import MisEventos from "./pages/MisEventos";
import Onboarding from "./pages/Onboarding";
import { useAuth } from "./store/auth";

function Protegida({ children }: { children: JSX.Element }) {
  const access = useAuth((s) => s.access);
  return access ? children : <Navigate to="/" replace />;
}

export const router = createBrowserRouter(
  [
    { path: "/", element: <Login /> },
    { path: "/onboarding", element: <Onboarding /> },
    {
      element: (
        <Protegida>
          <Layout />
        </Protegida>
      ),
      children: [
        { path: "/dashboard", element: <Dashboard /> },
        { path: "/empleados", element: <Empleados /> },
        { path: "/documentos", element: <Documentos /> },
        { path: "/eventos", element: <MisEventos /> },
      ],
    },
  ],
  { basename: "/proveedores" },
);
