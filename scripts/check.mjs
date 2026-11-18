import assert from 'node:assert/strict'
import {readFile, writeFile} from 'node:fs/promises'
import {createAccount} from 'genlayer-js'
import {read} from '../chain.js'
import {acceptance} from './acceptance.mjs'

const {address} = JSON.parse(await readFile(new URL('../deployment.json', import.meta.url)))
const account = createAccount()
const other = createAccount()
const owner = account.address.toLowerCase()
const key = 'atlantic-review'
const {submit, transactions} = await acceptance(address)
const campaign = () => read(address, 'read_campaign', [owner, key])
await Promise.all([
  submit('opened', account, 'open_campaign', [key, 100000000, -900000000, 400000000, -100000000, 405]),
  submit('no_owner_campaign', other, 'submit_changeset', [key, 100000000], 'CAMPAIGN_NOT_FOUND'),
])
const cases = [
  ['admitted', 100000000, 'ADMITTED'],
  ['over_budget', 100000001, 'OVER_BUDGET'],
  ['out_of_area', 100000002, 'OUT_OF_AREA'],
]
const decisions = []
for (const [label, id, outcome] of cases) {
  await submit(label, account, 'submit_changeset', [key, id])
  const decision = await read(address, 'read_decision', [owner, key, id])
  assert.equal(decision.outcome, outcome)
  assert.equal((await campaign()).remaining, 5)
  decisions.push(decision)
}
await submit('duplicate', account, 'submit_changeset', [key, 100000000], 'CHANGESET_ALREADY_EVALUATED')
await submit('closed', account, 'close_campaign', [key])
await submit('late_submission', account, 'submit_changeset', [key, 100000003], 'CAMPAIGN_CLOSED')
const final = await campaign()
assert.equal(final.status, 'CLOSED')
assert.equal(final.remaining, 5)
assert.deepEqual(final.admitted, [100000000])
assert.equal(await read(address, 'read_decision', [owner, key, 100000003]), null)
await writeFile(new URL('../evidence.json', import.meta.url), JSON.stringify({
  address, owner, key, campaign:final, decisions, transactions,
}, null, 2) + '\n')
