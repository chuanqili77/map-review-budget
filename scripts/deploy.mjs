import assert from 'node:assert/strict'
import {readFile, writeFile} from 'node:fs/promises'
import {createAccount, createClient} from 'genlayer-js'
import {chain, reader, read, waitForFinality} from '../chain.js'

const code = await readFile(new URL('../contracts/map_review_budget.py', import.meta.url), 'utf8')
const account = createAccount()
const client = createClient({chain, account})
assert.equal(Number(await client.getChainId()), 61999)
assert.equal(BigInt(await client.request({method:'eth_gasPrice', params:[]})), 0n)
const hash = process.argv[2] ?? await client.deployContract({code, args:[], leaderOnly:false})
console.log('Deployment', hash)
const receipt = await waitForFinality(hash, status => console.log(status))
const address = receipt.data.contract_address
assert.match(address, /^0x[0-9a-f]{40}$/i)
assert.equal(await reader.getContractCode(address), code)
assert.equal(await read(address, 'read_campaign', [account.address, 'catalog-round']), null)
await writeFile(new URL('../deployment.json', import.meta.url), JSON.stringify({address, hash}, null, 2) + '\n')
console.log('Finalized deployment', address)
