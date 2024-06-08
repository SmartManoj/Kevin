## Introduction

This folder contains unit tests that could be run locally.

Run all test:

```bash
poetry run pytest ./tests/unit
```

Run specific test file:

```bash
poetry run pytest ./tests/unit/test_micro_agents.py
```

Run specific unit test

```bash
poetry run pytest ./tests/unit/test_micro_agents.py:test_coder_agent_with_summary
```

More details see [pytest doc](https://docs.pytest.org/en/latest/contents.html)

## Writing Tests for New Agent Behaviors

When adding new behaviors or functionalities to agents, it's crucial to write corresponding unit tests to ensure the changes work as expected and to prevent future changes from breaking these new behaviors. This is especially important for testing command prioritization logic in agents like `CodeActAgent`, where the order of commands can significantly impact the agent's actions.

### Guidelines for Writing Tests

- **Test Command Prioritization:** For agents that execute commands based on their appearance in the action string, write tests to verify that the first command is executed and subsequent commands are ignored. This ensures the agent behaves predictably in scenarios where multiple commands are present.
- **Use Mocks Sparingly:** While mocking external dependencies can be useful, try to write tests that exercise the agent's logic as thoroughly as possible without relying too heavily on mocks. This helps ensure the tests are realistic and meaningful.
- **Cover Edge Cases:** Consider edge cases in the agent's behavior and write tests to cover these scenarios. This helps catch potential bugs and ensures the agent behaves correctly under various conditions.
- **Document Test Intent:** Clearly document what each test is verifying and why it's important. This helps other contributors understand the purpose of the tests and how they relate to the agent's expected behavior.

By following these guidelines and writing comprehensive tests for new agent behaviors, we can maintain a high level of quality and reliability in the OpenDevin project.
