![Stars](https://img.shields.io/github/stars/fabifont/jobpilot?style=social)

![Pre-commit checks](https://github.com/fabifont/jobpilot/actions/workflows/pre-commit.yaml/badge.svg)

![Open issues](https://img.shields.io/github/issues/fabifont/jobpilot?color=9cf) ![Open pull requests](https://img.shields.io/github/issues-pr/fabifont/jobpilot?color=9cf)

![License](https://img.shields.io/github/license/fabifont/jobpilot?color=blue) ![Latest release](https://img.shields.io/github/v/release/fabifont/jobpilot)

![PyPI release](https://img.shields.io/pypi/v/jobpilot)

# jobpilot

**jobpilot** is a straightforward job scraping library.

## Current limitations

Currently, **jobpilot** only supports LinkedIn. However, integration with other platforms, such as Indeed, is in the pipeline.

## Installation

You can install **jobpilot** from PyPI using popular Python package managers like `poetry`, `pip`, `pipx`, and others.

## Usage

A basic usage script is available in the `examples` directory.

## Development

If you're interested in contributing to **jobpilot**, start by cloning the repository:

```bash
git clone https://github.com/fabifont/jobpilot.git
cd jobpilot
```

Once cloned, install the development dependencies with:

```bash
poetry install
```

This project maintains code quality and consistency using tools like `pre-commit`, `ruff`, `black`, and `pyright`. After cloning and installing the necessary dependencies, set up the pre-commit hooks:

```bash
pre-commit install
```

The pre-commit configuration checks for various common issues. These hooks run automatically with every commit. If a hook detects an issue it cannot fix automatically, it will abort the commit, offering an explanation of the problem.

To manually run pre-commit without committing, for instance, to validate your code before committing, use:

```bash
pre-commit run --all-files
```

All contributors must adhere to these checks. Submitted code in pull requests must pass all Continuous Integration (CI) workflows. GitHub workflows will verify this automatically. Pull requests with failing checks will not be merged.

**jobpilot** follows the [Semantic Versioning 2.0.0](https://semver.org/) standard.

## Contributing

Contributions to **jobpilot** are very welcome! Whether you're reporting bugs, enhancing documentation, or improving the code, every contribution helps.

Sure! Based on the article you provided, here's the section discussing branches and commit naming conventions:

## Branching and commit naming conventions

To ensure consistency and clarity across the codebase, **jobpilot** follows a simplified naming convention for branches and commits. The naming conventions are based on the concepts shared in this [article](https://dev.to/varbsan/a-simplified-convention-for-naming-branches-and-commits-in-git-il4).

To assist with crafting conformant commit messages, **jobpilot** includes `commitizen` in its development dependencies. After staging your changes, you can utilize:

```bash
cz commit
```

`commitizen` will guide you in generating a structured and consistent commit message, adhering to our project's conventions.

## License

**jobpilot** is licensed under the GPL-3.0. For full details, see the `LICENSE` file.
