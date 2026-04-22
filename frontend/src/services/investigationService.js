import transactions from '../mocks/transactions.json';

function simulateDelay(ms = 250) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

export async function getTransactionById(transactionId) {
  await simulateDelay();
  const tx = transactions.find(t => t.transaction_id === transactionId);
  if (!tx) {
    throw new Error('TRANSACTION_NOT_FOUND');
  }
  return tx;
}

export async function getRelatedTransactions(accountId, excludeTransactionId) {
  await simulateDelay();
  return transactions
    .filter(
      t => t.account_id === accountId && t.transaction_id !== excludeTransactionId
    )
    .slice(0, 5);
}
