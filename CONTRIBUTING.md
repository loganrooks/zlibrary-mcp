# Contributing to Z-Library MCP

We welcome contributions to the Z-Library MCP project! To ensure a smooth and collaborative development process, please adhere to the following guidelines.

## Version Control Strategy

This project follows a Gitflow-inspired branching model and specific commit conventions.

### Branching Model

Our branching model is designed to maintain stability in `master` while allowing for parallel feature development and integration.

*   **`master`**: This branch represents the most stable, production-ready version of the codebase. All deployments and releases are made from `master`. Direct commits to `master` are prohibited; changes are merged from the `development` branch.
*   **`development`**: This is the main integration branch for new features and fixes. All feature branches are created from `development`, and Pull Requests are merged back into `development` after review. This branch should always be in a state that could be deployed to a staging environment.
*   **Feature Branches**:
    *   Format: `feature/<task-name>` (e.g., `feature/get-metadata-tool`) or `fix/<issue-id>` (e.g., `fix/login-bug-123`).
    *   These branches are created from the `development` branch for individual features, enhancements, or bug fixes.
    *   Once development on a feature branch is complete and tested, it is merged back into `development` via a Pull Request.

**Workflow:**

1.  Ensure your `development` branch is up-to-date: `git checkout development && git pull origin development`.
2.  Create a new feature branch from `development`: `git checkout -b feature/your-feature-name`.
3.  Develop your feature on this branch, making regular, atomic commits (see Commit Message Conventions below).
4.  Once the feature is complete and locally tested, push your feature branch to the remote repository: `git push origin feature/your-feature-name`.
5.  Create a Pull Request (PR) from your feature branch to the `development` branch.
6.  After the PR is reviewed and approved, it will be merged into `development`.
7.  Periodically, the `development` branch will be merged into `master` for releases.

### Commit Message Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/) to ensure commit messages are descriptive and follow a standard format. This helps with automated changelog generation and makes the project history easier to understand.

**Format:**

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Common Types:**

*   `feat`: A new feature for the user.
*   `fix`: A bug fix for the user.
*   `docs`: Changes to documentation only.
*   `style`: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc).
*   `refactor`: A code change that neither fixes a bug nor adds a feature.
*   `perf`: A code change that improves performance.
*   `test`: Adding missing tests or correcting existing tests.
*   `chore`: Changes to the build process or auxiliary tools and libraries such as documentation generation. Includes Memory Bank updates.

**Examples:**

*   `feat: Implement get_metadata MCP tool`
*   `fix: Correct parsing error in download history`
*   `docs: Add version control strategy to CONTRIBUTING.md`
*   `chore(memory): Update activeContext with get_metadata completion`
*   `test: Add unit tests for metadata scraping logic`

### Memory Bank & Commits

Memory Bank updates are crucial for maintaining project context. We follow **Option A: Separate Commits** for Memory Bank updates:

1.  Commit your primary code changes (feature, fix, etc.) first.
2.  Immediately after, make a separate commit for the related Memory Bank updates. This commit should use the `chore` type with a `memory` scope.
    *   Example: `chore(memory): Log completion of get_metadata tool and TDD cycle`
    *   The body of this commit can reference the hash of the preceding code commit if helpful.

This approach keeps code changes and context logging distinct, improving clarity in the commit history.

### Pull Requests (PRs)

*   All feature branches must be merged into `development` via Pull Requests.
*   All merges from `development` into `master` must also be done via Pull Requests.
*   **Review:** PRs should be reviewed before merging. For solo developers or initial stages, self-review is encouraged to establish good practice. The review should check for:
    *   Adherence to coding standards.
    *   Completeness of the feature/fix.
    *   Adequate test coverage.
    *   Clear and conventional commit messages.
    *   Correct Memory Bank updates in a separate commit.
    *   No direct commits of secrets or sensitive data.

By following these guidelines, we can maintain a clean, understandable, and robust version control history.