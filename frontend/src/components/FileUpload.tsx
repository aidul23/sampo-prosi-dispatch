import { useRef, useState } from "react";
import { fetchSampleOrders, uploadExcel } from "../api/client";
import type { Order } from "../types/dispatch";

interface Props {
  onOrdersLoaded: (orders: Order[], source: string) => void;
}

export default function FileUpload({ onOrdersLoaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<string>("No file uploaded yet.");
  const [busy, setBusy] = useState(false);

  async function handleFile(file: File) {
    setBusy(true);
    setStatus(`Uploading ${file.name}…`);
    try {
      const orders = await uploadExcel(file);
      onOrdersLoaded(orders, file.name);
      setStatus(`Loaded ${orders.length} orders from ${file.name}.`);
    } catch (err) {
      setStatus(`Upload failed: ${(err as Error).message}`);
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  async function handleSample() {
    setBusy(true);
    setStatus("Loading sample data…");
    try {
      const orders = await fetchSampleOrders();
      onOrdersLoaded(orders, "sample data");
      setStatus(`Loaded ${orders.length} sample orders.`);
    } catch (err) {
      setStatus(`Could not load sample data: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>1. Load orders</h2>
      <div className="row">
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls,.xlsm"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <button onClick={handleSample} disabled={busy}>
          Load sample data
        </button>
      </div>
      <p className="status-text">{status}</p>
    </section>
  );
}
