

    Originator

Assignment
Replication Engineer, Take-Home Assignment

Time box: you have 3 to 4 days from when we send this, so you can fit it around your schedule. Please spend no more than one day of actual effort on it in total. We expect the coding itself to take only a few hours; the rest is method and write-up.

Stack: your choice, though TypeScript is what we use day to day.

Outcome: a strong submission earns you a session with the team.


What this exercise is really testing

The job at Originator isn't "build an app." It's dropping into an unfamiliar piece of software, working out how it actually behaves, and reproducing that behaviour faithfully and fast, leaning hard on LLM agents to get there. This take-home is a small-scale version of that loop.

We are not grading you on how polished the running clone looks. We're grading you on how you think about replication, how you drive AI to do it, and how you prove the result is correct. A candidate who ships a tiny but rigorously verified slice with a clear method will beat one who ships something big, pretty, and unverified.


The task

Pick a real piece of a software (closed source only) and replicate one meaningful slice of its business logic. Not the whole product, and not just its frontend. Then write up how you did it.

Concretely:

    Choose a target and a slice. Find the part of the product where the value and the logic actually live: the pricing engine, the scheduling rules, the balance calculation, the state machine. Not the login page or the CSS. In a paragraph, tell us what the core value of this software is and why this slice is the right thing to clone first.

    Propose a few cloning approaches. Before you write much code, lay out 2 to 4 genuinely different strategies for replicating this slice accurately and efficiently, with the trade-offs of each: fidelity, speed, robustness, how much you can lean on AI, how you'd verify it. Approaches can differ on things like black-box behavioural reproduction versus reverse-engineering the data model, scraping or recording real usage versus inferring the rules from docs, hand-writing the core versus generating it from an LLM knowledge base, or an API bridge versus a full reimplementation.

    Implement one of them. Implement one of them. Build a resettable, deterministic clone of the slice: the business logic behind a thin API, plus the screens a user goes through to exercise that logic. It has to be seedable and resettable to a known state (a process restart or a reset call brings it back), so that in principle it could be trained against over and over.
    For the UI, faithful means behaviour, not pixels: same layout and controls, same state transitions (what appears, what gets disabled, what the user sees after each action), and the same side effects (requests fired, exports produced, confirmations and error messages shown), including the awkward ones. A good test is that the same scripted walkthrough drives both the original and your clone. Do not spend time on visual polish: copy the structure and the behaviour, ignore fonts, colours and responsiveness unless they carry logic.
    Keep the surface small. One workflow end to end, exposed through a couple of endpoints and the screens that call them, is plenty.

    Verify it. Write a small test suite that pins down the behaviour you're claiming, across the normal cases and the edge cases you think matter. Your target is free to access, so use it as your reference, for instance: run a handful of carts through an open-source reference like Medusa or Saleor and confirm your clone agrees, especially where multiple discounts interact. Then tell us plainly where you're confident it's faithful and where you know, or suspect, it diverges. We care more about an honest, specific account of the gaps than about zero gaps.

    Show your AI leverage. This part matters a lot. Include the agents, prompts, knowledge base, scaffolds, and tooling you used to move quickly. We want to see how you got an LLM to produce correct, verifiable code rather than code that merely looks plausible. Bonus points if your scaffolding would let you clone a second feature faster than the first..


Deliverables

The write-up and the agent artifacts are the main deliverable. The running code is the evidence, not the prize.

    A short write-up, roughly 2 to 3 pages, markdown is fine, covering:

        the target, the slice, and your reasoning for the choice

        your 2 to 4 candidate approaches with trade-offs, and why you picked the one you built

        how you used AI: which agents and tools, how you structured the work, what worked and what didn't

        your verification story: what you tested, what passed, and the gaps you know about or suspect

        what you'd do next with two more days, and how you'd scale this method to a much larger target

    A repository with the implemented slice, runnable from a README in one or two commands, resettable to a clean state.

    Your AI scaffolding, checked in: prompts, agent definitions, knowledge-base files, recorded workflows, generation and verification scripts, whatever you actually used.


Constraints and guidance

    Keep to the time box. We mean the one day of effort, not the calendar window. If you find yourself polishing a frontend, you've misread the exercise. Spend the time on method, correctness, and verification instead.

    In-memory persistence only. The backend has to keep its state in memory. No external database, no disk-backed store. This keeps the environment trivially resettable and deterministic: a process restart, or a reset call, brings it back to a known clean state. Seeding fixtures at startup is fine. Reaching for Postgres is not.

    AI leverage is expected, not optional. Using LLM agents heavily is the whole point of the role, and so is knowing how to structure their work. Do not just prompt your way through: build a small cloning harness and let it do the cloning. By harness we mean the agent definitions, skills or prompts, knowledge-base notes, recorded fixtures and verification scripts that take a target from "unknown" to "verified clone", organised so that a second slice of the same product, or a different product, would be faster than the first. It can be thin. What we look at is whether the harness encodes what you know about replication rather than what you know about this one target.

    Pick a slice with real logic. Frontend-only clones, static pages, and CRUD with no rules are out of scope. We're after branching, calculation, ordering, or state.

    Faithful beats feature-complete. A small slice that closely matches the original, weird edge cases included, is worth far more than a broad slice that's roughly right.

    Be honest about the gaps. We trust candidates who can tell us precisely where their clone is wrong. Overclaiming fidelity is the quickest way to fail this.


Submission

Send us a link to the repository (or a zip) with the write-up and your AI scaffolding included. A short Loom-style walkthrough is welcome but optional. If anything about the scope is unclear, make a reasonable assumption, note it in the write-up, and move on. That judgment is part of what we're looking at.



Submission
Files
Upload File(s)

or drag and drop here
Notes


Submit Assignment
Powered by 

Privacy PolicySecurityVulnerability Disclosure
