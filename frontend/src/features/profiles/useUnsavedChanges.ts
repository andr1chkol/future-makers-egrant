import { useEffect } from "react";

export function useUnsavedChanges(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return;
    const unload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    const followLink = (event: MouseEvent) => {
      const link =
        event.target instanceof Element
          ? event.target.closest("a[href]")
          : null;
      if (
        link instanceof HTMLAnchorElement &&
        link.href !== window.location.href &&
        !window.confirm("Máte neuložené zmeny. Chcete ich zahodiť?")
      ) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    // BrowserRouter has no useBlocker support. The Navigation API can cancel
    // same-document back/forward navigation without changing shared routing.
    const navigation = (window as Window & { navigation?: EventTarget })
      .navigation;
    const traverse = (event: Event) => {
      const navigationEvent = event as Event & { navigationType?: string };
      if (
        navigationEvent.navigationType === "traverse" &&
        event.cancelable &&
        !window.confirm("Máte neuložené zmeny. Chcete ich zahodiť?")
      )
        event.preventDefault();
    };
    window.addEventListener("beforeunload", unload);
    document.addEventListener("click", followLink, true);
    navigation?.addEventListener("navigate", traverse);
    return () => {
      window.removeEventListener("beforeunload", unload);
      document.removeEventListener("click", followLink, true);
      navigation?.removeEventListener("navigate", traverse);
    };
  }, [dirty]);
}
