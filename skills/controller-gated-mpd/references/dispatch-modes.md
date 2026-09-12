# Dispatch Modes

## native-dispatch
Use only when the runtime can actually create isolated workers. Worker contracts still include frozen base, lane ownership, inherited risk floor, authorization limits, verification, and result envelope.

## prompt-handoff
Use in ordinary ChatGPT conversations without native worker dispatch. Render zero-context worker prompts and one coordinator prompt. State that prompts are ready to open in separate windows; never imply workers started automatically.

Blocked lanes are withheld by default. Previewed blocked prompts must say `DO NOT START` and list unmet prerequisites.
