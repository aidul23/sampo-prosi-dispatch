import { useCallback, useEffect, useState } from "react";
import {
  deleteAddressBookEntry,
  fetchAddressBook,
  saveAddressBookEntries,
  saveAddressBookEntry,
} from "../api/client";
import type { AddressBookEntry, Order } from "../types/dispatch";

interface Props {
  orders: Order[];
  onApplyToPlan: () => Promise<void>;
  onMessage: (message: string) => void;
}

/**
 * Consignee address register: store each recurring consignee's address once.
 * Orders without an address get it filled automatically (on import, on
 * "Locate addresses", or via "Fill missing addresses in plan").
 */
export default function AddressBookPanel({ orders, onApplyToPlan, onMessage }: Props) {
  const [entries, setEntries] = useState<AddressBookEntry[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("");
  const [newConsignee, setNewConsignee] = useState("");
  const [newAddress, setNewAddress] = useState("");
  const [edits, setEdits] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setEntries(await fetchAddressBook());
    } catch (err) {
      onMessage(`Could not load address register: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [onMessage]);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    try {
      await action();
    } catch (err) {
      onMessage(`Address register: ${(err as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  function handleAdd() {
    const consignee = newConsignee.trim();
    const address = newAddress.trim();
    if (!consignee || !address) return;
    run(async () => {
      await saveAddressBookEntry(consignee, address);
      setNewConsignee("");
      setNewAddress("");
      await refresh();
      onMessage(`Saved address for "${consignee}".`);
    });
  }

  function handleSaveEdit(entry: AddressBookEntry) {
    const address = (edits[entry.id] ?? entry.address).trim();
    if (!address || address === entry.address) return;
    run(async () => {
      await saveAddressBookEntry(entry.consignee, address, entry.id);
      setEdits(({ [entry.id]: _, ...rest }) => rest);
      await refresh();
      onMessage(`Updated address for "${entry.consignee}".`);
    });
  }

  function handleDelete(entry: AddressBookEntry) {
    if (!window.confirm(`Remove "${entry.consignee}" from the address register?`)) return;
    run(async () => {
      await deleteAddressBookEntry(entry.id);
      await refresh();
    });
  }

  function handleSaveFromPlan() {
    const seen = new Set<string>();
    const fromPlan = orders
      .filter((o) => o.consignee.trim() && o.address.trim())
      .filter((o) => {
        const key = o.consignee.trim().toLowerCase();
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((o) => ({ consignee: o.consignee.trim(), address: o.address.trim() }));
    if (fromPlan.length === 0) {
      onMessage("No orders with both consignee and address to save.");
      return;
    }
    run(async () => {
      const saved = await saveAddressBookEntries(fromPlan);
      await refresh();
      onMessage(`Saved ${saved.length} consignee address(es) from the current plan.`);
    });
  }

  function handleApply() {
    run(onApplyToPlan);
  }

  const query = filter.trim().toLowerCase();
  const visible = query
    ? entries.filter(
        (e) =>
          e.consignee.toLowerCase().includes(query) || e.address.toLowerCase().includes(query)
      )
    : entries;
  const ordersWithAddress = orders.filter((o) => o.address.trim()).length;

  return (
    <section className="card">
      <div className="card-header">
        <div>
          <h2>Address register</h2>
          <p className="status-text">
            Store each recurring consignee's delivery address once. Orders without an
            address get it filled automatically.
          </p>
        </div>
        <button type="button" onClick={() => setOpen(!open)}>
          {open ? "Hide" : "Show"} register
        </button>
      </div>

      {open && (
        <>
          <div className="saved-plans-actions">
            <button
              type="button"
              onClick={handleSaveFromPlan}
              disabled={busy || ordersWithAddress === 0}
              title="Save consignee + address of every order in the current plan"
            >
              Save addresses from current plan ({ordersWithAddress})
            </button>
            <button
              type="button"
              className="btn-primary"
              onClick={handleApply}
              disabled={busy || orders.length === 0}
            >
              Fill missing addresses in plan
            </button>
          </div>

          <div className="address-book-form" style={{ marginTop: 12 }}>
            <input
              type="text"
              placeholder="Consignee (as written in the Excel)"
              value={newConsignee}
              onChange={(e) => setNewConsignee(e.target.value)}
            />
            <input
              type="text"
              placeholder="Address, e.g. Tuupakantie 10, 01740 Vantaa"
              value={newAddress}
              onChange={(e) => setNewAddress(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            />
            <button
              type="button"
              onClick={handleAdd}
              disabled={busy || !newConsignee.trim() || !newAddress.trim()}
            >
              + Add
            </button>
          </div>

          {entries.length > 5 && (
            <div className="address-book-form">
              <input
                type="search"
                placeholder="Search consignee or address"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
            </div>
          )}

          <div className="table-wrap">
            <table className="saved-plans-table address-book-table">
              <thead>
                <tr>
                  <th>Consignee</th>
                  <th>Address</th>
                  <th className="col-action">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading && entries.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="status-text">
                      Loading…
                    </td>
                  </tr>
                ) : visible.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="status-text">
                      {entries.length === 0 ? "No addresses saved yet." : "No matches."}
                    </td>
                  </tr>
                ) : (
                  visible.map((entry) => {
                    const value = edits[entry.id] ?? entry.address;
                    const dirty = value.trim() !== entry.address;
                    return (
                      <tr key={entry.id}>
                        <td>{entry.consignee}</td>
                        <td>
                          <input
                            type="text"
                            value={value}
                            onChange={(e) =>
                              setEdits({ ...edits, [entry.id]: e.target.value })
                            }
                            onKeyDown={(e) => e.key === "Enter" && handleSaveEdit(entry)}
                          />
                        </td>
                        <td className="cell-action saved-plans-row-actions">
                          <button
                            type="button"
                            onClick={() => handleSaveEdit(entry)}
                            disabled={busy || !dirty || !value.trim()}
                          >
                            Save
                          </button>
                          <button
                            type="button"
                            className="btn-danger-text"
                            onClick={() => handleDelete(entry)}
                            disabled={busy}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
