

# site / slice

Huggingface / gated model 

It's a site that I know quite well and where I've alread some models hosted. There's a opensource client (https://github.com/huggingface/huggingface_hub) bien the server side is closed, and it's where the logic lies. There's an abondant documentation. Those enable multiple approaches and cross chercking

At first, I was tempted to chose the whole model hosting slice, but I was struggling to grasp the real workload of cloning perfectly something that complex. I brainstormed with Opus about this and It gave me exemple of slices that could fit in a half day of work. (gated models, pull requests and discussions, commit apis, collections). I read the docs of those slices

I chose gated models, because it seems to fit perfectly the requirements (well documented, determinist). We have two sides for this clone, the owner and the requester. The requester doesn't have any internal logic here.

# Cloning approaches


## Spec Driven Devlopment

We use the fact that HF have a good documentation on the subject plus the opensource client to generate a precise spec of the slice. Then we rely on a agent to implet the spec. In this approach, we condiser that the documentation is the source of truth, any real world divergence is a bug. The problem here are the probable missing spec, ambiguities. We would then have to test VS the original and rely heavily on the fact that the spec isn't too far from the production, and that ambiguities are nicely resolved by a quick test. This approcach is the most straigth forward because it's quite similar to how a developer would work, we can rely a lot on AI to generate the spec and the code. The downside is solving the edge-cases can become a very long whack-a-mole exercise.

## Computer-use behavior extraction

We make a plan that cover most uses of the slice, create accounts of user (atleast two), and test how the state change in the UI and try to reverse engineer how the server works. Here again, we can use the AI the establih the testing plan, and agents with computer use to get the data, and a coding agent to code the clone. We can then play the testing plan on the clone and check that it behave exactly in the same way. In between each of this agent phase, we would proceed to an human review. The documentation can serve here to establish the testing plan. This approach is the best to have strong evidence of fidelity for the workflows we observe. It also has some problems : first it can drift quite a lot in term of time and token cost if while testing some behaviour seems hard to reproduce. Secondly, we can face some limits in computer use, HF can have some restriction that would force a long and tedious manual testing. 

## Bridge into clone 

We can go for a solution using a bridge that we would gradually replace by our clone. We clone the UI first, we use a bridge to connect our UI to the real HF backend. This way we have an UI that we can test precisely. It should behave exactly like the HF one, because it's connected to the real API. Then we replace the bridge by our clone backend. We can then test that the clone give us the same state in the UI. We can rely quite heavily on the AI too, with an agent with playwright handling UI, and AI to carefully compare outputs of both the bridge and the clone. 
Again, we have a form of black box for internal logic which can make it hard to resolve edgecase. Another downside is that we have to carefully reset the state each time we have a divergence between the bridge and the clone. A major plus side is that the bridge can validate our work at any step, even if HF update its behaviour

I chose the bridge solution, as it seems to me the most robust solution to implement in the given time. We will have a working UI with high fidelity to the real one because it's built with the real API. Testing is also quite straight forward because we can easily compare both outputs. The fact that an opensource client exist will help us to create the bridge and the clone.
