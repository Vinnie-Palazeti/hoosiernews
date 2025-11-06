#* Standard Workflow
1. First think through the problem, read the coadebase for relevant files, and write a plan to projectplan.md
2. The plan should have a list of todo items that you can checkoff as you complete them
3. Before you begin working, check in with me and I will verify the plan
4. Then, begin working on the todo items, marking them complete as you go
5. Please very step of the way give me a high level explanation of what changes you made
6. Make every task and code change you do as simple as possible. We want to avoid making any massive for complex changes. Every change should impact as little code as possible. Everytyghin is about simplicity
7. Finally, add a review section to the projectplan.md file ith a summary of the changes you made and any other relevant information


#* Code Preferences
1. Python Preferences
- Write Functional Programming code. Do not use Object Oriented Programming.
- I want functions that do things.

#* Package Management
2. Use the uv python package manager
- if you need to test the main.py file, run `uv run main.py`

3. FastHTML
- If needed, review the FastHTML llms.txt: https://www.fastht.ml/docs/llms-ctx.txt
- When possible, define attributes close to the div
Good:
```python
Div(cls='flex flex-row')(Span(cls='text-base-content', name='content')('Content Span'), Span(cls='text-success')('Success Span'))
```
Bad:
```python
Div(Span('Content Span', cls='text-base-content', name='content'),Span('Success Span', cls='text-success'),cls='flex flex-row')
```
- Do not use Titled() tags. 
