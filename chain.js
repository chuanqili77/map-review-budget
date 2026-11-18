import {createClient} from 'genlayer-js'
import {studionet} from 'genlayer-js/chains'

export const chain = studionet
export const explorer = 'https://explorer-studio.genlayer.com'
export const reader = createClient({chain})

export async function read(address, functionName, args) {
  const result = await reader.readContract({address, functionName, args, transactionHashVariant:'latest-final'})
  return result ? JSON.parse(result) : null
}

export async function waitForFinality(hash, onStatus = () => {}) {
  for (let attempt = 0; attempt < 120; attempt++) {
    const tx = await reader.getTransaction({hash}).catch(() => null)
    if (tx) {
      const label = tx.statusName ?? tx.status
      onStatus(label)
      if ([7, 'FINALIZED'].includes(tx.status) || label === 'FINALIZED') {
        const receipts = [tx.consensus_data?.leader_receipt].flat()
        const leader = receipts.find(item => item?.mode === 'leader') ?? receipts[0]
        if (![6, 'MAJORITY_AGREE'].includes(tx.result) || leader?.execution_result !== 'SUCCESS') {
          const reason = leader?.result?.status === 'rollback' ? leader.result.payload : ''
          throw Error('Finalized without successful execution.' + (reason ? ' ' + reason : ''))
        }
        return tx
      }
      if ([8, 'CANCELED', 'UNDETERMINED', 'LEADER_TIMEOUT', 'VALIDATORS_TIMEOUT'].includes(label)) {
        throw Error('Consensus stopped: ' + label)
      }
    }
    await new Promise(resolve => setTimeout(resolve, 3500))
  }
  throw Error('Finality is still unconfirmed. Use the transaction link before retrying.')
}
