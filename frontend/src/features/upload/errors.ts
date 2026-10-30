export class UploadRequestError extends Error {
  constructor(code?: string) {
    super(errorMessage(code));
  }
}

export function errorMessage(code?: string): string {
  const messages: Record<string, string> = {
    UPLOAD_TOO_LARGE: "Súbor je príliš veľký. Zmenšite ho a nahrajte znova.",
    BATCH_LIMIT: "Dávka prekročila povolený limit. Nahrajte menej súborov.",
    MIME_MISMATCH:
      "Obsah súboru nezodpovedá jeho typu. Exportujte ho do podporovaného formátu.",
    UNSUPPORTED_CONTENT:
      "Tento obsah nie je podporovaný. Použite PDF, JPEG, PNG, XLSX alebo CSV.",
    CORRUPT_FILE:
      "Súbor je poškodený alebo chránený. Nahrajte jeho čitateľnú kópiu.",
    EMPTY_FILE: "Súbor je prázdny. Vyberte iný súbor.",
    EMPTY_DOCUMENT: "Dokument neobsahuje čitateľné údaje.",
    CONTENT_HASH_MISMATCH:
      "Uložený súbor neprešiel kontrolou integrity. Kontaktujte správcu a nahrajte originál znova.",
    PARSING_FAILED:
      "Súbor sa nepodarilo bezpečne spracovať. Nahrajte jeho čitateľnú kópiu.",
    PROCESSING_FAILED:
      "Spracovanie zlyhalo. Skúste ho zopakovať alebo kontaktujte správcu.",
    OCR_UNAVAILABLE:
      "OCR nie je nakonfigurované. Správca musí pripojiť OCR pre fotografie a skeny.",
    OCR_EMPTY: "OCR nenašlo čitateľný text. Skúste ostrejší sken.",
    OCR_TIMEOUT:
      "OCR trvalo príliš dlho. Skúste menší dokument alebo opakovanie.",
    OCR_FAILED: "OCR služba zlyhala. Skúste spracovanie zopakovať.",
    CSV_ENCODING: "CSV musí používať UTF-8 alebo UTF-16 s označením BOM.",
    CSV_MALFORMED:
      "CSV má neplatné úvodzovky alebo rôzny počet stĺpcov v riadkoch.",
    DECOMPRESSION_LIMIT:
      "Tabuľka prekročila limit rozbalenia. Rozdeľte ju na menšie súbory.",
    ROW_LIMIT: "Tabuľka má príliš veľa riadkov alebo stĺpcov. Rozdeľte ju.",
    CELL_LIMIT: "Tabuľka prekročila limit buniek. Rozdeľte ju.",
    PAGE_LIMIT: "PDF má príliš veľa strán. Rozdeľte ho.",
    IMAGE_LIMIT: "Obrázok má príliš vysoké rozlíšenie. Zmenšite ho.",
    SOURCE_LIMIT: "Dokument obsahuje príliš veľa textu. Rozdeľte ho.",
    PROCESSING_TIMEOUT:
      "Spracovanie prekročilo časový limit. Skúste menší dokument.",
    PROCESSING_INTERRUPTED: "Spracovanie bolo prerušené. Skúste ho zopakovať.",
    STORAGE_UNAVAILABLE:
      "Úložisko nie je dostupné. Skúste znova alebo kontaktujte správcu.",
    DOCUMENT_DEPENDENCY_UNAVAILABLE:
      "Spracovanie tohto formátu nie je dostupné. Kontaktujte správcu.",
    FEATURE_UNAVAILABLE: "Táto služba zatiaľ nie je dostupná. Skúste neskôr.",
    CONFLICT:
      "Stav dokumentu sa zmenil alebo bol dosiahnutý limit pokusov. Obnovte zoznam.",
    UNAUTHENTICATED: "Platnosť prihlásenia vypršala. Prihláste sa znova.",
  };
  return (
    messages[code ?? ""] ??
    "Operácia zlyhala. Skontrolujte pripojenie a skúste znova."
  );
}
