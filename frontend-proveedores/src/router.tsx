import { createBrowserRouter, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Documentos from "./pages/Documentos";
import Empleados from "./pages/Empleados";
import Legal from "./pages/Legal";
import Login from "./pages/Login";
import MisEventos from "./pages/MisEventos";
import Onboarding from "./pages/Onboarding";
import Recuperar from "./pages/Recuperar";
import Restablecer from "./pages/Restablecer";
import { useAuth } from "./store/auth";

function Protegida({ children }: { children: JSX.Element }) {
  const access = useAuth((s) => s.access);
  return access ? children : <Navigate to="/" replace />;
}

export const router = createBrowserRouter(
  [
    { path: "/", element: <Login /> },
    { path: "/recuperar", element: <Recuperar /> },
    { path: "/restablecer", element: <Restablecer /> },
    { path: "/onboarding", element: <Onboarding /> },
    // Documentos legales: públicos (sin sesión), accesibles siempre desde el footer.
    { path: "/legal/:tipo", element: <Legal /> },
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
