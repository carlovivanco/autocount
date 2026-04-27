import { createBrowserRouter } from "react-router";
import { Root } from "./pages/Root";
import { Dashboard } from "./pages/Dashboard";
import { AdminPanel } from "./pages/AdminPanel";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, Component: Dashboard },
      { path: "admin", Component: AdminPanel },
    ],
  },
]);
