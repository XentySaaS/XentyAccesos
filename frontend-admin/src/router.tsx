import { createBrowserRouter, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import { useAuth } from "./store/auth";

function Protegida({ children }: { children: JSX.Element }) {
  const access = useAuth((s) => s.access);
  return access ? children : <Navigate to="/" replace />;
}

export const router = createBrowserRouter([
  { path: "/", element: <Login /> },
  { path: "/dashboard", element: <Protegida><Dashboard /></Protegida> },
]);
