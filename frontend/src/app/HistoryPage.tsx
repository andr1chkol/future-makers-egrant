import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../shared/api";
import { Button, Notice } from "../shared/ui";

const statuses = {
  queued: "Čaká na spracovanie",
  running: "Spracováva sa",
  ready: "Pripravené na kontrolu",
  failed: "Spracovanie zlyhalo",
};

export function HistoryPage() {
  const [offset, setOffset] = useState(0);
  const history = useQuery({
    queryKey: ["history", offset],
    retry: false,
    queryFn: async () => {
      const result = await api.GET("/api/v1/extractions", {
        params: { query: { limit: 20, offset } },
      });
      if (result.error) throw new Error(result.error.error.code);
      return result.data;
    },
    refetchInterval: (query) =>
      query.state.data?.data.some((item) =>
        ["queued", "running"].includes(item.status),
      )
        ? 5000
        : false,
  });
  return (
    <section className="workspace">
      <p className="eyebrow">Pracovný priestor</p>
      <h1>História spracovania</h1>
      {history.isPending ? (
        <Notice>Načítavame históriu…</Notice>
      ) : history.isError ? (
        <>
          <p role="alert">
            {history.error.message === "FEATURE_UNAVAILABLE"
              ? "História bude dostupná po pripojení modulu extrakcie."
              : "Históriu sa nepodarilo načítať."}
          </p>
          <Button onClick={() => void history.refetch()}>Skúsiť znova</Button>
        </>
      ) : history.data.data.length === 0 ? (
        <Notice>Zatiaľ tu nie sú žiadne spracovania.</Notice>
      ) : (
        <ul className="history-list">
          {history.data.data.map((item) => (
            <li key={item.id}>
              <div>
                <strong>{statuses[item.status]}</strong>
                <span>
                  {new Date(item.createdAt).toLocaleString("sk-SK")} ·{" "}
                  {item.mode === "fixture"
                    ? "Ukážkové údaje"
                    : "Živé spracovanie"}
                </span>
                <span className="resource-id">{item.id}</span>
              </div>
              {item.status === "ready" && (
                <Link className="text-link" to={`/review/${item.id}`}>
                  Skontrolovať údaje
                </Link>
              )}
              {item.status === "failed" && (
                <span>Otvorte dokument a overte možnosti opakovania.</span>
              )}
            </li>
          ))}
        </ul>
      )}
      <div className="pagination" aria-label="Stránkovanie histórie">
        <Button
          disabled={offset === 0 || history.isFetching}
          onClick={() => setOffset(Math.max(0, offset - 20))}
        >
          Predchádzajúce
        </Button>
        <Button
          disabled={
            !history.data ||
            offset + 20 >= history.data.pagination.total ||
            history.isFetching
          }
          onClick={() => setOffset(offset + 20)}
        >
          Nasledujúce
        </Button>
      </div>
    </section>
  );
}
