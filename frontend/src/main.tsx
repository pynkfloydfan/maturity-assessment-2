
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import { SessionProvider } from "./context/SessionContext";
import { BreadcrumbProvider } from "./context/BreadcrumbContext";
import { AcronymProvider } from "./context/AcronymContext";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <SessionProvider>
    <AcronymProvider>
      <BreadcrumbProvider>
        <App />
      </BreadcrumbProvider>
    </AcronymProvider>
  </SessionProvider>,
);
  
