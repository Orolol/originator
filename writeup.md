

# site / slice

Huggingface / gated model 

There's an open source client (https://github.com/huggingface/huggingface_hub) but the server side is closed, and it's where the logic lies. There's abundant documentation. Those enable multiple approaches and cross checking

At first, I was tempted to choose the whole model hosting slice, but I was struggling to grasp the real workload of cloning something that complex. I brainstormed with Opus about this and It gave me exemple of slices that could fit in a half day of work. (gated models, pull requests and discussions, commit apis, collections). I read the docs of those slices

I chose gated models, because it seems to fit perfectly the requirements (well documented, determinist). We have two sides for this clone, the owner and the requester. It's also interesting because it's a small size authorization system, which can hold a lot of complexity. 

# Cloning approaches


## Spec Driven Development

We use the fact that HF has good documentation on the subject plus the open source client to generate a precise spec of the slice. Then we rely on an agent to implement the spec. In this approach, we consider that the documentation is the source of truth, any real world divergence is a bug. The problem here are the probable missing spec, ambiguities. We would then have to test VS the original and rely heavily on the fact that the spec isn't too far from the production, and that ambiguities are nicely resolved by a quick test. This approach is the most straightforward because it's quite similar to how a developer would work, we can rely a lot on AI to generate the spec and the code. The downside is solving the edge-cases can become a very long whack-a-mole exercise.

## Computer-use behavior extraction

We make a plan that covers most uses of the slice, create accounts of users (at least two), and test how the state changes in the UI and try to reverse engineer how the server works. Here again, we can use the AI the establish the testing plan, and agents with computer use to get the data, and a coding agent to code the clone. We can then play the testing plan on the clone and check that it behave exactly in the same way. In between each of this agent phase, we would proceed to an human review. The documentation can serve here to establish the testing plan. This approach is the best to have strong evidence of fidelity for the workflows we observe. It also has some problems : first it can drift quite a lot in term of time and token cost if while testing some behaviour seems hard to reproduce. Secondly, we can face some limits in computer use, HF can have some restriction that would force a long and tedious manual testing. 

## Bridge into clone 

We can go for a solution using a bridge that we would gradually replace by our clone. We clone the UI first, we use a bridge to connect our UI to the real HF backend. This way we have an UI that we can test precisely and the bridge gives us a backend for validating both the UI and the clone. Then we replace the bridge with our clone backend. We can then test that the clone gives us the same state in the UI. We can rely quite heavily on the AI too, with an agent with a playwright handling UI, and AI to carefully compare outputs of both the bridge and the clone. To be sure that the clone UI is correct, we would have to rely on separate browser observation.
Again, we have a form of black box for internal logic which can make it hard to resolve edgecase. Another downside is that we have to carefully reset the state each time we have a divergence between the bridge and the clone. A major plus side is that the bridge can validate our work at any step, even if HF update its behaviour

I chose the bridge solution, as it seems to me the most robust solution to implement in the given time. We will have a working UI with high fidelity to the real one because it's built with the real API. Testing is also quite straightforward because we can easily compare both outputs. The fact that an open source client exists will help us to create the bridge and the clone.

## Workflow with AI

AI setup : Claude Code w/ Fable, Opus 5.5 and Sonnet 5.5. Subagents to code while writing and iterating on next steps. I didn't use ultracode because of its tendency to overengineer and to ship "too much".

Prompts used by agents are in /harness/agents

After choosing the approach, I created the repository, feeding it with information about this cloning. I asked an agent to gather documentation about the gated model slice in /docs. I reviewed the documentation quickly, and iterated with the agent to make sure the scope of the clone is doable, creating an account and access tokens. 
I asked the agent to manually run some tests to check that everything is reachable via API and with access token. 
I built a walkthrough that will be used as a live conformance scenario. 

After this, two agents worked to implement the UI and the bridge, and another one . I reviewed and tested it VS the real interface, once validated, I ran another agent to create the clone and another in parallel added a conformance test suite, with unit tests and scenarios to be tested. The agent working on conformance couldn't read the clone code, only rules, records.

I added a switch button between bridge and clone, and a reset button. I then spent some time manually using the UI with both the bridge and the clone, and then some time with the real UI, to try to find some anomaly. 

Each affirmation has its tag ([OBS], [OBS-UI], ...) which gives the agent a knowledge of the reliability of an affirmation and ability to revoke them by testing. Each rule has its tag name to be used in the code and tests. Finally a rule prevent agent to invent a rule without an evidence. Each unknown or open question was written in a markdown by agents and we solved them with different setup and live testing. 

Each agent used the same contract (/docs/system.md) with a lot of rules to prevent failure, like a rule to prevent agents from writing on the real hub. 

## Project structure 

Bridge, Clone and Web folders are project folders with the code. Clones and bridges are in python, Web is the NextJS UI.
Conformance contains the test suite, with units tests in /tests and the scripts to run scenarios in / conformance/src
Docs contains the docs, in hf-gated documentation extracted by the agent specifically for this slice.
Harness contains various scripts used by agents and subagents prompts.

## Verification & Gaps

On the clone, everything is in memory only, resetable.

The project has many automated tests, from unit test to e2e scenarios testing. Those formed the first verification pass, ensuring that the bridge and the clone act in the same way. There's 19 sandbox scenarios with 739 step recorded.
The offical client is also used against the clone to ensure compatibilty.
The second verification pass was done by me and an agent by computer use, to check if the UI was correct in both modes. 
Then, with the help of an agent, did the same verification with the original UI. This last step helped me to correct a lot of  gaps. 

There's still some known gaps.

- HF have a little lag when we send a "reset", while our clone is instant
- User search isn't working on the live HF site when we were testing, or in the bridge, but is working on the clone.
- UI don't send the same params as the bridge for requests handle (and the clone)
- The clone is focused on the owner side and there's many gaps on the requester side, like the ability to choose other repos, or the UI to show them. 

Suspected gaps:

- behavior with lot of requests from many differents user
- State of UI with edge case like very long usernames from the requesters

Out of scope : 

- Large Files downloading
- Custom form for requests. This was planned at start but was cut to fit in the timebox. The clone and bridge have the code and test pass, but I didn't have the time to do all verification needed for it.
- EU blocking
- Organizations member bypassing requests
- Emails

## What didn't work

- Claude Code blocked some interactions with Hugging Face, I had to do some clicks myself where I wasn't supposed to.
- Sometimes both documentaiton and client are wrong and doesn't use correctly their own API
- I underestimated the time to verify properly. I should have prepared a verification harness first, with agents, accounts etc.

## What's next

With two full more days, I would focus on filling the gap and suspected gaps with a larger computer-use powered agent. This would have required multiple accounts, emails, and such. 

Then I would have extended the slice in two directions. First, horizontally, by fully including the custom requested information. The requester would have to fill a small form to have access to the model. I think this is a quite interesting feature to include because there is lot of decision that can be done on this. You can give a model a lose set of rules and try to foul it. This was planned initially, but as I finished the verification pass on the current slice, I was short on time to include it. 

Datasets have the same API also, so it would be a low cost addition to this clone. 

The bridge can be enriched with the full API, meaning that this method will be perfect to reproduce everything that is doable via API. The obvious caveat is that is there's some UI only features, you wouldn't be able to clone it without a browser exploration. 

If I had a much more larger target, I would have to split the work in this way, reusing the method (/docs/method.md) : 
The exploration and documentation gathering phase would have to prepare folders for each slice. Slice can't be too close in terms of UI and features to prevent agents from having too many conflicts. For Hugging face, you woul have a slice for the whole model management, another for datasets, etc.
Each slice would have to be vertically sliced into phase when work can't be paralelized. 
Also, you would have to prepare a fleet of accounts ready to be used for agents by computeruse, with a lot of different setup (organization, etc ...).
