import assert from 'node:assert/strict'
import {writeFile} from 'node:fs/promises'
import {createClient} from 'genlayer-js'
import {chain, reader, waitForFinality} from '../chain.js'

export async function acceptance(address) {
  assert.equal(Number(await reader.getChainId()), 61999)
  assert.equal(BigInt(await reader.request({method:'eth_gasPrice', params:[]})), 0n)
  const transactions = {}
  let checkpoint = Promise.resolve()
  const log = new URL('../.acceptance-progress.json', import.meta.url)
  return {
    transactions,
    async submit(label, account, method, args, reason) {
      const client = createClient({chain, account})
      const hash = await client.writeContract({address, functionName:method, args, value:0n, leaderOnly:false})
      transactions[label] = {hash, sender:account.address.toLowerCase(), method, args, ...(reason ? {reason} : {})}
      checkpoint = checkpoint.then(() => writeFile(log, JSON.stringify(transactions, null, 2) + '\n'))
      await checkpoint
      console.log(label, hash)
      const finalized = waitForFinality(hash)
      if (!reason) {
        await finalized
      } else {
        await assert.rejects(finalized, new RegExp(reason))
        const tx = await reader.getTransaction({hash})
        validateReceipt(tx, address, transactions[label])
      }
      console.log(label, 'FINALIZED', reason ?? 'SUCCESS')
    },
  }
}

export function validateReceipt(tx, address, entry) {
  assert.ok(tx.status === 7 || tx.statusName === 'FINALIZED')
  assert.ok([6, 'MAJORITY_AGREE'].includes(tx.result))
  assert.equal(tx.from_address.toLowerCase(), entry.sender)
  assert.equal(tx.to_address.toLowerCase(), address.toLowerCase())
  const leader = [tx.consensus_data?.leader_receipt].flat().find(receipt => receipt?.mode === 'leader')
  // The consensus node renders positional arguments with a trailing comma.
  const args = entry.args.map(arg => JSON.stringify(arg) + ',').join('')
  const expected = '{"args":[' + args + ']"method":' + JSON.stringify(entry.method) + '}'
  assert.equal(leader.calldata.readable, expected)
  assert.equal(leader.execution_result, entry.reason ? 'ERROR' : 'SUCCESS')
  if (entry.reason) assert.equal(leader.result.payload, entry.reason)
}
