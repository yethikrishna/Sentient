# Contributing to Sentient  

We welcome contributions! Please read these guidelines carefully.  

## Code of Conduct  
All contributors must adhere to our [Code of Conduct](CODE_OF_CONDUCT.md).  

## Development Workflow  

### 1. **Branch Strategy**  
We follow a structured branching model to ensure smooth collaboration:  

- **`master`** → Stable, production-ready code.  
- **`development`** → Active development branch (target all PRs here).  
- **`feature/<some-feature>`** → New features are developed in separate branches prefixed with `feature/`.  
- **`bugfix/<some-bug>`** → Bug fixes should be addressed in dedicated `bugfix/` branches.  
- **`research/<some-research>`** → Experimental branches used for exploring ideas. These are sandbox environments that can later be integrated into `feature/` branches and then merged into `development`.  

> 🔹 **Research branches (`research/`) are meant for exploration and testing.** Once a concept is validated, it should be merged into a `feature/` branch before integration into `development`.  

### 2. **Pull Request Process**  
- Fork the repository and create a relevant branch (`feature/`, `bugfix/`, or `research/`).  
- Open PRs **only** to the `development` branch.  
- PRs must include:  
  - A clear description of changes.  
  - Updated documentation (if applicable).  

### 3. **Code Standards**  
- Follow existing code style and architecture patterns.  
- Document new APIs and features thoroughly.  
- Keep commits atomic and well-described.  

### 4. **Testing Requirements**  
- All code must pass existing test suites.  
- New features require ≥80% test coverage.  
- Manual testing steps must be documented in PRs.  

### 5. **CLA Requirement**  
- You **must** sign our [Contributor License Agreement](CLA.md) before merging.  
- Unsigned PRs will be blocked automatically.  

### 6. **Review Process**  
- **2 maintainer approvals** required for merging.  
- **Security-critical code** requires **3 approvals**.  
- Reviewers may request changes or additional tests.  

### 7. **Community Guidelines**  
- **Discussion Forum**: [Link to Discourse/Forum]  
- **Feature Requests**: Use GitHub Discussions.  
- **Critical Bugs**: Use "Security Advisory" template.  

---

**Thank you for contributing to Sentient! 🚀**  