import { createBrowserRouter, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Proveedores from "./pages/Proveedores";
import Recintos from "./pages/Recintos";
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
      { path: "/proveedores", element: <Proveedores /> },
    ],
  },
]);
