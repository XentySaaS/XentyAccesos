import { createBrowserRouter, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Accesos from "./pages/Accesos";
import Bitacora from "./pages/Bitacora";
import Catalogos from "./pages/Catalogos";
import Citas from "./pages/Citas";
import Dashboard from "./pages/Dashboard";
import Escaner from "./pages/Escaner";
import Eventos from "./pages/Eventos";
import Historial from "./pages/Historial";
import Login from "./pages/Login";
import Mensajeria from "./pages/Mensajeria";
import Proveedores from "./pages/Proveedores";
import Recintos from "./pages/Recintos";
import Sanciones from "./pages/Sanciones";
import Usuarios from "./pages/Usuarios";
import Verificacion from "./pages/Verificacion";
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
      { path: "/dashboard",   element: <Dashboard /> },
      { path: "/accesos",     element: <Accesos /> },
      { path: "/recintos",    element: <Recintos /> },
      { path: "/eventos",     element: <Eventos /> },
      { path: "/bitacora",    element: <Bitacora /> },
      { path: "/proveedores", element: <Proveedores /> },
      { path: "/citas",       element: <Citas /> },
      { path: "/sanciones",   element: <Sanciones /> },
      { path: "/verificacion",element: <Verificacion /> },
      { path: "/mensajeria",  element: <Mensajeria /> },
      { path: "/escaner",     element: <Escaner /> },
      { path: "/usuarios",    element: <Usuarios /> },
      { path: "/catalogos",   element: <Catalogos /> },
      { path: "/historial",   element: <Historial /> },
    ],
  },
]);
