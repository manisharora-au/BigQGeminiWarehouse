# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Guidelines

### Code Simplicity
- Keep code as simple as possible. Even if it means that we have to refactor a lot of code later. This is because I like to keep the code simple and easy to understand. 

### Code Quality
- Use type hints for all Python functions
- Maintain test coverage above 80%
- Follow PEP 8 style guidelines
- Document all public APIs with docstrings
- documentation above the method explaining the signature, variables, return type, and the purpose of the method

### Data Operations
- All data transformations must be idempotent
- Implement proper error handling and retry mechanisms
- Log all data quality metrics and pipeline status
- Use configuration-driven pipeline definitions

### Testing Strategy
- Unit tests for individual components
- Integration tests for pipeline workflows
- End-to-end tests for critical data flows
- Mock external dependencies in tests

### Security
- Never commit credentials or API keys
- Use environment variables for sensitive configuration
- Implement proper data access controls
- Encrypt sensitive data at rest and in transit

### Tasks
- First think through the problem, read the codebase for relevant files, and write a plan to tasks/todo.md.
- The plan should have a list of todo items that you can check off as you complete them
- Before you begin working, check in with me and I will verify the plan.
- Then, begin working on the todo items, marking them as complete as you go.
- Please every step of the way just give me a high level explanation of what changes you made
- Make every task and code change you do as simple as possible. We want to avoid making any massive or complex changes. Every change should impact as little code as possible. Everything is about simplicity.
- Ensure that there is adequate documentation for the class and any methods / functions introduced to the code base. This documentation should clearly articulate the purpose of the class or the method, function. 