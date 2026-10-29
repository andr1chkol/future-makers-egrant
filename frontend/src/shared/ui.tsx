import type { ButtonHTMLAttributes, ReactNode } from "react";
import { AlertCircle } from "lucide-react";

export function Button(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className="button" {...props} />;
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <p className="notice" role="status">
      <AlertCircle size={18} aria-hidden="true" />
      {children}
    </p>
  );
}

export function FeatureUnavailable({ title }: { title: string }) {
  return (
    <section className="workspace">
      <p className="eyebrow">Pracovný priestor</p>
      <h1>{title}</h1>
      <Notice>Táto funkcia zatiaľ nie je dostupná.</Notice>
      <p>
        Pripravujeme spracovanie dokumentov. Údaje bude vždy potrebné
        skontrolovať a potvrdiť.
      </p>
    </section>
  );
}
