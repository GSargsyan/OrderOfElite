# Order of Elites — Game Design Analysis

*A grand-level design review: what will work, what won't, and why. Written to be argued with.*

---

## 1. The verdict, up front

The game can work. Not "will definitely work" — but the core bet is sound, several of your ideas
are genuinely better than what the genre usually produces, and the failure modes are known and
avoidable. The three biggest risks are not the ones you'd guess:

1. **You are designing a 5,000-player game and you will launch with 40.** Almost every feature
   in the wiki (Grand Council, syndicate wars, 4-player missions, per-city chat, market
   competition) assumes a population you won't have for a long time, possibly ever. This is the
   single most important lens in this document, and it reshapes everything else.
2. **Your flagship fantasy is locked behind a year of grinding.** Rank 30 → Grand Council needs
   365 days. Rank 20 → Chairman needs 120. Rank 9 just to *enter the Citadel*. The things that
   make your game *your game* are invisible to every player for months. The first-day experience
   is clicking "Stakeout" every 6 minutes, alone.
3. **Permadeath in a small population is a self-extinguishing fire.** It's also your best
   feature. Handling this tension correctly is the design problem of the whole project.

None of these are fatal. All of them are fixable at the design level, before code. Let's go
through everything.

---

## 2. The genre you're actually entering

Some honest history, because you named mafia-family.com and it matters.

Text-based crime PBBGs had their golden age roughly 2003–2011: Omerta, Bootleggers, Mobstar,
TheCrims, mafia-family, and dozens of clones. Several had permadeath and it *worked* — Bootleggers
and Omerta at their peak were dramatic precisely because death was real. People still write
nostalgia posts about being shot in Bootleggers in 2006. Torn is the genre's lone big survivor
(tens of thousands of daily actives after 20+ years, notably *without* permadeath).

Why did the others die? Mostly not copyright (that finished some off, but it was the last blow,
not the first). The real killers were:

- **Population collapse.** These games are social organisms. The mechanics are an excuse; the
  product is the chat, the gossip, the feuds, the politics. When the social graph thins below a
  critical mass, the game *feels* dead long before it *is* dead, and the feeling is
  self-fulfilling. mafia-family almost certainly died this way — the death spiral, not the lawyers.
- **Multi-accounting and cheating.** Every one of these games lost its competitive legitimacy to
  alts — scout accounts, feeder accounts, intel alts. Once the honest players believe the top
  players are cheating, they leave.
- **Stagnation + aging UX.** No mobile, no updates, same loop for years.

The lesson set is clear: your competition isn't other assassin games, it's the death spiral, the
alt problem, and boredom. Everything below should be read against those three enemies.

Who plays these games today? A niche but *loyal* audience: 25–45, nostalgic for exactly the games
above, plays in browser tabs at work and on phones in bed, values depth and social stakes over
graphics. They exist, they congregate (r/PBBG, Torn's diaspora, old Omerta/Bootleggers Discords),
and they are *reachable*. 100 active players is a realistic goal. 1,000 is hard. 10,000 would
require luck plus years. Design for the 100 first — genuinely design for it, don't just hope past it.

---

## 3. The one number that rules everything

Take every feature in the wiki and ask: **"What does this feel like with 40 concurrent players?"**

- Per-city chat, 4 cities: 40 players ÷ 4 cities ÷ (most offline) = **3 people in a chat room.**
  A dead chat room is the strongest "this game is dead, leave" signal that exists. At launch, chat
  must be **global** (tag messages with the sender's city for flavor if you want). Split it per-city
  only when a single room is genuinely too busy — that's a champagne problem you should pray to have.
- High-Profile Assassination: 4 players, same city, 2 with attack-skill thresholds, 1 with a
  driving threshold, simultaneously online and willing. At 40 players this mission will fire
  approximately never. Even Extraction (2 players, same city, one with a car) will be hard to
  assemble. **Any content gated on simultaneous co-presence is large-population content.**
- Syndicate wars: at 100 players you'll have 2–4 syndicates. "War" between a 12-person syndicate
  and a 9-person one is a group DM argument, not a war.
- Market competition (supply/demand pricing per city): with 5 sellers per city, one player *is*
  the market. Your formulas assume statistical crowds.

I'm not saying cut these. I'm saying: **sequence them.** The wiki reads like a final-state design
document. What it's missing is a *launch-state* design — the version of the game that is fun with
40 people, from which the final state grows. Concretely, the launch game should be built around
things that work at any population:

- The 1v1 kill dance (intel, stalking, Citadel timing) — works with 20 players.
- Solo missions and the drug loop — works with 1 player.
- Global chat — works with 10.
- Seals — works with 2.
- NPC targets (see §10) — work with 1.

And two cities, not four. You can open Moscow and Rome later as an *event* ("The Order expands
east") — which turns your own growth into content.

---

## 4. Permadeath — the core bet, and it's the right one

Permadeath is your most important design decision and you got the fundamentals right. Let me be
precise about *why* it works, because the why dictates how to protect it.

**Why permadeath works:** It's the only mechanic in gaming that produces genuine fear, and fear is
the substrate of every emotion the genre is remembered for. Nobody writes nostalgia posts about
grinding. They write them about the night they got shot, the betrayal that preceded it, the
revenge that followed. Permadeath converts gameplay into *biography*. It's also, quietly, your
economy's master valve: killing a rich player deletes ~60% of their wealth from the game. Your
money sinks and your drama engine are the same mechanic. That's elegant design, whether you did it
on purpose or not.

**Why permadeath kills games:** at small populations, each death removes a node from an already
sparse social graph. Victim quits → fewer targets and fewer chat voices → killers get bored →
they quit → repeat. One dedicated killer with a 9-hour cooldown can kill ~2 players a day; at 100
players that's a server-emptying rate. The successful permadeath games survived because death was
*statistically rare per capita* (huge populations) and because social structures (families,
retaliation) made killing expensive.

**Your mitigations, graded:**

- **Rebirth (old nickname visible, 2x exp catch-up, 40% money carryover): excellent.** This is the
  best version of this mechanic I've seen in the genre. The key insight — which you seem to have
  hit intuitively — is that players don't primarily fear losing *stuff*, they fear losing
  *identity*. Letting the new account carry the old name as a scar ("formerly known as X")
  preserves identity continuity while keeping the sting. Death becomes a dramatic chapter break,
  not an account deletion. Guard this feature; it's the difference between "permadeath game" and
  "game people actually keep playing after dying."
- **Rank 9 to be killable, Rank 10 to kill: correct instinct**, protects newbies. But note the side
  effect: it also defines a sharp cliff. The day you hit Rank 9 you go from untouchable to prey,
  probably before you understand the defense game. Consider making the transition ceremonial and
  *loud* — the game formally notifies you that you are now "on the books," explains the Citadel,
  the intel economy, and the bank, as an in-fiction rite. A player who dies confused churns; a
  player who dies *knowing they gambled* re-registers.
- **The Citadel: good**, and the 12h-in/2h-out rhythm is a clever fear-driven appointment mechanic
  (more in §8).
- **What's missing entirely: protected absence.** In your current design, going on vacation for a
  week means logging in dead. That is the #1 long-term churn mechanism in fear-based games — not
  the fear itself, but the *inability to ever put the game down*. Fear-of-loss drives daily logins
  for months and then one day produces "I can't live like this" and an uninstall. You need an
  off-the-grid mechanic, and your fiction hands it to you gift-wrapped: an Elite can **go dark**
  (retire temporarily, leave the city, "sabbatical under the Order's protection") — untargetable,
  but also unable to act, earn, or accrue interest, with a meaningful cooldown so it can't be
  combat-abused. Torn survives 20 years partly because being offline doesn't mean losing
  everything. This is a grand-level gap in the wiki. Fill it before launch.

**One warning:** resist all future temptation to soften permadeath further (insurance items, second
chances, revival tokens — the monetization devil will whisper these). The rebirth mechanic is
already the correct amount of soft. If death stops being scary, you lose the only thing
differentiating you from a hundred dead Torn clones, and the players you attracted *because* of
permadeath — your core — will leave first.

---

## 5. The name and the theme

**The theme is right.** John Wick is the best possible skin for this genre in 2026: currently
beloved, tonally perfect for text (ritual, formality, consequences — all of which render in *prose*
better than action does), and structurally aligned with your mechanics (a hotel that is neutral
ground, a council, markers, excommunication — the films practically contain a game design doc).
Your instinct to keep all text formal-but-cool is exactly correct and you should enforce it
ruthlessly, including on button labels and error messages. Tone discipline is cheap and it's the
thing screenshots carry.

**The legal instinct is also right.** mafia-family died with Scarface images on its pages; you've
renamed every gun, car, and plane (Krasny 47, Bordeaux V16 — these are good), you say "Citadel" not
"Continental." Keep that discipline total: never the words "John Wick" in game or marketing, no
AI art that visibly imitates the films, no "High Table," no "Excommunicado" verbatim ("Persona non
grata" is a real Latin term and safe; it's also honestly the better phrase). "Inspired by neo-noir
assassin cinema" is the most you ever say out loud.

**The name itself is your weakest branding asset.** "Order of Elites" has two problems:

1. **"Elites" is flattery, not fiction.** The John Wick vocabulary works because it's mundane
   words made sinister — a *hotel*, a *table*, a *marker*, a *ledger*. Concrete nouns, institutional
   language. "Elites" is an adjective wearing a trench coat; it tells the player they're cool
   instead of showing them an institution with weight. It also reads adjacent to hustle-culture
   scam branding ("join the elite"), which is a real first-impression tax on a signup page.
2. **Calling every Rank-1 player an "Elite" undercuts your own progression.** In your fiction,
   status should be scarce and earned. If everyone is an Elite on day one, the word means nothing
   by day two.

I wouldn't necessarily rename the *game* at this point — the domain, the codebase, and momentum
have value, and no game ever died of a mediocre name. But consider: (a) the *institution* in-fiction
can carry a heavier name than the game title (the ruleset being called "the Order" is good — lean
on that); (b) the *player noun* is worth rethinking — even "Operative," "Contractor," or a rank-gated
use of "Elite" (you *become* an Elite at some rank; below that you're an "Aspirant" or "Associate")
would convert the word from flattery into a goal. That last option is cheap and turns your weakest
word into a progression carrot.

---

## 6. The Grand Council — the dream vs. the arithmetic

The dream: players governing players, EVE-style emergent politics, rules written by winners and
enforced on everyone. This dream is *achievable* — eRepublik, EVE, CyberNations, and NationStates
all proved players will generate astonishing drama when handed real power. Player governance
produced the most legendary stories in gaming history. You're right to want it.

Now the arithmetic and the failure modes:

**Problem 1 — the year-long vacuum.** Grand Council requires Rank 30 = 365 days. Your marquee
feature cannot exist until the game's first birthday, assuming anyone grinds that long in a game
whose marquee feature doesn't exist. Chairman needs Rank 20 = 120 days. This is a launch-sequencing
bug at the highest level. Options: launch-era rank requirements that ratchet up over time ("the
first Council is seated from the five highest-ranked Elites at week 4, whatever rank they are");
or explicitly seasonal terms where early seasons have low bars. Either way, **the Council must
exist within the first month of launch** or it's vaporware to your founding population — and your
founding population are the people who'll decide if the game lives.

**Problem 2 — how are the five chosen?** The wiki says "rotated every week/month" (it says both,
pick one) but never says *by what mechanism*. This is the single most consequential unanswered
question in the document:

- *Top 5 by rank:* an oligarchy of grinders. Stable, boring, zero drama. The same names forever.
- *Random among eligibles:* fair, but power without pursuit is weightless — nobody campaigns,
  nobody cares.
- *Election:* this is where the gold is. Campaigning, bribery, syndicate bloc voting, betrayal,
  vote-buying scandals — in every game that ever had elections, the elections became the content.
  If you want players to "do cool things" with governance, they need to *fight* for it, publicly.

My strong recommendation: elections, with candidacy gated by rank and a candidacy *fee* (a money
sink and a seriousness filter). Weekly is too fast for drama to build; monthly terms feel right —
the wiki's "rotated each month" under General Terms is the better of your two versions.

**Problem 3 — Council membership currently means *not playing*.** No missions, no assassinations.
You've designed the reward for winning the political game as the removal of the actual game. The
best players will either refuse the seat or park an alt in it. The protective intent is good
(sitting members shouldn't be assassins), but frame power as *more* game, not less: Council
members get exclusive verbs — setting the Treasury commission rate within bounds, funding public
bounties from the Treasury, pardoning a Persona non grata, one "Decree" per term with a mechanical
effect (a tax holiday, a city lockdown, doubled mission payouts for a weekend). If the Council can
pull levers that every player *feels*, then the ruleset stops being a message-of-the-week and
becomes law. Which brings us to—

**Problem 4 — rules without teeth.** "The Order of the Elites" as a free-text ruleset enforced by
humans tagging violators PNG is workable but fragile: it's a moderation burden wearing a costume,
and favoritism accusations are guaranteed (some of that is spicy content; too much is toxicity).
Two stabilizers: make punitive tags *cost* something (a Chairman spends Treasury money or personal
standing to tag someone PNG — power with a price is politics; free power is abuse), and give the
Council override/pardon authority so there's an appeals drama loop instead of a resentment dead-end.
Longer term, the more of the "law" you can make *mechanically* enforceable (via exactly the
predicate machinery you're building for Seals — a Decree is just a Seal with the whole server as
party B), the more real the government becomes. That's a genuinely novel direction almost nobody
in the genre has built: **legislation as code, drafted by players.** You're closer to it than you
realize.

---

## 7. Seals — your ace. Protect it.

Straight assessment: **Seals are the most original feature in this design and the best claim you
have to being a new game rather than a well-themed clone.** Mechanically enforced player-to-player
promises essentially do not exist in this genre — deals in mafia games have always run on trust
and forum screenshots. You are proposing to mechanize the Marker, which is not just thematically
on-brand, it's *the* dramatic engine of the source material. "I owe him. The game itself will make
me pay" is a sentence that markets your game by itself.

Your architecture decision (per SEALS_PROPERTIES.md: LLM compiles free text into a fixed predicate
vocabulary at creation time, enforcement is deterministic code, never an LLM) is the correct one —
the naive "LLM judges the logs" design would have been a disputes-and-hallucinations tarpit. Good
engineering judgment there.

Three grand-level warnings:

1. **Sequencing: Seals are hostage to the kill system and P2P transfers.** Your own predicate
   table shows `PLAYER_KILLED` and `MONEY_RECEIVED` blocked — and those two are the narrative heart
   of the feature. A Seal that can only trigger on "traveled to Rome" or "sold a car" is a toy.
   Don't ship Seals before kills and transfers exist, or the feature makes its first impression as
   a gimmick and first impressions on features are nearly as sticky as on games. Ship it when
   "avenge my death" is expressible — that's the demo, that's the trailer, that's the Reddit post.
2. **Do not paywall it.** The wiki says "available to pro players only." I understand the
   monetization logic and it's wrong for *this* feature: Seals are a network-effect mechanic (each
   one binds two players and its story spreads to many more) and your single strongest
   differentiator. Paywalling it caps its spread exactly where you need it viral. Monetize
   convenience and cosmetics (more on this in §12); never monetize the thing that makes people
   tell their friends about you. If you must gate it, gate by *rank* — earned, not bought.
3. **Breach must be survivable but scarring.** If the penalty menu is too brutal, nobody signs
   Seals (the genre's players are sharks; they price risk instantly). If too soft, Seals are
   decorative. The sweet spot is *reputational*: breach marks your profile, permanently and
   publicly. "Oathbreaker" on a dossier card in a game about a code is worse than losing money —
   and it costs you nothing to enforce.

---

## 8. The kill loop — quietly your best-designed system

Reading the wiki, the intel-and-assassination dance is the most complete piece of design in it,
and it deserves to be recognized as the *core loop* of the whole game:

- Paying Elite coins to progressively narrow a target's location (same city? → status? → which
  city?) is a genuinely tense cat-and-mouse with real information economics. Blind attempts as the
  budget option adds a gambling texture. This works at *any* population — it's 1v1.
- The Citadel's 12h-max-stay / 2h-cooldown rhythm means safety is a *schedule*, and schedules leak.
  Watching a target's pattern to predict their exposure window is emergent stalking gameplay that
  costs you zero additional code. The 2-hour forced exposure is the heartbeat of the whole PvP game.
- Three attack types with different risk/backfire profiles (and sniping as a multi-attacker
  chip-damage tool — implicit raid content!) give tactical texture.
- The backfire mechanic (failed attacks reverse roles) is the right deterrent against spam.

Three grand-level notes on it:

1. **The alt problem will hit this system first and hardest.** Your entire intel economy — the
   most elegant thing in the design — is bypassed by a free guest account in the target's city
   DMing the killer "he's here, he's driving." Every mafia PBBG fought this war and most lost.
   You cannot fully solve multi-accounting, but you must have a *stance* from day one: guest
   accounts can't see other players' statuses or locations at all, new accounts have intel
   functions locked for days, and you log enough (IP/device fingerprint correlation between
   scout-pattern accounts) to ban with confidence. This isn't a feature, it's regime defense: the
   moment your players believe kills are alt-assisted, the competitive legitimacy that permadeath
   depends on is gone. Budget real design time for this; it is not a post-launch cleanup item.
2. **Survivor punishment is backwards.** "The attacked player loses $10,000 per percent of health
   lost" — the *victim* of a failed assassination pays up to a million dollars for the crime of
   surviving? Getting attacked while offline and waking up poorer *and* hurt, having done nothing,
   is the kind of unfairness that churns players silently (they don't complain, they just stop
   logging in — this is the Secrecy-over-feedback principle's evil twin: silent punishment invites
   silent quitting). Healing costs at the Hospital (which you already have as a business!) achieve
   the same money sink with agency attached. Attackers should bear the cost of failure; that's
   what the backfire is for.
3. **Kill velocity needs a governor at small populations.** 9h cooldown = ~2 kills/day/killer =
   one bored veteran can depopulate a 100-player server in a month. Consider making assassinations
   of *real players* expensive in fiction and mechanics — a mandatory contract fee to the Treasury
   ("the Order taxes blood"), scaling with your recent kill count. Serial killing stays possible
   but becomes a visible, funded, *political* act (the Treasury getting rich off a murderer is
   Council drama fuel), rather than a free hobby. Population protection disguised as theme.

---

## 9. Economy — one grand point only

You asked me to skip the medium-sized economy notes, so just the structural one:

**Your economy's true sink is murder, and that's a feature — but it means the economy only works
if the kill game works.** Missions, drug production, bank interest, and businesses all *create*
money; fees and maintenance drain slowly; the only violent, scalable removal of wealth is death
(60% of a victim's cash evaporates). You've accidentally (or brilliantly) built an economy where
inflation is regulated by assassination. Two consequences worth internalizing:

- **Wealth must attract violence for the loop to close.** The 5%-to-killer transfer is weak
  motivation to hunt whales. Player-opened contracts/bounties (in your ideas list — promote it to
  core) are the missing piece: they let the *whole server* price a rich player's head. And
  businesses becoming purchasable on the owner's death is the single best idea in the wiki's
  economy — it gives assassination an *economic motive* ("kill the man who owns every gas station
  in New York" is an emergent quest no designer has to write). Connect these deliberately: wealth
  → visibility (histograms, rankings, dossiers) → bounties → death → redistribution. That's a
  self-regulating economy with a plot.
- **The bank's 0.5% daily compound interest fights your own design** — it rewards hoarding wealth
  in the one place violence can't fully reach it, i.e., it pays players to *disengage* from the
  loop above. At the grand level: passive yield in a game whose economy is balanced by predation
  is a contradiction. Keep the bank as death insurance (that part is well-designed); be very
  suspicious of it as an income source.

---

## 10. Onboarding — the first hour is the entire funnel

The genre's traditional fatal flaw, faithfully reproduced in the current wiki: **the fantasy is
"you are an elite assassin in a secret order," and the first session is clicking a button every
six minutes, alone, to earn $200.** Every locked door (Citadel at 9, killing at 10, syndicates at
7, Council at 30) is a promise, but day-one players don't experience promises — they experience
the room they're standing in, and right now that room is empty.

You already own the solution — it's sitting in your own ideas list marked as "maybe":

- **The debut contract ("kill an NPC within X hours") is not a maybe. It's the most important
  screen in the game.** A new player must *assassinate someone* — stake them out, buy the cheap
  pistol, pick the moment, see a kill transcript with their name on it — within the first 15
  minutes, even if the target is an NPC and the outcome is nearly rigged. This is the moment the
  player decides whether your fantasy is real. Everything about the account can be tutorialized
  through this one contract (missions fund the gun, training raises the odds, the transcript
  teaches the kill report format they'll someday appear in for real).
- **NPC contracts also solve the small-population problem** (§3): a roster of procedurally-flavored
  NPC marks ("a banker under the Order's protection has broken the code…") gives solo players the
  assassin loop every day regardless of how many humans are online, exercises the same
  skills/weapons/intel systems, and — crucially — keeps the *killers* fed so they're less tempted
  to depopulate your real player base out of boredom. Your "Solo Assassination Missions (cross
  city)" line is already this; elevate it from a mission type to the backbone of solo play.
- **Let new players walk into the Citadel.** It's the most iconic set-piece of your fiction and
  Rank-1 players can't enter the building for weeks? Split the two functions: the Citadel as
  *social space* (see the chat, the boards, the atmosphere — the lobby, in hotel terms) from day
  one; the Citadel as *mechanical fortress* (the defense multiplier) at Rank 9 as designed. New
  players should stand in the lobby and watch the veterans, wanting.

---

## 11. Social architecture — the game is the people

Restating the genre's iron law: mechanics recruit players; *people* retain them. A player whose
syndicate expects them online, who has a rival, who has a Seal outstanding and a grudge pending,
cannot quit — quitting would have social meaning. A player with none of those quits the moment the
grind bores them, which is roughly day nine. Every system should be evaluated by whether it
manufactures relationships:

- **Global chat at launch** (§3). Non-negotiable, in my view. A busy room is the product.
- **Syndicates are more load-bearing than the wiki treats them.** They're your retention engine,
  your newbie protection racket (join one and killers think twice — retaliation is deterrence),
  your content generator (wars), and eventually your political parties (Council bloc voting). Two
  wiki numbers to reconsider at grand level: Rank 7 to *join* is too late — social embedding must
  happen in week one, before the boredom window, not after it (let low ranks join as "Associates"
  even if full membership rights come later); and the 20-member cap at your populations means two
  syndicates could contain
  the entire active server — fine early, but it makes the cap itself a political object (who gets
  cut?). That's drama, which is fine, as long as you meant it.
- **Kill transcripts, Last Wills, Dossier cards — these are not flavor ideas, they're your entire
  marketing department.** More in §12, but socially: a death in your game should be a *public
  event* — a transcript in the feed, a Last Will published to all, the killer's dossier updated,
  the widow syndicate swearing revenge in global chat. The 2005 games generated this drama and let
  it evaporate into forum posts. You can capture it in artifacts. Design every death to produce a
  story object.
- **Ratings/reviews of other players (Rank 4)**: careful — in a game about reputation, a 1–5 star
  system will be weaponized instantly (revenge one-stars, syndicate brigading). Reputation should
  come from *facts the game witnessed* (kills, Seals honored, Seals broken, offices held — your
  tags idea does exactly this) rather than opinions players type. Facts can't be brigaded.
  Consider whether reviews add anything the tags system doesn't do better.

---

## 12. Growth, money, and the shareable death

**Growth.** The realistic path to your first 100: launch tight (2 cities, global chat, NPC
contracts, kill loop, drugs, bank, Citadel), recruit 30–50 founders from r/PBBG, Torn-adjacent
communities, and the mafia-family/Omerta nostalgia diaspora (these people are *specifically
findable* and specifically hungry for exactly the game you're building — lead with "permadeath is
back" because that's the phrase that summons them), then let deaths do the marketing. Which they
can, if and only if every death produces a shareable artifact:

- **Kill transcripts** — a beautifully formatted, permalink-able account of an assassination
  (neo-noir styling, both parties' dossier stats, the weapon, the city, the Last Will appended).
  This is a screenshot that carries your entire tone to Discord and Reddit for free.
- **Dossier cards** — the shareable player card. Every proud player posting one is an ad.
- **Last Wills** — published to all on death. Free viral copywriting, written by your players, at
  their moment of highest emotion.

These three (all already in your ideas list — again, promote them from "ideas" to launch-core) are
the growth mechanic the 2005 games never had. They cost little and they're your only realistic
acquisition channel besides word of mouth, because you will not outspend anyone on ads.

**Money.** You didn't ask, but it's a grand design choice so one paragraph: the genre's proven
model is Torn's — subscription/donator status for *convenience and cosmetics* (more concurrent
trainings, cosmetic profile flair, quality-of-life), never for power, and absolutely never for
kill-relevant power. In a permadeath game, pay-to-win isn't just distasteful, it's *lethal to the
premise*: the moment someone believes they died to a credit card, the fear that powers your whole
game curdles into resentment, and the story they tell about your game changes from "I got
assassinated" (glorious, recruiting) to "I got paywalled" (fatal, repelling). Elite coins for
intel searches sits right on this line — watch it carefully; intel-for-cash is kill-relevant power
if coins are purchasable.

---

## 13. What I would cut or defer (launch-state proposal)

**Launch with** (the 40-player game):
- 2 cities, global chat, DMs
- Solo missions + NPC assassination contracts (debut contract as onboarding)
- Kill system + intel economy + Citadel + bank (with "go dark" absence protection)
- Alcohol + Cannabis production only
- Rebirth, kill transcripts, Last Wills, dossier cards
- Syndicates in minimal form (name, chat, roster — the social container, not the war machinery)

**Fast-follow (month 1–3):**
- Seals (the moment kills + transfers exist to trigger on) — launch this loudly, it's your press release
- First Grand Council seating (launch-era rank rules), contracts/bounties
- Meth/Coke, businesses, city 3 as an expansion event

**Defer without guilt:**
- High-Profile 4-player mission (needs population), syndicate war mechanics (needs multiple real
  syndicates), Chairman layer (needs cities with populations worth governing), airplanes beyond
  commercial (a $200M Concorde is a year-3 fantasy), the cards idea (different game, park it).

This isn't cutting scope, it's *phasing* it — and each deferred feature becomes a live-ops event
("The Council is seated." "The Order opens Moscow.") instead of a dusty tab nobody's used since launch.

---

## 14. The honest closing assessment

**What you have:** the correct genre instincts (permadeath, formality of tone, social systems as
content), one genuinely novel system (Seals) with the right architecture behind it, a
better-than-genre-standard answer to permadeath's churn problem (rebirth-with-identity), a kill
loop whose intel dance is real design, and an economy that — perhaps accidentally — self-regulates
through violence. That is more original design than 90% of the PBBGs that get launched.

**What you're missing:** a launch-state design for 40 players (everything is final-state), an
answer to the year-locked governance problem, absence protection, an alt-defense stance, and a
first hour that delivers the fantasy instead of promising it.

**Will it work?** The version in the wiki, launched as written — probably not: chat splits four
ways and dies, the marquee features sit locked for months, a couple of bored veterans permadeath
the population, and it joins mafia-family in the graveyard, having been a good design that was
never allowed to be a good *small* game. The same design, phased as in §13, with global chat, NPC
contracts feeding the killers, deaths producing shareable artifacts, and the Council seated in
week 4 — that game can absolutely hold 100 players, because 100 players is a *community* problem,
not a product problem, and your product gives a community more to talk about than almost anything
in the genre. Whether it goes from 100 to 1,000 depends on the stories the first 100 generate —
which is exactly why the transcript/will/dossier artifacts and the Seals matter more than any
formula in the wiki.

You're not on the wrong path. You're on the right path holding a map of the destination instead of
the first mile. Draw the first mile.

---

*Points I'd most like to argue about next: Council selection mechanism (§6), the "go dark"
mechanic's exact rules (§4), whether reviews survive contact with the tags system (§11), and the
launch-state feature list (§13).*
