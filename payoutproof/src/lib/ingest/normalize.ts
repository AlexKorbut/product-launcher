import type { SettlementTransaction } from "../engine/types";

/** A zeroed transaction so callers only set the fields a source provides. */
export function blankTransaction(
  partial: Partial<SettlementTransaction> &
    Pick<SettlementTransaction, "orderId" | "currency">,
): SettlementTransaction {
  return {
    skuId: undefined,
    statementId: undefined,
    statementDate: undefined,
    orderCreatedDate: undefined,
    type: "order",
    grossSales: 0,
    netSales: 0,
    customerPayment: 0,
    platformDiscount: 0,
    sellerDiscount: 0,
    salesTax: 0,
    referralFee: 0,
    transactionFee: 0,
    refundAdminFee: 0,
    affiliateCommission: 0,
    affiliatePartnerCommission: 0,
    affiliateAdsCommission: 0,
    otherFees: 0,
    shippingActual: 0,
    shippingCustomerPaid: 0,
    shippingSubsidy: 0,
    fbtFees: 0,
    adjustmentAmount: 0,
    adjustmentId: undefined,
    adjustmentReason: undefined,
    grossSalesRefund: 0,
    customerRefund: 0,
    settlementAmount: 0,
    ...partial,
  };
}
