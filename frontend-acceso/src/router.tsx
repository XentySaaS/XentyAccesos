import { createBrowserRouter, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Citas from "./pages/Citas";
import Dashboard from "./pages/Dashboard";
import Escaner from "./pages/Escaner";
import Eventos from "./pages/Eventos";
import Login from "./pages/Login";
import Proveedores from "./pages/Proveedores";
import Recintos from "./pages/Recintos";
import Sanciones from "./pages/Sanciones";
import { useAuth } from "./store/auth";

function Protegida({ children }: { children: JSX.Element }) {
  const access = useAuth((s) => s.access);
  return access ? children : <Navigate to="/" replace />;
}

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
      { path: "/recintos", element: <Recintos /> },
      { path: "/eventos", element: <Eventos /> },
      { path: "/proveedores", element: <Proveedores /> },
      { path: "/citas", element: <Citas /> },
      { path: "/sanciones", element: <Sanciones /> },
      { path: "/escaner", element: <Escaner /> },
    ],
  },
]);
