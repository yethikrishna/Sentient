**Contributing to Sentient**
============================

We welcome contributions! Please read these guidelines carefully.

**Code of Conduct**
-------------------

All contributors must adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).

**Development Workflow**
------------------------

### **1\. Branch Strategy**

We follow a structured branching model to ensure smooth collaboration:

*   **`master`** → Stable, production-ready code.
*   **`development`** → Active development branch (target all PRs here).
*   **`feature/<some-feature>`** → New features are developed in separate branches prefixed with `feature/`.
*   **`bugfix/<some-bug>`** → Bug fixes should be addressed in dedicated `bugfix/` branches.
*   **`research/<some-research>`** → Experimental branches used for exploring ideas. These are sandbox environments that can later be integrated into `feature/` branches and then merged into `development`.

> 🔹 **Research branches (`research/`) are meant for exploration and testing.** Once a concept is validated, it should be merged into a `feature/` branch before integration into `development`.

### **2\. Pull Request Process**

*   Fork the repository and create a relevant branch (`feature/`, `bugfix/`, or `research/`).
*   Open PRs **only** to the `development` branch.
*   PRs must include:
    *   A clear description of changes.
    *   Updated documentation (if applicable).

### **3\. Code Standards**

*   Follow existing code style and architecture patterns.
*   Document new APIs and features thoroughly.
*   Keep commits atomic and well-described.

### **4\. Testing Requirements**

*   All code must pass existing test suites.
*   New features require ≥80% test coverage.
*   Manual testing steps must be documented in PRs.

### **5\. Commit Message Format (Conventional Commits)**

To maintain a clean and meaningful commit history, follow the **Conventional Commits** format:

```
<type>(<scope>): <description>
```

#### **Examples**:

✅ **Feature Addition:**

```
feat(auth): add OAuth2 login support
```

✅ **Bug Fix:**

```
fix(ui): resolve button alignment issue in navbar
```

✅ **Documentation Update:**

```
docs(contributing): clarify PR submission process
```

✅ **Refactor:**

```
refactor(api): optimize query handling for performance
```

✅ **Chore (dependencies, CI/CD, etc.):**

```
chore(deps): update dependency eslint to v8.3.1
```

#### **Valid Types:**

Type

Description

`feat`

Introduces a new feature

`fix`

Fixes a bug

`docs`

Documentation updates

`style`

Code style (formatting, missing semicolons, etc.)

`refactor`

Code refactoring (no new features or bug fixes)

`test`

Adding or updating tests

`chore`

Maintenance tasks (dependencies, CI/CD, etc.)

> **🔹 Note:** All PR titles must follow the **Conventional Commits** format. PRs with invalid commit messages may be rejected.

### **6\. CLA Requirement**

*   When a pull request is raised, the CLA Assistant bot will guide you with the steps required to sign our CLA, you have to simply follow them
*   Along with the steps of the bot, you have to sign with your name in [CLA.md](./CLA.md) at the bottom in your own fork of the repository
*   Unsigned PRs will be blocked automatically.

### **7\. Review Process**

*   **2 maintainer approvals** required for merging.
*   **Security-critical code** requires **3 approvals**.
*   Reviewers may request changes or additional tests.

### **8\. Community Guidelines**

*   **Early Adopter Community**: [Join Here](https://chat.whatsapp.com/IOHxuf2W8cKEuyZrMo8DOJ)
*   **Feature Requests**: Use GitHub Discussions.
*   **Critical Bugs**: Use the "Security Advisory" template.

* * *

**Thank you for contributing to Sentient! 🚀**