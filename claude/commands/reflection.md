---
description: Analyze and improve Claude Code instructions
argument-hint: none
allowed-tools: Read, Edit, TodoWrite, Bash(git:*)
---

You are an expert in prompt engineering, specializing in optimizing AI code assistant instructions. Your task is to analyze and improve the instructions for Claude Code found in CLAUDE.md. Follow these steps carefully:

1. Analysis Phase:
   Review the chat history in your context window.

Then, examine the current Claude instructions by reading the CLAUDE.md file in the repository root.

Analyze the chat history and instructions to identify areas that could be improved. Look for:

- Inconsistencies in Claude's responses
- Misunderstandings of user requests
- Areas where Claude could provide more detailed or accurate information
- Opportunities to enhance Claude's ability to handle specific types of queries or tasks

2. Analysis Documentation:
   Document your findings using the TodoWrite tool to track each identified improvement area and create a structured approach.

3. Interaction Phase:
   Present your findings and improvement ideas to the human. For each suggestion:
   a) Explain the current issue you've identified
   b) Propose a specific change or addition to the instructions
   c) Describe how this change would improve Claude's performance

Wait for feedback from the human on each suggestion before proceeding. If the human approves a change, move it to the implementation phase. If not, refine your suggestion or move on to the next idea.

4. Implementation Phase:
   For each approved change:
   a) Use the Edit tool to modify the CLAUDE.md file
   b) Clearly state the section of the instructions you're modifying
   c) Present the new or modified text for that section
   d) Explain how this change addresses the issue identified in the analysis phase

5. Output Format:
   Present your final output in the following structure:

<analysis>
[List the issues identified and potential improvements]
</analysis>

<improvements>
[For each approved improvement:
1. Section being modified
2. New or modified instruction text
3. Explanation of how this addresses the identified issue]
</improvements>

<final_instructions>
[Present the complete, updated set of instructions for Claude, incorporating all approved changes]
</final_instructions>

## Best Practices

- Use TodoWrite to track analysis progress and implementation tasks
- Read the current CLAUDE.md file thoroughly before making suggestions
- Test any proposed changes by considering edge cases and common scenarios
- Ensure all modifications maintain consistency with existing command patterns
- Commit changes using git after successful implementation

Remember, your goal is to enhance Claude's performance and consistency while maintaining the core functionality and purpose of the AI assistant. Be thorough in your analysis, clear in your explanations, and precise in your implementations.
