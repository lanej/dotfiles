---
name: org-announce
description: Draft org-level or company-wide announcements (reporting changes, promotions, departures, strategy, business decisions). Produces email and Slack formats in one invocation. Enforces Josh Lane's register: terse, declarative, no sentiment, no signature, no sycophantic close. Use when asked to draft an announcement, org update, or leadership communication.
---

## When to use

Use this skill for two announcement categories:

**People changes** — org restructures, reporting line changes, promotions, departures, role changes

**Strategic/business** — strategy direction, high-level business decisions, business actions affecting the org

Not in scope: incident comms, product launches/deprecations, external or customer-facing communications.

## Voice rules (apply unconditionally to all output)

NEVER use:
- "Thanks for your support as we make this transition."
- "I'm excited / pleased to announce..."
- "We look forward to..."
- "I'm proud of the team..."
- Any closing line expressing gratitude, optimism, or encouragement
- A signature or sign-off on either channel
- A colon after standalone interjections — write "fwiw" not "fwiw:", "fyi" not "fyi:", "btw" not "btw:"

ALWAYS:
- Open with a declarative statement of what is changing — no wind-up
- State rationale as structural ("this creates tighter feedback loops") not motivational ("this will help us grow together")
- Call out timing explicitly: "Effective [date]" or "Effective immediately"
- Bold names and titles in bulleted lists: **Name**, **Title**
- Bold key phrases and facts throughout the body: outcomes in the goal line, scope descriptors, concrete impacts. E.g., "The goal is **tighter feedback loops, clearer ownership, and faster execution**."
- End the body when the information is complete — no closing sentence

## Skeleton: People changes

```
Subject: [Category] — [Descriptor]

[One sentence: what kind of change and its scope]

Effective [date/immediately][, context if needed]:

- **[Name]**, [title], [reporting/role change — concise]
- **[Name]**, [title], [reporting/role change — concise]

[1–2 sentences: structural rationale — this IS the goal statement. State what the change enables structurally. E.g., "This structure brings X and Y into closer alignment, allowing us to more directly Z."]

[Optional second list with its own header if additional changes are distinct in nature]
```

## Skeleton: Strategic/business

```
Subject: [Brief descriptor of decision or direction]

[One sentence: what was decided or what direction is being taken]

[2–3 sentences: brief context — what prompted it, what it changes. Structural, not motivational.]

[What this means concretely for the org — no aspirational language]
```

## Output format

Always produce both formats in a single response:

```
## Email

Subject: ...

[Body]

---

## Slack

[Body — identical to email body, no subject line, no sign-off]
```

## Worked example (people change)

**Input facts:**
- Engineering, Product, and Customer-facing teams consolidating under one org
- Jonathan Bowen promoted to VP, Client Services & Operations, reporting to Josh; leads post-sales (CS, Support, PS, Integrations) and Lehi office ops
- Dave Vantress, VP Data Analytics & Operations, now reports to Josh
- John Campo, VP Carrier Relations, now reports to Jarrett
- Lynden Whitaker, Manager Sales Engineering, now reports to Ron Justin, VP Sales

**Output:**

---

## Email

Subject: Organizational Update — Aligning Product, Engineering, and Customer Teams

We are making an organizational change to better connect how we build with how we serve customers.

Effective immediately, Engineering, Product, and Customer-facing teams will operate under a single organization.

As part of this:

- **Jonathan Bowen**, **Vice President, Client Services & Operations**, reporting to me, will lead all post-sales functions (Customer Success, Support, Professional Services, and Integrations) and oversee day-to-day operations of the Lehi office.
- **Dave Vantress**, **Vice President, Data Analytics & Operations**, will also report to me.

This structure brings product development and customer experience into closer alignment, allowing us to more directly translate customer signals into product decisions and improvements.

Additional updates:

- **John Campo**, **Vice President, Carrier Relations**, will now report to Jarrett.
- **Lynden Whitaker**, **Manager, Sales Engineering**, will report to **Ron Justin**, **Vice President, Sales**.

---

## Slack

We are making an organizational change to better connect how we build with how we serve customers.

Effective immediately, Engineering, Product, and Customer-facing teams will operate under a single organization.

As part of this:

- **Jonathan Bowen**, **Vice President, Client Services & Operations**, reporting to me, will lead all post-sales functions (Customer Success, Support, Professional Services, and Integrations) and oversee day-to-day operations of the Lehi office.
- **Dave Vantress**, **Vice President, Data Analytics & Operations**, will also report to me.

This structure brings product development and customer experience into closer alignment, allowing us to more directly translate customer signals into product decisions and improvements.

Additional updates:

- **John Campo**, **Vice President, Carrier Relations**, will now report to Jarrett.
- **Lynden Whitaker**, **Manager, Sales Engineering**, will report to **Ron Justin**, **Vice President, Sales**.
