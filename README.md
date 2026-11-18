# Map Review Budget

An Intelligent Contract primitive for territorial map-review queues. A mapping campaign maintainer fixes a geographic envelope and a change-count budget. The contract admits qualifying closed OpenStreetMap changesets until that budget is spent. It provides reproducible inclusion and exclusion receipts for downstream review tooling.

## Contract behavior

| Method | Behavior |
| --- | --- |
| `open_campaign(key, south, west, north, east, budget)` | Fix a rectangle and a budget of 1–100,000 changes in the caller's namespace. |
| `submit_changeset(key, changeset_id)` | Evaluate a closed changeset against the caller-owned open campaign. |
| `close_campaign(key)` | End admissions permanently. |
| `read_campaign(owner, key)` | Read the policy, admitted IDs, remaining capacity, and status. |
| `read_decision(owner, key, changeset_id)` | Read the normalized observation and outcome, or an empty string if absent. |

Coordinates are signed integers in 10⁻⁷ degrees. Bounds are inclusive and the rectangle must have positive area. Rectangles that cross the antimeridian are unsupported.

### Consensus and admission

Validators independently fetch the indexed [OpenStreetMap changeset](https://wiki.openstreetmap.org/wiki/API_v0.6#Changesets_2). The equivalence check compares the record's numeric identity, geographic bounds, and change count after validating that it is closed. The contract then compares that agreed observation against the current campaign state.

- `ADMITTED` adds the changeset to the queue and debits its change count.
- `OUT_OF_AREA` records geographic exclusion and leaves the budget intact.
- `OVER_BUDGET` records a capacity exclusion and leaves the budget intact.

The maintainer controls which IDs to evaluate and when to close the campaign. A changeset can be evaluated once per campaign. Closing keeps prior decisions readable. The result gates review workload and does not certify edit quality, contributor identity, or individual geometry.

## Actual call example

The testnet example opens an envelope spanning 10° to 40° north and 90° to 10° west, with 405 changes of capacity.

```js
await client.writeContract({
  address,
  functionName: 'open_campaign',
  args: ['atlantic-review', 100000000, -900000000, 400000000, -100000000, 405],
  leaderOnly: false,
  value: 0n,
})
```

Using the same signer, call `submit_changeset('atlantic-review', 100000000)` after opening finalizes. The observed changeset consumes 400 units. Changesets 100000001 and 100000002 are excluded for capacity and location respectively. Call `close_campaign('atlantic-review')` to preserve the final queue with five units remaining.

## Test and reproduce

Use Node.js 24 and Python 3.

```sh
npm ci
npm test
npm run verify
```

[Deployment](deployment.json) and [testnet evidence](evidence.json) target Stable Studionet, chain 61999, at `https://studio.genlayer.com/api` with `genlayer-js@1.1.8`. The read-only verifier checks the deployment, independently re-fetches transaction receipts and reads each finalized decision and the closed campaign. Local Python tests use isolated response fixtures.

Run `npm run deploy` for a new deployment or `npm run check` for a fresh testnet campaign with temporary accounts. Both commands require zero gas price and submit zero value.
