import { useState } from "react";
import Home from "./pages/Home";
import Datasets from "./pages/Datasets";

type Page = "home" | "datasets";

function App() {
  const [page, setPage] = useState<Page>("home");

  return (
    <>
      <nav>
        <button onClick={() => setPage("home")}>Home</button>
        <button onClick={() => setPage("datasets")}>Datasets</button>
      </nav>

      {page === "home" && <Home />}
      {page === "datasets" && <Datasets />}
    </>
  );
}

export default App;