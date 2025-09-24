
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import { SessionProvider } from "./context/SessionContext";
import { BreadcrumbProvider } from "./context/BreadcrumbContext";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <SessionProvider>
    <BreadcrumbProvider>
      <App />
    </BreadcrumbProvider>
  </SessionProvider>,
);
  
