import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import {read, reader, waitForFinality} from '../chain.js'
import {validateReceipt} from './acceptance.mjs'

const load = path => readFile(new URL(path, import.meta.url), 'utf8')
const [deployment, proof, source] = await Promise.all([
  load('../deployment.json').then(JSON.parse),
  load('../evidence.json').then(JSON.parse),
  load('../contracts/map_review_budget.py'),
])
const {address} = deployment
assert.equal(Number(await reader.getChainId()), 61999)
assert.equal(proof.address, address)
assert.equal(await reader.getContractCode(address), source)
const provision = await waitForFinality(deployment.hash)
assert.equal(provision.data.contract_address.toLowerCase(), address.toLowerCase())
for (const [label, entry] of Object.entries(proof.transactions)) {
  validateReceipt(await reader.getTransaction({hash:entry.hash}), address, entry)
  console.log(label, 'FINALIZED', entry.reason ?? 'SUCCESS')
}

const {owner, key, decisions, campaign} = proof
const final = await read(address, 'read_campaign', [owner, key])
assert.deepEqual(final, campaign)
assert.deepEqual([final.status, final.budget, final.remaining, final.admitted], ['CLOSED', 405, 5, [100000000]])
for (const decision of decisions) {
  assert.deepEqual(await read(address, 'read_decision', [owner, key, decision.id]), decision)
}
assert.deepEqual(decisions.map(row => row.outcome), ['ADMITTED','OVER_BUDGET','OUT_OF_AREA'])
assert.equal(await read(address, 'read_decision', [owner, key, 100000003]), null)
console.log('Campaign balances, decision receipts and closed-state readback are verified.')
