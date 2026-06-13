import { describe, it, expect } from "vitest";
import * as XLSX from "xlsx";
import {
  parseRows,
  parseSettlementWorkbook,
} from "../src/lib/ingest/settlement-xlsx-parser";
import { normalizeHeader } from "../src/lib/ingest/column-map";

describe("normalizeHeader", () => {
  it("lowercases, strips punctuation and parentheticals", () => {
    expect(normalizeHeader("Referral Fee Amount (USD)")).toBe("referral fee amount");
    expect(normalizeHeader("Order ID")).toBe("order id");
  });
});

describe("parseRows", () => {
  it("maps known headers into normalized transactions", () => {
    const rows = [
      {
        "Order ID": "12345",
        "SKU ID": "SKU-1",
        "Total revenue": "100.00",
        "Referral fee amount": "-6.00",
        "Total settlement amount": "94.00",
        "Order created time": "2025-09-01",
      },
    ];
    const result = parseRows(rows);
    expect(result.transactions).toHaveLength(1);
    const tx = result.transactions[0]!;
    expect(tx.orderId).toBe("12345");
    expect(tx.skuId).toBe("SKU-1");
    expect(tx.grossSales).toBe(10000);
    expect(tx.referralFee).toBe(-600);
    expect(tx.settlementAmount).toBe(9400);
    expect(tx.orderCreatedDate).toBe("2025-09-01");
    expect(result.unknownHeaders).toHaveLength(0);
  });

  it("reports unknown headers but does not crash", () => {
    const rows = [
      { "Order ID": "1", "Total settlement amount": "10.00", "Mystery Column": "x" },
    ];
    const result = parseRows(rows);
    expect(result.unknownHeaders).toContain("Mystery Column");
    expect(result.transactions).toHaveLength(1);
  });

  it("ignores descriptive columns we intentionally skip", () => {
    const rows = [
      { "Order ID": "1", "Product Name": "Widget", "Total settlement amount": "10.00" },
    ];
    const result = parseRows(rows);
    expect(result.unknownHeaders).not.toContain("Product Name");
  });

  it("skips rows without an order id and counts them", () => {
    const rows = [
      { "Order ID": "1", "Total settlement amount": "10.00" },
      { "Total settlement amount": "5.00" },
    ];
    const result = parseRows(rows);
    expect(result.transactions).toHaveLength(1);
    expect(result.skippedRows).toBe(1);
  });

  it("infers refund type from refund columns", () => {
    const rows = [
      { "Order ID": "1", "Customer refund amount": "(10.00)", "Total settlement amount": "-10.00" },
    ];
    const result = parseRows(rows);
    expect(result.transactions[0]!.type).toBe("refund");
    expect(result.transactions[0]!.customerRefund).toBe(-1000);
  });
});

describe("parseSettlementWorkbook end-to-end", () => {
  it("reads a generated XLSX workbook and parses the transaction sheet", () => {
    const wb = XLSX.utils.book_new();
    const summary = XLSX.utils.aoa_to_sheet([["Statements summary"], ["Total", "100"]]);
    const orders = XLSX.utils.json_to_sheet([
      {
        "Order ID": "A1",
        "Total revenue": "50.00",
        "Referral fee amount": "-3.00",
        "Total settlement amount": "47.00",
      },
      {
        "Order ID": "A2",
        "Total revenue": "20.00",
        "Referral fee amount": "-1.20",
        "Total settlement amount": "18.80",
      },
    ]);
    XLSX.utils.book_append_sheet(wb, summary, "Summary");
    XLSX.utils.book_append_sheet(wb, orders, "Order details");
    const buf = XLSX.write(wb, { type: "array", bookType: "xlsx" }) as ArrayBuffer;

    const result = parseSettlementWorkbook(buf);
    // should have picked the "Order details" sheet, not "Summary"
    expect(result.transactions).toHaveLength(2);
    expect(result.transactions.map((t) => t.orderId).sort()).toEqual(["A1", "A2"]);
  });
});
