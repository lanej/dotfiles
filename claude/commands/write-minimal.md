---
description: "Write with radical brevity: think about what needs communicating, then find the MOST MINIMAL way to say it. People don't read long documents. ALWAYS edit existing document, NEVER create new files."
argument-hint: [what to write]
model: sonnet
tags:
  - writing
  - documentation
  - brevity
---

# Write Minimal - Radical Brevity for Busy Readers

**CRITICAL ASSUMPTIONS:**
1. People will NOT read your document. They will scan it.
2. You are editing ONE document, not creating new files for every iteration.
3. **It's easier to add than remove** - write ONLY what's requested, nothing more.

Your task: Write about **$ARGUMENTS** using radical brevity.

## The Golden Rule: No Extrapolation

**ONLY write what's explicitly asked for.**

User says: "Write a policy on X"
→ Write the policy. That's it.
→ NO timeline, authority matrix, decision framework, implementation steps, FAQs, or "helpful" extras.

User says: "Add a timeline"
→ NOW add a timeline.

**If the user wants more, they'll ask. Don't anticipate needs.**

## Executive Communication Standards

**Context: VP of Engineering / CTO-level writing.**

### Voice and Tone

**Executive voice is:**
- Decisive and authoritative
- Clear and direct
- Professional without formality
- Action-oriented
- Confident in recommendations

**NOT casual, NOT academic:**
- ❌ Casual: "Hey team, so we should probably..."
- ❌ Academic: "Upon careful consideration of various factors..."
- ✅ Executive: "Adopt Solution A. Here's why."

### Communication Principles

1. **Be decisive**: Make clear recommendations
   - ❌ "We might consider"
   - ✅ "I recommend"

2. **State trade-offs directly**: Don't hide costs
   - ❌ "This has some benefits"
   - ✅ "Costs $50k, saves 200 eng hours/month"

3. **Respect intelligence**: No hand-holding
   - ❌ "As you may know, code review is important because..."
   - ✅ "Code review reduces defects 40%"

4. **Action-oriented**: What to do next
   - ❌ "This is an interesting opportunity"
   - ✅ "Ship by Friday"

5. **No hedging**: Own your position
   - ❌ "It seems like we could potentially..."
   - ✅ "We should do X"

## Document Workflow - ONE FILE ONLY

**NEVER create a new file unless explicitly requested.**

### Starting a Document

**If document doesn't exist:**
1. Ask user for file path once
2. Create document at that path
3. ALL future iterations edit that file

**If document exists:**
1. Read the existing file
2. Edit it with changes
3. Never create a new version/draft

**Anti-Pattern:**
```
❌ Creating: draft-v1.md, draft-v2.md, draft-final.md, draft-final-v2.md
```

**Correct Pattern:**
```
✅ Editing: doc.md (same file, multiple iterations)
```

### Iteration Process

1. **User provides feedback** → Edit existing document
2. **User adds new section** → Edit existing document
3. **User wants to revise** → Edit existing document
4. **User wants shorter** → Edit existing document

**The file path never changes.**

## The Minimal Writing Process

### Step 1: Extract Core Message (30 seconds)

Ask yourself:
- What's the ONE thing the reader must know?
- If they only read the title, what should it say?
- What decision or action does this enable?

**Write this down in one sentence.**

### Step 2: Identify Essential Points (1 minute)

What are the 3-5 points that MUST be communicated **to answer the specific request**?

For each point:
- Was it explicitly requested? (If no, DELETE IT)
- Can I delete it? (If yes, delete it)
- Can I combine it with another point? (If yes, combine)
- Can I show it instead of explain it? (If yes, use code/diagram)

**List only the survivors.**

**Ask yourself: "Did the user ask for this?"**
- If no → Delete it
- If maybe → Delete it (they'll ask if needed)
- If yes → Keep it minimal

### Step 3: Choose Format (30 seconds)

Pick the SHORTEST format that works:

**For simple info:**
- Single sentence → Use it as-is
- 2-3 points → Bullet list
- Comparison → Table
- Process → Numbered steps
- Code example → Just show the code

**For complex info:**
- Still use above formats
- Just add minimal context
- Break into sections with clear headers

### Step 4: Write Minimally (5 minutes)

**Rules:**
1. **One idea per sentence**: Maximum 15 words
2. **One sentence per point**: No elaboration unless critical
3. **Delete ruthlessly**:
   - Introductions (just start)
   - Transitions ("furthermore", "additionally")
   - Explanations of obvious things
   - Examples unless essential
   - Summaries (they already read it)
   - Conclusions (end when done)

4. **Use these patterns:**
   ```
   # Title (what this is)

   [Why this matters in one sentence]

   ## Section 1
   - Point
   - Point
   - Point

   ## Section 2
   - Point
   - Point

   [What to do next]
   ```

### Step 5: Cut in Half (2 minutes)

**After writing, cut 50% of the words:**

1. **Delete anything not explicitly requested**
2. Delete first paragraph (usually warm-up text)
3. Delete last paragraph (usually summary)
4. Cut each sentence to < 15 words
5. Replace paragraphs with bullets
6. Delete every adjective and adverb
7. Remove entire sections user didn't ask for
8. Remove phrases:
   - "It is important to note"
   - "As mentioned previously"
   - "In order to"
   - "One of the key benefits"
   - "Going forward"

**Common extrapolations to DELETE:**
- Timelines (unless requested)
- Implementation plans (unless requested)
- Risk analysis (unless requested)
- Authority matrices (unless requested)
- Budget estimates (unless requested)
- Team structures (unless requested)
- FAQs (unless requested)

**If you can't cut 50%, you didn't try hard enough.**

## Format Templates

### Template 1: Announcement/Update

```markdown
# [What changed]

[Why it matters - one sentence]

## What's different
- Point
- Point
- Point

## What to do
[Action in 1-2 sentences]
```

### Template 2: Proposal/Decision

```markdown
# Recommend: [Solution]

Why: [Benefit in < 10 words]

Trade-off: [Cost vs value in one sentence]

## Next steps
1. Action
2. Action
```

### Template 3: Technical Doc

```markdown
# [Feature name]

[What it does - one sentence]

## Quick start
bash
command here


## Common uses
- Use case → solution
- Use case → solution

## Need help?
[Link or contact]
```

### Template 4: Meeting Notes

```markdown
# [Meeting topic] - [Date]

## Decisions
- Decision
- Decision

## Actions
- [ ] Task (owner, due)
- [ ] Task (owner, due)

## Open questions
- Question
```

### Template 5: Email

```markdown
Subject: [The ask or update]

[Why this matters - one sentence]

[Details if needed - 2-3 bullets max]

Next: [What you need from them]
```

## Anti-Patterns - Delete Immediately

**Opening paragraphs like:**
```
I wanted to reach out to provide you with an update
regarding the recent developments in...
```
→ **Delete. Start with the update.**

**Transitional phrases:**
```
Furthermore, it's important to note that additionally...
```
→ **Delete. Just say the next thing.**

**Summaries:**
```
In summary, as we discussed above, the key points are...
```
→ **Delete. They just read it.**

**Hedging:**
```
It might be worth considering that we could potentially...
```
→ **Delete. Be direct: "We should..."**

## Brevity Checklist

Before sending ANY document, verify:

- [ ] Title states what this is (< 8 words)
- [ ] First sentence = why it matters
- [ ] Total doc < 200 words (exception: API reference)
- [ ] No paragraph > 3 lines
- [ ] No sentence > 15 words
- [ ] Used bullets instead of paragraphs
- [ ] Deleted intro/conclusion/summary
- [ ] Removed all hedging phrases
- [ ] Cut at least 50% from first draft
- [ ] Can scan in 30 seconds

**If you fail any check: rewrite shorter.**

## The 30-Second Test

Read your document aloud. Time it.

**If it takes > 30 seconds to read:**
- Too long for email/update/note
- Needs to be cut by 50%

**If it takes > 2 minutes to read:**
- Too long for proposal/decision doc
- Break into sections or multiple docs

**If it takes > 5 minutes to read:**
- Too long. Period.
- Ask: Does this need to exist?

## The Extrapolation Problem

**User asks for ONE thing. You write FIVE things.**

### Example: "Write a policy on code review"

**❌ What NOT to do (extrapolation):**
```markdown
# Code Review Policy

## Overview
Code reviews ensure quality and knowledge sharing...

## The Policy
All PRs require review before merge.

## Implementation Timeline
- Week 1: Training
- Week 2: Pilot program
- Week 3: Full rollout

## Authority Matrix
- Junior devs: 1 approver required
- Senior devs: 1 approver required
- Staff+: Can self-approve urgent fixes

## Decision Framework
When to require extra reviewers...

## Common Scenarios
Q: What if reviewer is on vacation?
A: Escalate to team lead...
```

**✅ What to do (requested only):**
```markdown
# Code Review Policy

All PRs require one approval before merge.
```

**If user wants more:**
- "Add timeline" → Add timeline section
- "Who can approve?" → Add authority info
- "What about urgent fixes?" → Add exception

**Start minimal. Let them ask.**

## Executive Voice Examples

### Example 1: Technical Decision

**❌ Wishy-washy:**
"I wanted to discuss the possibility of potentially migrating to a microservices architecture. There are several factors to consider, and it might be beneficial if we could evaluate the trade-offs."

**✅ Executive:**
"Migrate to microservices. Team velocity increases 30%. Cost: 6 months migration, $200k infra increase."

### Example 2: Policy Recommendation

**❌ Academic:**
"Upon careful analysis of various code review methodologies and their impact on software quality metrics, it has become apparent that implementing a structured review process could potentially yield improvements in defect detection rates."

**✅ Executive:**
"Require code review on all PRs. Defects drop 40%. Cost: 2 hours per engineer weekly."

### Example 3: Status Update

**❌ Casual:**
"Hey everyone, just wanted to give you guys a quick update on how things are going with the auth system. We've been making some good progress and things are looking pretty good so far."

**✅ Executive:**
"Auth system ready for QA. OAuth2 live in staging. Test by Friday."

### Example 4: Problem Escalation

**❌ Hedging:**
"I think we might be experiencing some challenges with the current deployment process that could potentially impact our ability to release on schedule."

**✅ Executive:**
"Deployment broken. Blocks Friday release. Need DevOps support today."

## Examples: Before & After

### Example 1: Status Update

**❌ Before (143 words):**
```
Hello team,

I wanted to take a moment to provide you with an important
update regarding the progress we've made on the authentication
system refactoring project. Over the past two weeks, our team
has been working diligently to implement the new OAuth2 flow
that we discussed in our previous planning meetings.

I'm pleased to report that we have successfully completed the
initial implementation phase and the new system is now ready
for testing. The key benefits of this new approach include
improved security, better user experience, and easier
integration with third-party services.

Moving forward, we would appreciate it if the QA team could
begin testing the new authentication flow at their earliest
convenience. Please let me know if you have any questions or
concerns.

Thank you for your continued support.
```

**✅ After (28 words):**
```
# Auth system ready for testing

New OAuth2 flow is live in staging.

Benefits: Better security + easier 3rd party integration.

Next: QA team test this week.
```

### Example 2: Technical Decision

**❌ Before (187 words):**
```
After extensive analysis and careful consideration of the
various database options available to us, we have determined
that PostgreSQL would be the most suitable choice for our
needs going forward. This decision was reached after
evaluating multiple factors including performance
characteristics, scalability requirements, and operational
complexity.

PostgreSQL offers several advantages that align well with
our requirements. First and foremost, it provides excellent
performance for our workload patterns. Additionally, it has
strong community support and extensive documentation, which
will facilitate easier onboarding of new team members.
Furthermore, it includes built-in support for JSON data
types, which we anticipate will be beneficial for our use
cases.

While there are some trade-offs to consider, such as the
need for additional operational expertise and slightly higher
infrastructure costs compared to some alternatives, we believe
the benefits outweigh these concerns. We recommend proceeding
with PostgreSQL implementation.
```

**✅ After (31 words):**
```
# Recommend: PostgreSQL

Why: Handles our workload + JSON support built-in.

Trade-off: +$200/mo hosting, need DB expertise.

Strong community = easier hiring.

Next: Prototype this week.
```

### Example 3: Meeting Notes

**❌ Before (156 words):**
```
Meeting Notes - Product Roadmap Discussion
Date: January 15, 2026
Attendees: Sarah, Mike, Jennifer, Tom

We convened today to discuss the upcoming product roadmap
for Q1 2026. The discussion was productive and we were able
to reach consensus on several important matters.

Key Discussion Points:
Sarah presented the user research findings which indicated
that customers are requesting better mobile support. Mike
raised concerns about the engineering timeline for
implementing these features. Jennifer suggested we could
potentially address this by prioritizing the most critical
mobile features first.

After thorough discussion, we agreed to move forward with
a phased approach to mobile development. Tom will lead the
effort and provide weekly updates. We also decided to
postpone the analytics dashboard work until Q2.

Action items:
- Tom to create mobile development plan by Jan 22
- Sarah to share research deck with team
- Next meeting scheduled for Jan 29
```

**✅ After (47 words):**
```
# Roadmap Q1 - Jan 15

## Decisions
- Mobile: phased approach, Tom leads
- Analytics dashboard: postponed to Q2

## Actions
- [ ] Tom: mobile plan (Jan 22)
- [ ] Sarah: share research deck

Next meeting: Jan 29
```

## When to Break the Rules

**Okay to be longer for:**
- API reference documentation (but still be concise per item)
- Legal/compliance requirements (but still cut fluff)
- Tutorial with code examples (but minimize prose)

**Never okay to be longer for:**
- Emails
- Slack messages
- Meeting notes
- Status updates
- Proposals
- READMEs

## Usage

```bash
# Start a new minimal document (asks for file path once)
/write-minimal "proposal for new feature"

# Continue editing the same document (no new files)
/write-minimal "add section about timeline"
/write-minimal "make it 50% shorter"
/write-minimal "revise the introduction"
```

**All iterations edit the SAME file. Never create new versions.**

## Integration

This command uses the **human-writer agent** for:
- Enforcing brevity principles
- Avoiding AI patterns
- Ensuring human-readable output
- Checking for duplication
- **Editing ONE document** (never creating new files)

The agent will:
1. Help you identify core message
2. Cut your draft by 50%
3. Ensure it passes the 30-second test
4. Flag any AI tell phrases
5. Verify zero duplication
6. **Edit existing document** instead of creating new versions

## File Management Rules

**CRITICAL - Read this:**

1. **First iteration**: Ask for file path, create document
2. **All subsequent iterations**: Edit that same file
3. **NEVER create**:
   - draft-v1.md, draft-v2.md
   - doc-revised.md
   - doc-final.md
   - doc-final-ACTUALLY-final.md

4. **ALWAYS use Edit tool** on existing document
5. **User wants changes** → Edit the file
6. **User wants new section** → Edit the file
7. **User wants shorter** → Edit the file
8. **User wants different approach** → Edit the file

**The document is iterative. The file path is permanent.**

## Remember

**People don't read. They scan.**

Your job: Make it scannable.

- Brutal brevity
- Clear structure
- No fluff
- Action-oriented

If they have to work to understand you, you failed.

Make it effortless.
