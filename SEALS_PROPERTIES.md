# Seals — Predicate Catalog (Draft)

> Companion to `SEALS_FABLE.md` (which settled the architecture: **LLM compiles free text into
> this fixed vocabulary at creation time; enforcement afterward is plain deterministic code,
> never an LLM**). This file is the actual vocabulary — the discrete "properties" the LLM is
> allowed to compile a Seal into. Nothing here is implemented. Status: draft for review.

---

## 1. How a Seal is structured

A Seal is two parties plus a list of **clauses**. Each clause is one obligation owed by one party,
gated by a trigger, with a deadline and a penalty on breach.

```json
{
  "party_a": "user:101",
  "party_b": "user:202",
  "raw_text": "If I get killed, he must kill my killer within 30 days, or he's marked.",
  "clauses": [
    {
      "obligor": "party_b",
      "trigger": { "predicate": "PLAYER_KILLED", "args": { "victim": "party_a", "killer": "$X" } },
      "obligation": { "predicate": "KILL", "args": { "target": "$X" } },
      "deadline_days": 30,
      "penalty": { "predicate": "PERSONA_NON_GRATA", "args": { "days": null } }
    }
  ]
}
```

**Party references** — the values `trigger`/`obligation` args can take for a "who":
- `"party_a"` / `"party_b"` — the two signatories.
- `"$X"` (any capital-letter variable) — a wildcard bound when the trigger fires. `PLAYER_KILLED(victim=party_a, killer=$X)` binds `$X` to whoever the killer turns out to be; the obligation `KILL(target=$X)` then means "kill *that specific person*," resolved at trigger time, not at signing time. This is the mechanism behind your own example (`killed(player_1, by=player_2)` → `kill(player_2, ...)`), generalized so the killer doesn't have to be party_a or party_b.
- `"user:<id>"` — an explicit named third party (LLM resolves a mentioned username to an id at compile time; unresolvable names bounce the Seal back to the author for correction).

**Deadline** is always `deadline_days`, always a plain integer, never inferred loosely from text ("soon," "eventually" get rejected at compile time and bounced back).

**Penalty** comes from the fixed menu in §4, never free text.

---

## 2. Trigger predicates (what has to happen to arm an obligation)

| Predicate | Args | Backed by | Status |
|---|---|---|---|
| `IMMEDIATE` | — | signing itself | **buildable now** |
| `TIME_REACHED` | `days` (from signing) | pure timer | **buildable now** |
| `TRAVELED_TO_CITY` | `party`, `city` | `FlightLog` | **buildable now** |
| `ENTERED_CITADEL` / `LEFT_CITADEL` | `party` | `CitadelStay` | **buildable now** |
| `MISSION_COMPLETED` | `party`, `mission_type="extraction"`, `with_party?` | `ExtractionMission.status=completed` | **buildable now** (extraction only — generic `Mission`/`MissionLog` is unwired, see below) |
| `CAR_SOLD` / `CAR_BOUGHT` | `party`, `car_type?` | `CarTransaction` | **buildable now** |
| `RANK_REACHED` | `party`, `rank` | `User.rank` (current-state, no change log) | **buildable with a periodic check**, cleaner with a small `RankChange` log if one gets added anyway |
| `PLAYER_KILLED` | `victim`, `killer` (or `$X`/`"any"`) | — | **blocked**: no Kill/Death model exists. `kill_simulator.py` has the math; nothing persists a kill event yet. |
| `MONEY_RECEIVED` | `from`, `to`, `min_amount?` | — | **blocked**: no P2P money transfer exists at all today |

## 3. Obligation predicates (what the bound party must do)

| Predicate | Args | Backed by | Status |
|---|---|---|---|
| `TRAVEL_TO` | `city` | `FlightLog` | **buildable now** |
| `AVOID_CITY` (negative) | `city` | `FlightLog` / `User.city` | **buildable now** |
| `COMPLETE_MISSION_WITH` | `party`, `mission_type`, `count` | `ExtractionMission` | **buildable now** |
| `SELL_CAR` / `BUY_CAR` | `car_type?` | `CarTransaction` | **buildable now** |
| `NO_CONTACT` (negative) | `target` | `Message` (DM room) | **buildable now**, but see secrecy note below |
| `KILL` | `target` | — | **blocked** on Kill/Death model |
| `REFRAIN_FROM_ATTACKING` (negative) | `target` | — | **blocked** on Kill/Death model — but *cheap once it exists*: negative obligations just need "no matching Kill row in window," no combat changes needed |
| `PAY` | `to`, `amount` | — | **blocked**: no P2P payment model |
| `TRANSFER_ITEM` | `item_type` (house/gun/car/airplane), `to` | — | **blocked**: items only move to/from an implicit market today, never player→player directly |

## 4. Penalty predicates (fixed menu — never free text)

| Predicate | Args | Notes |
|---|---|---|
| `PERSONA_NON_GRATA` | `days` (`null` = indefinite, requires a lift action) | This is your Excommunicado-equivalent. Needs: `is_persona_non_grata` + `png_until` on `User`, plus an append-only `PersonaNonGrataLog` (who, seal_id, reason, imposed_at) for auditability/appeals. **No dependency on Kill or Payment systems — buildable immediately, independent of everything else.** |
| `SEAL_BREAKER_MARK` | — (permanent, doesn't expire) | Visible dossier flag, separate from the active PNG status. Distinguishes "currently being punished" from "has broken a Seal before" (reputation history survives the punishment window). |
| `FORFEIT_MONEY` | `amount`, `to="treasury"\|party_ref` | **blocked** on P2P payment system (or at least a treasury-forfeit primitive) |

---

## 5. What's missing to make the flagship use case work

Your own wiki example — *"if I die, he should kill my killer within 30 days"* — needs `PLAYER_KILLED`
and `KILL`, both blocked on a persisted Kill/Death event. `kill_simulator.py` shows the combat
math is already designed; what's missing is a Django-side `Kill` (or `CombatLog`) row recording
`attacker_id`, `defender_id`, `city_id`, `attack_type`, `outcome`, `created_at` at the moment an
attack resolves. Once that exists, both the trigger and the negative obligation
(`REFRAIN_FROM_ATTACKING`) come almost for free — it's one more predicate reading one more table.

P2P `PAY`/`FORFEIT_MONEY` similarly need a real money-transfer primitive (which `SEALS_FABLE.md`
already flags should route through the same Treasury fee as everything else, precisely so Seals
don't become a fee-dodge channel).

## 6. Suggested v1 scope (ships before Kill/Payment systems exist)

Triggers: `IMMEDIATE`, `TIME_REACHED`, `TRAVELED_TO_CITY`, `ENTERED_CITADEL`/`LEFT_CITADEL`,
`MISSION_COMPLETED`, `CAR_SOLD`/`CAR_BOUGHT`.
Obligations: `TRAVEL_TO`, `AVOID_CITY`, `COMPLETE_MISSION_WITH`, `SELL_CAR`/`BUY_CAR`, `NO_CONTACT`.
Penalty: `PERSONA_NON_GRATA`, `SEAL_BREAKER_MARK`.

This is a real, self-contained feature — e.g. *"Meet me in Prague within 7 days or you're marked,"*
*"Run three extractions together within two weeks,"* *"Don't set foot in Miami for a month."*
It ships without waiting on combat or payments, and v2 (`KILL`, `REFRAIN_FROM_ATTACKING`, `PAY`)
slots into the same schema later — existing Seals and the compiler prompt don't need rework,
just a bigger enum.

## 7. One piece of shared infra worth building alongside v1

Right now `FlightLog`, `ExtractionMission`, `CarTransaction`, `CitadelStay` are four independent
append-only tables with no common shape. Seal-checking code would otherwise need four different
queries hand-written per predicate. Consider one unified append-only `GameEvent` table
(`event_type`, `actor_id`, `target_id?`, `city_id?`, `metadata` JSON, `created_at`) that each
existing controller writes to *in addition to* its own specific table (no need to rip out the
specific tables — they stay the source of truth for their own feature; `GameEvent` is a
generic index over them). Seal predicate checks then become one query shape against one table,
and every future event type (kills, payments, rank-ups) is a new `event_type` value, not a new
migration for the Seals system.

### 7a. Insertion pattern: signals, not manual calls, same transaction

Don't hand-add a `GameEvent.objects.create(...)` at every controller call site — it will get
missed the next time someone adds a new action. Instead, attach a `post_save` signal to each
domain model that matters (`FlightLog`, `CarTransaction`, `CitadelStay`, and `ExtractionMission`
guarded on the transition to `status="completed"`). Because Django dispatches `post_save`
synchronously inside whatever transaction the triggering `.save()` is already in, the `GameEvent`
row and the domain row commit or roll back together automatically — the only requirement is that
the controller's write already runs inside `transaction.atomic()` (or `ATOMIC_REQUESTS`).

Do **not** evaluate Seal conditions or apply penalties inside the signal itself. Defer that to
`transaction.on_commit(lambda: check_seals(event))`, so Seal consequences only fire once the
underlying data is durably committed (a rolled-back action must never arm or fulfill an
obligation).

### 7b. Matching wildcard triggers without scanning every Seal

A clause like *"if someone kills me, kill them"* compiles to
`PLAYER_KILLED(victim=party_a, killer=$X)` — `killer` is a wildcard, but `victim` is a concrete,
known user id. Every clause has at least one concrete party slot like this, even when another
slot is a wildcard. Index clauses on their concrete slots:

```
SealTriggerIndex(clause_id, predicate, slot_name, user_id)
  → (clause_9, "PLAYER_KILLED", "victim", 101)
```

When a `PLAYER_KILLED` event fires (`victim=101, killer=477`), the lookup is one indexed query —
`WHERE predicate='PLAYER_KILLED' AND slot_name='victim' AND user_id=101` — not a scan of all
players or all active Seals. `$X` binds to `477` only for clauses that matched, only at that
moment. Only index clauses whose Seal is still `active`/`waiting_trigger`; drop the index row once
a clause fires, expires, or the Seal resolves, so the index stays small and matches are
idempotent (a redelivered event can't re-arm an already-armed clause).

This handles "something happened" triggers. It does **not** handle "nothing happened by the
deadline" (e.g. a plain `deadline_days` timeout with no qualifying event) — that needs a separate
periodic Celery beat task scanning `SealClause.status='pending' AND deadline < now()`.

## 8. Note on secrecy (per existing project rule)

`TRAVELED_TO_CITY`/`AVOID_CITY` triggers necessarily reveal the target's location to the
counterparty when they fire or fail — that cuts directly against [[secrecy-over-feedback]]
(never leak another player's city/activity/cooldowns). Decide per-predicate whether the leak is
acceptable (arguably yes here, since both parties *consented* to a Seal referencing it) or
restrict location-based triggers to Seals where the party being tracked is the trigger's own
`party_a`/`party_b` and never a silent third party. `NO_CONTACT` has the same shape of concern —
enforcing it means scanning DM rows, which is fine for the two consenting signatories but should
never extend to reading a third party's messages.
